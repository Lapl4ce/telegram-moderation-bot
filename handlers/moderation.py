"""Moderation handlers for warn, mute, ban commands."""

import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update

from config import WARN_LIMIT, MUTE_DURATION_DEFAULT, BAN_DURATION_DEFAULT
from database.database import get_db
from database.models import User, ModerationAction
from utils.permissions import check_moderator_permissions
from utils.user_parser import parse_username

router = Router()


def parse_duration(duration_str: str) -> Optional[int]:
    """Parse duration string like '1d', '2h', '30m', '60s' to seconds."""
    if not duration_str:
        return None
    
    pattern = r'^(\d+)([dhms])$'
    match = re.match(pattern, duration_str.lower())
    
    if not match:
        return None
    
    amount, unit = match.groups()
    amount = int(amount)
    
    if unit == 's':
        return amount
    elif unit == 'm':
        return amount * 60
    elif unit == 'h':
        return amount * 3600
    elif unit == 'd':
        return amount * 86400
    
    return None


async def get_target_user(message: Message, args: list) -> Optional[tuple[int, str]]:
    """Get target user from command arguments or reply."""
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.first_name or "Пользователь"
    
    if not args:
        return None
    
    username = parse_username(args[0])
    
    async for session in get_db():
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user:
            return user.user_id, user.first_name or user.username or "Пользователь"
    
    return None


@router.message(Command("warn"))
async def warn_command(message: Message, user_role: str):
    """Handle /warn command."""
    if not await check_moderator_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    target_info = await get_target_user(message, args)
    
    if not target_info:
        await message.reply("❌ Пользователь не найден. Используйте /warn @username или ответьте на сообщение.")
        return
    
    target_user_id, target_name = target_info
    
    # Extract reason
    reason = None
    if args and not args[0].startswith('@'):
        reason = ' '.join(args)
    elif len(args) > 1:
        reason = ' '.join(args[1:])
    
    async for session in get_db():
        try:
            # Get current warns
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            new_warns = user.warns + 1
            
            # Update warns
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(warns=new_warns)
            )
            
            # Log moderation action
            action = ModerationAction(
                target_user_id=target_user_id,
                moderator_user_id=message.from_user.id,
                action_type="warn",
                reason=reason
            )
            session.add(action)
            
            await session.commit()
            
            # Check if should auto-ban
            if new_warns >= WARN_LIMIT:
                await session.execute(
                    update(User)
                    .where(User.user_id == target_user_id)
                    .values(
                        is_banned=True,
                        ban_until=datetime.utcnow() + timedelta(seconds=BAN_DURATION_DEFAULT)
                    )
                )
                
                ban_action = ModerationAction(
                    target_user_id=target_user_id,
                    moderator_user_id=message.from_user.id,
                    action_type="ban",
                    reason=f"Автобан за {WARN_LIMIT} предупреждений",
                    duration=BAN_DURATION_DEFAULT
                )
                session.add(ban_action)
                await session.commit()
                
                await message.reply(
                    f"⚠️ <b>Пользователь {target_name} получил предупреждение</b>\n"
                    f"🔢 <b>Предупреждений:</b> {new_warns}/{WARN_LIMIT}\n"
                    f"🚫 <b>Автоматический бан за превышение лимита предупреждений!</b>\n"
                    f"📝 <b>Причина:</b> {reason or 'Не указана'}"
                )
            else:
                await message.reply(
                    f"⚠️ <b>Пользователь {target_name} получил предупреждение</b>\n"
                    f"🔢 <b>Предупреждений:</b> {new_warns}/{WARN_LIMIT}\n"
                    f"📝 <b>Причина:</b> {reason or 'Не указана'}"
                )
                
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при выдаче предупреждения: {e}")


@router.message(Command("mute"))
async def mute_command(message: Message, user_role: str):
    """Handle /mute command."""
    if not await check_moderator_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    target_info = await get_target_user(message, args)
    
    if not target_info:
        await message.reply("❌ Пользователь не найден. Используйте /mute @username [время] [причина]")
        return
    
    target_user_id, target_name = target_info
    
    # Parse duration and reason
    duration_seconds = MUTE_DURATION_DEFAULT
    reason = None
    
    # Skip username if provided
    args_start = 1 if args and args[0].startswith('@') else 0
    remaining_args = args[args_start:]
    
    if remaining_args:
        # Try to parse first arg as duration
        parsed_duration = parse_duration(remaining_args[0])
        if parsed_duration:
            duration_seconds = parsed_duration
            if len(remaining_args) > 1:
                reason = ' '.join(remaining_args[1:])
        else:
            reason = ' '.join(remaining_args)
    
    mute_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    async for session in get_db():
        try:
            # Update user
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(is_muted=True, mute_until=mute_until)
            )
            
            # Log action
            action = ModerationAction(
                target_user_id=target_user_id,
                moderator_user_id=message.from_user.id,
                action_type="mute",
                reason=reason,
                duration=duration_seconds
            )
            session.add(action)
            
            await session.commit()
            
            duration_text = format_duration(duration_seconds)
            await message.reply(
                f"🔇 <b>Пользователь {target_name} заглушен</b>\n"
                f"⏰ <b>Время:</b> {duration_text}\n"
                f"📅 <b>До:</b> {mute_until.strftime('%d.%m.%Y %H:%M')}\n"
                f"📝 <b>Причина:</b> {reason or 'Не указана'}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при заглушении: {e}")


