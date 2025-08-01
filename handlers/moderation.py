"""
Moderation handlers for the Telegram moderation bot.
Handles warn, mute, ban commands and their removal counterparts.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from middleware.auth import moderator_required
from database.database import Database
from utils.user_parser import parse_username
from config import MAX_WARNINGS, DEFAULT_MUTE_TIME, DEFAULT_BAN_TIME
import re
import time

router = Router()

@router.message(Command("warn"))
@moderator_required
async def warn_command(message: Message, **kwargs):
    """Handle /warn command to give a warning to a user."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    reason = None
    
    # Parse target user and reason
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        reason = " ".join(args) if args else None
    elif args:
        # First arg should be username or user_id
        target_arg = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else None
        
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Укажите пользователя для предупреждения.")
        return
    
    # Check if target user exists
    target_user = await Database.get_user(target_user_id)
    if not target_user:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Add warning
    moderator_id = message.from_user.id
    warning_id = await Database.add_warning(target_user_id, moderator_id, reason)
    
    # Get current warnings count
    warnings = await Database.get_active_warnings(target_user_id)
    warnings_count = len(warnings)
    
    # Format warning message
    target_username = target_user.get('username')
    target_display = f"@{target_username}" if target_username else target_user.get('first_name', 'Неизвестный')
    
    reason_text = f"\n📝 <b>Причина:</b> {reason}" if reason else ""
    
    warning_text = f"""
⚠️ <b>Предупреждение выдано</b>

👤 <b>Пользователь:</b> {target_display}
🔢 <b>Предупреждение:</b> #{warning_id}
📊 <b>Всего предупреждений:</b> {warnings_count}/{MAX_WARNINGS}
👮 <b>Модератор:</b> {message.from_user.mention_html()}{reason_text}
    """
    
    # Check if user should be banned for too many warnings
    if warnings_count >= MAX_WARNINGS:
        # Auto-ban for exceeding warning limit
        ban_until = int(time.time()) + DEFAULT_BAN_TIME
        await Database.add_ban(target_user_id, moderator_id, ban_until, "Превышен лимит предупреждений")
        warning_text += f"\n\n🚫 <b>Пользователь заблокирован за превышение лимита предупреждений!</b>"
    
    await message.reply(warning_text)

@router.message(Command("unwarn"))
@moderator_required
async def unwarn_command(message: Message, **kwargs):
    """Handle /unwarn command to remove warnings from a user."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    
    # Parse target user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif args:
        target_arg = args[0]
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Укажите пользователя для снятия предупреждений.")
        return
    
    # Remove warnings
    removed_count = await Database.clear_user_warnings(target_user_id)
    
    if removed_count == 0:
        await message.reply("❌ У пользователя нет активных предупреждений.")
        return
    
    # Get user info for display
    target_user = await Database.get_user(target_user_id)
    target_username = target_user.get('username') if target_user else None
    target_display = f"@{target_username}" if target_username else "Пользователь"
    
    success_text = f"""
✅ <b>Предупреждения сняты</b>

👤 <b>Пользователь:</b> {target_display}
🔢 <b>Снято предупреждений:</b> {removed_count}
👮 <b>Модератор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("mute"))
@moderator_required
async def mute_command(message: Message, **kwargs):
    """Handle /mute command to mute a user."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    mute_duration = DEFAULT_MUTE_TIME
    reason = None
    
    # Parse arguments
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        if args:
            # First arg might be duration, rest is reason
            duration_arg = args[0]
            parsed_duration = parse_duration(duration_arg)
            if parsed_duration:
                mute_duration = parsed_duration
                reason = " ".join(args[1:]) if len(args) > 1 else None
            else:
                reason = " ".join(args)
    elif args:
        target_arg = args[0]
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
        
        if len(args) > 1:
            duration_arg = args[1]
            parsed_duration = parse_duration(duration_arg)
            if parsed_duration:
                mute_duration = parsed_duration
                reason = " ".join(args[2:]) if len(args) > 2 else None
            else:
                reason = " ".join(args[1:])
    
    if not target_user_id:
        await message.reply("❌ Укажите пользователя для блокировки.")
        return
    
    # Check if user exists
    target_user = await Database.get_user(target_user_id)
    if not target_user:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Add mute
    moderator_id = message.from_user.id
    unmute_time = int(time.time()) + mute_duration
    mute_id = await Database.add_mute(target_user_id, moderator_id, unmute_time, reason)
    
    # Format response
    target_username = target_user.get('username')
    target_display = f"@{target_username}" if target_username else target_user.get('first_name', 'Неизвестный')
    
    duration_text = format_duration(mute_duration)
    reason_text = f"\n📝 <b>Причина:</b> {reason}" if reason else ""
    
    mute_text = f"""
