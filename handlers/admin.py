"""Admin command handlers."""

import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update, delete

from config import UserRoles
from database.database import get_db
from database.models import User, ExperienceMultiplier
from utils.permissions import check_admin_permissions, can_modify_experience, can_manage_roles
from utils.experience import calculate_level_from_experience, add_experience
from utils.user_parser import parse_username

router = Router()


async def get_target_user_admin(message: Message, args: list) -> Optional[tuple[int, str]]:
    """Get target user for admin commands."""
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


@router.message(Command("xpmodify"))
async def xp_modify_command(message: Message, user_role: str):
    """Handle /xpmodify command to modify user experience."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 <b>Изменение опыта</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/xpmodify @username количество</code>\n\n"
            "📋 <b>Примеры:</b>\n"
            "<code>/xpmodify @user 1000</code> - добавить 1000 XP\n"
            "<code>/xpmodify @user -500</code> - отнять 500 XP"
        )
        return
    
    target_info = await get_target_user_admin(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    try:
        xp_change = int(args[1] if not args[0].startswith('@') else args[2] if len(args) > 2 else args[1])
    except (ValueError, IndexError):
        await message.reply("❌ Неверное количество опыта.")
        return
    
    async for session in get_db():
        try:
            # Get current user data
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            old_experience = user.experience
            old_level = user.level
            new_experience = max(0, old_experience + xp_change)
            new_level = calculate_level_from_experience(new_experience)
            
            # Update user
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(experience=new_experience, level=new_level)
            )
            await session.commit()
            
            change_text = f"+{xp_change}" if xp_change > 0 else str(xp_change)
            level_text = ""
            if new_level != old_level:
                level_text = f"\n📊 <b>Уровень:</b> {old_level} → {new_level}"
            
            await message.reply(
                f"✅ <b>Опыт изменен для {target_name}</b>\n"
                f"💎 <b>Опыт:</b> {old_experience:,} → {new_experience:,} ({change_text})"
                f"{level_text}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при изменении опыта: {e}")


@router.message(Command("levelmodify"))
async def level_modify_command(message: Message, user_role: str):
    """Handle /levelmodify command to modify user level."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 <b>Изменение уровня</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/levelmodify @username уровень</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/levelmodify @user 25</code> - установить 25 уровень"
        )
        return
    
    target_info = await get_target_user_admin(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    try:
        new_level = int(args[1] if not args[0].startswith('@') else args[2] if len(args) > 2 else args[1])
        if new_level < 0:
            raise ValueError()
    except (ValueError, IndexError):
        await message.reply("❌ Неверный уровень.")
        return
    
    async for session in get_db():
        try:
            # Get current user data
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            old_level = user.level
            
            # Calculate experience for the new level
            from utils.experience import calculate_experience_for_level
            new_experience = calculate_experience_for_level(new_level)
            
            # Update user
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(level=new_level, experience=new_experience)
            )
            await session.commit()
            
            await message.reply(
                f"✅ <b>Уровень изменен для {target_name}</b>\n"
                f"📊 <b>Уровень:</b> {old_level} → {new_level}\n"
                f"💎 <b>Новый опыт:</b> {new_experience:,} XP"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при изменении уровня: {e}")


@router.message(Command("multiplier"))
async def multiplier_command(message: Message, user_role: str):
    """Handle /multiplier command to set experience multiplier."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 <b>Множитель опыта</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/multiplier @username множитель [время]</code>\n\n"
            "📋 <b>Примеры:</b>\n"
            "<code>/multiplier @user 2.0</code> - множитель x2 навсегда\n"
            "<code>/multiplier @user 1.5 7d</code> - множитель x1.5 на 7 дней"
        )
        return
    
    target_info = await get_target_user_admin(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    try:
        multiplier_arg_index = 1 if not args[0].startswith('@') else 2
        multiplier = float(args[multiplier_arg_index])
        if multiplier <= 0:
            raise ValueError()
    except (ValueError, IndexError):
        await message.reply("❌ Неверный множитель.")
        return
    
    # Parse duration if provided
    expires_at = None
    if len(args) > multiplier_arg_index + 1:
        duration_str = args[multiplier_arg_index + 1]
        from handlers.moderation import parse_duration
        duration_seconds = parse_duration(duration_str)
        if duration_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    async for session in get_db():
        try:
            # Remove existing multiplier
            await session.execute(
                delete(ExperienceMultiplier).where(ExperienceMultiplier.user_id == target_user_id)
            )
            
            # Add new multiplier
            if multiplier != 1.0:
                new_multiplier = ExperienceMultiplier(
                    user_id=target_user_id,
                    multiplier=multiplier,
                    expires_at=expires_at
                )
                session.add(new_multiplier)
            
            await session.commit()
            
            multiplier_text = f"x{multiplier}"
            if expires_at:
                multiplier_text += f" до {expires_at.strftime('%d.%m.%Y %H:%M')}"
            elif multiplier != 1.0:
                multiplier_text += " (навсегда)"
            else:
                multiplier_text = "убран"
            
            await message.reply(
                f"✅ <b>Множитель опыта для {target_name}</b>\n"
                f"📈 <b>Множитель:</b> {multiplier_text}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при установке множителя: {e}")


@router.message(Command("give_rights"))
async def give_rights_command(message: Message, user_role: str):
    """Handle /give_rights command to give user permissions."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 <b>Выдача прав</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/give_rights @username роль</code>\n\n"
            "📋 <b>Доступные роли:</b>\n"
            "• <code>moderator</code> - модератор\n"
            "• <code>admin</code> - администратор\n"
            "• <code>art_leader</code> - арт-лидер\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/give_rights @user moderator</code>"
        )
        return
    
    target_info = await get_target_user_admin(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    role_arg_index = 1 if not args[0].startswith('@') else 2
    try:
        new_role = args[role_arg_index].lower()
    except IndexError:
        await message.reply("❌ Роль не указана.")
        return
    
    valid_roles = [UserRoles.MODERATOR, UserRoles.ADMIN, UserRoles.ART_LEADER]
    if new_role not in valid_roles:
        await message.reply(f"❌ Неверная роль. Доступные: {', '.join(valid_roles)}")
        return
    
    async for session in get_db():
        try:
            # Update user role
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(role=new_role)
            )
            await session.commit()
            
            role_names = {
                UserRoles.MODERATOR: "🛡️ Модератор",
                UserRoles.ADMIN: "👑 Администратор",
                UserRoles.ART_LEADER: "🎨 Арт-лидер"
            }
            
            await message.reply(
                f"✅ <b>Права выданы пользователю {target_name}</b>\n"
                f"🎭 <b>Новая роль:</b> {role_names.get(new_role, new_role)}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при выдаче прав: {e}")


