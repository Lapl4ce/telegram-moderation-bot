from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging
from datetime import datetime, timedelta

from database.models import User, Punishment, PunishmentType
from database.database import Database
from middleware.auth import require_moderator
from utils.time_parser import parse_time_string, format_timedelta
from utils.validators import extract_user_id, sanitize_text, format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

async def get_target_user(message: Message, db: Database, args: list) -> User:
    """Get target user from message arguments or reply"""
    target_user = None
    
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_user = await db.get_or_create_user(
            user_id=target_user_id,
            username=message.reply_to_message.from_user.username,
            first_name=message.reply_to_message.from_user.first_name,
            last_name=message.reply_to_message.from_user.last_name
        )
    elif args:
        # Try to extract user ID from first argument
        user_id = extract_user_id(args[0])
        if user_id:
            target_user = await db.get_or_create_user(user_id=user_id)
    
    return target_user

@router.message(Command("warn"))
@require_moderator
async def cmd_warn(message: Message, user: User, db: Database):
    """Handle /warn command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для предупреждения (ответьте на сообщение или укажите ID)")
        return
    
    # Get reason
    reason_start_idx = 1 if args and extract_user_id(args[0]) else 0
    reason = " ".join(args[reason_start_idx:]) if len(args) > reason_start_idx else "Нарушение правил"
    reason = sanitize_text(reason)
    
    # Create punishment
    punishment = Punishment(
        user_id=target_user.user_id,
        moderator_id=user.user_id,
        punishment_type=PunishmentType.WARN,
        reason=reason
    )
    
    await db.add_punishment(punishment)
    
    # Get current warns count
    warns = await db.get_active_punishments(target_user.user_id, PunishmentType.WARN)
    warns_count = len(warns)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    moderator_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    warn_text = f"""
⚠️ **Предупреждение выдано**

👤 **Пользователь:** {target_name}
👮 **Модератор:** {moderator_name}
📝 **Причина:** {reason}
📊 **Предупреждений:** {warns_count}
"""
    
    await message.reply(warn_text, parse_mode="Markdown")
    
    # Check if user should be auto-banned
    from config import Config
    if warns_count >= Config.MAX_WARNS:
        # Auto-ban for max warns
        ban_punishment = Punishment(
            user_id=target_user.user_id,
            moderator_id=user.user_id,
            punishment_type=PunishmentType.BAN,
            reason=f"Автобан за {Config.MAX_WARNS} предупреждений",
            duration_minutes=24 * 60,  # 24 hours
            expires_at=datetime.now() + timedelta(hours=24)
        )
        await db.add_punishment(ban_punishment)
        
        await message.reply(f"🔨 {target_name} автоматически заблокирован на 24 часа за {Config.MAX_WARNS} предупреждений")

@router.message(Command("mute"))
@require_moderator
async def cmd_mute(message: Message, user: User, db: Database):
    """Handle /mute command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для заглушения")
        return
    
    # Parse arguments
    arg_start = 1 if args and extract_user_id(args[0]) else 0
    duration_str = args[arg_start] if len(args) > arg_start else "1h"
    reason_start = arg_start + 1
    reason = " ".join(args[reason_start:]) if len(args) > reason_start else "Нарушение правил"
    reason = sanitize_text(reason)
    
    # Parse duration
    duration = parse_time_string(duration_str)
    if not duration:
        await message.reply("❌ Неверный формат времени. Используйте: 1d2h30m")
        return
    
    expires_at = datetime.now() + duration
    
    # Create punishment
    punishment = Punishment(
        user_id=target_user.user_id,
        moderator_id=user.user_id,
        punishment_type=PunishmentType.MUTE,
        reason=reason,
        duration_minutes=int(duration.total_seconds() / 60),
        expires_at=expires_at
    )
    
    await db.add_punishment(punishment)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    moderator_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    mute_text = f"""
🔇 **Пользователь заглушен**

👤 **Пользователь:** {target_name}
👮 **Модератор:** {moderator_name}
⏱️ **Длительность:** {format_timedelta(duration)}
📝 **Причина:** {reason}
⏰ **До:** {expires_at.strftime('%d.%m.%Y %H:%M')}
"""
    
    await message.reply(mute_text, parse_mode="Markdown")

@router.message(Command("ban"))
@require_moderator
async def cmd_ban(message: Message, user: User, db: Database):
    """Handle /ban command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для блокировки")
        return
    
    # Parse arguments
    arg_start = 1 if args and extract_user_id(args[0]) else 0
    duration_str = args[arg_start] if len(args) > arg_start else None
    reason_start = arg_start + (1 if duration_str else 0)
    reason = " ".join(args[reason_start:]) if len(args) > reason_start else "Нарушение правил"
    reason = sanitize_text(reason)
    
    # Parse duration (optional for permanent ban)
    duration = None
    expires_at = None
    if duration_str:
        duration = parse_time_string(duration_str)
        if duration:
            expires_at = datetime.now() + duration
    
    # Create punishment
    punishment = Punishment(
        user_id=target_user.user_id,
        moderator_id=user.user_id,
        punishment_type=PunishmentType.BAN,
        reason=reason,
        duration_minutes=int(duration.total_seconds() / 60) if duration else None,
        expires_at=expires_at
    )
    
    await db.add_punishment(punishment)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    moderator_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    if duration:
        ban_text = f"""
🔨 **Пользователь заблокирован**

👤 **Пользователь:** {target_name}
👮 **Модератор:** {moderator_name}
⏱️ **Длительность:** {format_timedelta(duration)}
📝 **Причина:** {reason}
⏰ **До:** {expires_at.strftime('%d.%m.%Y %H:%M')}
"""
    else:
        ban_text = f"""
🔨 **Пользователь заблокирован навсегда**

👤 **Пользователь:** {target_name}
👮 **Модератор:** {moderator_name}
📝 **Причина:** {reason}
"""
    
    await message.reply(ban_text, parse_mode="Markdown")

@router.message(Command("unwarn"))
@require_moderator
async def cmd_unwarn(message: Message, user: User, db: Database):
    """Handle /unwarn command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для снятия предупреждения")
        return
    
    # Remove one warning
    await db.remove_punishment(target_user.user_id, PunishmentType.WARN)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    
    await message.reply(f"✅ Предупреждение снято с пользователя {target_name}")

@router.message(Command("unmute"))
@require_moderator
async def cmd_unmute(message: Message, user: User, db: Database):
    """Handle /unmute command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для разглушения")
        return
    
    # Remove mute
    await db.remove_punishment(target_user.user_id, PunishmentType.MUTE)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    
    await message.reply(f"🔊 Пользователь {target_name} разглушен")

@router.message(Command("unban"))
@require_moderator
async def cmd_unban(message: Message, user: User, db: Database):
    """Handle /unban command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для разблокировки")
        return
    
    # Remove ban
    await db.remove_punishment(target_user.user_id, PunishmentType.BAN)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    
    await message.reply(f"🔓 Пользователь {target_name} разблокирован")