@router.message(Command("ban"))
async def ban_command(message: Message, user_role: str):
    """Handle /ban command."""
    if not await check_moderator_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    target_info = await get_target_user(message, args)
    
    if not target_info:
        await message.reply("❌ Пользователь не найден. Используйте /ban @username [время] [причина]")
        return
    
    target_user_id, target_name = target_info
    
    # Parse duration and reason
    duration_seconds = BAN_DURATION_DEFAULT
    reason = None
    
    # Skip username if provided  
    args_start = 1 if args and args[0].startswith('@') else 0
    remaining_args = args[args_start:]
    
    if remaining_args:
        # Try to parse first arg as duration
        parsed_duration = parse_duration(remaining_args[0])
        if parsed_duration:
            duration_seconds = parsed_duration
            if len(remaining_args) > 1:
                reason = ' '.join(remaining_args[1:])
        else:
            reason = ' '.join(remaining_args)
    
    ban_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    async for session in get_db():
        try:
            # Update user
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(is_banned=True, ban_until=ban_until)
            )
            
            # Log action
            action = ModerationAction(
                target_user_id=target_user_id,
                moderator_user_id=message.from_user.id,
                action_type="ban",
                reason=reason,
                duration=duration_seconds
            )
            session.add(action)
            
            await session.commit()
            
            duration_text = format_duration(duration_seconds)
            await message.reply(
                f"🚫 <b>Пользователь {target_name} заблокирован</b>\n"
                f"⏰ <b>Время:</b> {duration_text}\n"
                f"📅 <b>До:</b> {ban_until.strftime('%d.%m.%Y %H:%M')}\n"
                f"📝 <b>Причина:</b> {reason or 'Не указана'}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при блокировке: {e}")


@router.message(Command("unwarn"))
async def unwarn_command(message: Message, user_role: str):
    """Handle /unwarn command."""
    if not await check_moderator_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    target_info = await get_target_user(message, args)
    
    if not target_info:
        await message.reply("❌ Пользователь не найден. Используйте /unwarn @username")
        return
    
    target_user_id, target_name = target_info
    
    async for session in get_db():
        try:
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or user.warns == 0:
                await message.reply("❌ У пользователя нет предупреждений.")
                return
            
            new_warns = max(0, user.warns - 1)
            
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(warns=new_warns)
            )
            
            # Log action
            action = ModerationAction(
                target_user_id=target_user_id,
                moderator_user_id=message.from_user.id,
                action_type="unwarn"
            )
            session.add(action)
            
            await session.commit()
            
            await message.reply(
                f"✅ <b>Предупреждение снято с пользователя {target_name}</b>\n"
                f"🔢 <b>Предупреждений:</b> {new_warns}/{WARN_LIMIT}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при снятии предупреждения: {e}")


@router.message(Command("unmute"))
async def unmute_command(message: Message, user_role: str):
    """Handle /unmute command."""
    if not await check_moderator_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    target_info = await get_target_user(message, args)
    
    if not target_info:
        await message.reply("❌ Пользователь не найден. Используйте /unmute @username")
        return
    
    target_user_id, target_name = target_info
    
    async for session in get_db():
        try:
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(is_muted=False, mute_until=None)
            )
            
            # Log action
            action = ModerationAction(
                target_user_id=target_user_id,
                moderator_user_id=message.from_user.id,
                action_type="unmute"
            )
            session.add(action)
            
            await session.commit()
            
            await message.reply(f"🔊 <b>Заглушение снято с пользователя {target_name}</b>")
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при снятии заглушения: {e}")


@router.message(Command("unban"))
async def unban_command(message: Message, user_role: str):
    """Handle /unban command."""
    if not await check_moderator_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    target_info = await get_target_user(message, args)
    
    if not target_info:
        await message.reply("❌ Пользователь не найден. Используйте /unban @username")
        return
    
    target_user_id, target_name = target_info
    
    async for session in get_db():
        try:
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(is_banned=False, ban_until=None)
            )
            
            # Log action
            action = ModerationAction(
                target_user_id=target_user_id,
                moderator_user_id=message.from_user.id,
                action_type="unban"
            )
            session.add(action)
            
            await session.commit()
            
            await message.reply(f"✅ <b>Блокировка снята с пользователя {target_name}</b>")
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при снятии блокировки: {e}")


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds}с"
    elif seconds < 3600:
        return f"{seconds // 60}м"
    elif seconds < 86400:
        return f"{seconds // 3600}ч"
    else:
        return f"{seconds // 86400}д"