@router.message(Command("remove_rights"))
async def remove_rights_command(message: Message, user_role: str):
    """Handle /remove_rights command to remove user permissions."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    if len(args) < 1:
        await message.reply(
            "📝 <b>Снятие прав</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/remove_rights @username</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/remove_rights @user</code>"
        )
        return
    
    target_info = await get_target_user_admin(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    async for session in get_db():
        try:
            # Get current role
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            old_role = user.role
            
            # Update user role to member
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(role=UserRoles.MEMBER)
            )
            await session.commit()
            
            role_names = {
                UserRoles.MODERATOR: "🛡️ Модератор",
                UserRoles.ADMIN: "👑 Администратор",
                UserRoles.ART_LEADER: "🎨 Арт-лидер",
                UserRoles.MEMBER: "👤 Участник"
            }
            
            await message.reply(
                f"✅ <b>Права сняты с пользователя {target_name}</b>\n"
                f"🎭 <b>Роль:</b> {role_names.get(old_role, old_role)} → {role_names[UserRoles.MEMBER]}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при снятии прав: {e}")


@router.message(Command("admin_stats"))
async def admin_stats_command(message: Message, user_role: str):
    """Handle /admin_stats command to show bot statistics."""
    if not await check_admin_permissions(message, user_role):
        return
    
    async for session in get_db():
        try:
            # Get user statistics
            from sqlalchemy import func
            
            # Total users
            result = await session.execute(select(func.count(User.user_id)))
            total_users = result.scalar()
            
            # Users by role
            result = await session.execute(
                select(User.role, func.count(User.user_id))
                .group_by(User.role)
            )
            roles_stats = dict(result.fetchall())
            
            # Active users (with messages in last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            result = await session.execute(
                select(func.count(User.user_id))
                .where(User.last_message_time > thirty_days_ago)
            )
            active_users = result.scalar()
            
            # Top level users
            result = await session.execute(
                select(User.username, User.level, User.experience)
                .order_by(User.level.desc(), User.experience.desc())
                .limit(5)
            )
            top_users = result.fetchall()
            
            stats_text = (
                f"📊 <b>Статистика бота</b>\n\n"
                f"👥 <b>Всего пользователей:</b> {total_users}\n"
                f"🟢 <b>Активные (30 дней):</b> {active_users}\n\n"
                f"🎭 <b>По ролям:</b>\n"
            )
            
            role_names = {
                UserRoles.MEMBER: "👤 Участники",
                UserRoles.MODERATOR: "🛡️ Модераторы",
                UserRoles.ADMIN: "👑 Администраторы",
                UserRoles.ART_LEADER: "🎨 Арт-лидеры"
            }
            
            for role, count in roles_stats.items():
                role_name = role_names.get(role, role)
                stats_text += f"• {role_name}: {count}\n"
            
            stats_text += "\n🏆 <b>Топ по уровню:</b>\n"
            for i, (username, level, experience) in enumerate(top_users, 1):
                username_display = username or "Неизвестно"
                stats_text += f"{i}. @{username_display} - {level} ур. ({experience:,} XP)\n"
            
            await message.reply(stats_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении статистики: {e}")