🔇 <b>Пользователь заблокирован</b>

👤 <b>Пользователь:</b> {target_display}
⏰ <b>Длительность:</b> {duration_text}
👮 <b>Модератор:</b> {message.from_user.mention_html()}{reason_text}
    """
    
    await message.reply(mute_text)

@router.message(Command("unmute"))
@moderator_required
async def unmute_command(message: Message, **kwargs):
    """Handle /unmute command to unmute a user."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    
    # Parse target user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif args:
        target_arg = args[0]
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Укажите пользователя для разблокировки.")
        return
    
    # Remove mute
    removed = await Database.remove_mute(target_user_id)
    
    if not removed:
        await message.reply("❌ Пользователь не заблокирован.")
        return
    
    # Get user info for display
    target_user = await Database.get_user(target_user_id)
    target_username = target_user.get('username') if target_user else None
    target_display = f"@{target_username}" if target_username else "Пользователь"
    
    success_text = f"""
✅ <b>Пользователь разблокирован</b>

👤 <b>Пользователь:</b> {target_display}
👮 <b>Модератор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("ban"))
@moderator_required
async def ban_command(message: Message, **kwargs):
    """Handle /ban command to ban a user."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    ban_duration = DEFAULT_BAN_TIME
    reason = None
    
    # Parse arguments (similar to mute)
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        if args:
            duration_arg = args[0]
            parsed_duration = parse_duration(duration_arg)
            if parsed_duration:
                ban_duration = parsed_duration
                reason = " ".join(args[1:]) if len(args) > 1 else None
            else:
                reason = " ".join(args)
    elif args:
        target_arg = args[0]
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
        
        if len(args) > 1:
            duration_arg = args[1]
            parsed_duration = parse_duration(duration_arg)
            if parsed_duration:
                ban_duration = parsed_duration
                reason = " ".join(args[2:]) if len(args) > 2 else None
            else:
                reason = " ".join(args[1:])
    
    if not target_user_id:
        await message.reply("❌ Укажите пользователя для бана.")
        return
    
    # Check if user exists
    target_user = await Database.get_user(target_user_id)
    if not target_user:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Add ban
    moderator_id = message.from_user.id
    unban_time = int(time.time()) + ban_duration
    ban_id = await Database.add_ban(target_user_id, moderator_id, unban_time, reason)
    
    # Format response
    target_username = target_user.get('username')
    target_display = f"@{target_username}" if target_username else target_user.get('first_name', 'Неизвестный')
    
    duration_text = format_duration(ban_duration)
    reason_text = f"\n📝 <b>Причина:</b> {reason}" if reason else ""
    
    ban_text = f"""
🚫 <b>Пользователь забанен</b>

👤 <b>Пользователь:</b> {target_display}
⏰ <b>Длительность:</b> {duration_text}
👮 <b>Модератор:</b> {message.from_user.mention_html()}{reason_text}
    """
    
    await message.reply(ban_text)

@router.message(Command("unban"))
@moderator_required
async def unban_command(message: Message, **kwargs):
    """Handle /unban command to unban a user."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    
    # Parse target user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif args:
        target_arg = args[0]
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Укажите пользователя для разбана.")
        return
    
    # Remove ban
    removed = await Database.remove_ban(target_user_id)
    
    if not removed:
        await message.reply("❌ Пользователь не забанен.")
        return
    
    # Get user info for display
    target_user = await Database.get_user(target_user_id)
    target_username = target_user.get('username') if target_user else None
    target_display = f"@{target_username}" if target_username else "Пользователь"
    
    success_text = f"""
✅ <b>Пользователь разбанен</b>

👤 <b>Пользователь:</b> {target_display}
👮 <b>Модератор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

# Utility functions

async def get_user_id_by_username(username: str) -> int:
    """Get user ID by username."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

def parse_duration(duration_str: str) -> int:
    """Parse duration string (e.g., '1h', '30m', '7d') to seconds."""
    if not duration_str:
        return None
    
    # Match pattern like 1h, 30m, 7d
    match = re.match(r'^(\d+)([mhd])$', duration_str.lower())
    if not match:
        return None
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 'm':  # minutes
        return value * 60
    elif unit == 'h':  # hours
        return value * 3600
    elif unit == 'd':  # days
        return value * 86400
    
    return None

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} ч"
    else:
        days = seconds // 86400
        return f"{days} дн"