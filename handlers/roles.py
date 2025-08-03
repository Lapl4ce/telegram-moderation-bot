"""Custom roles management handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update

from database.database import get_db
from database.models import User
from utils.permissions import check_admin_permissions
from utils.user_parser import parse_username

router = Router()


async def get_target_user_roles(message: Message, args: list):
    """Get target user for role commands."""
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


@router.message(Command("set_custom_role"))
async def set_custom_role_command(message: Message, user_role: str):
    """Handle /set_custom_role command to set custom role for user."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply(
            "📝 <b>Установка кастомной роли</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/set_custom_role @username роль</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/set_custom_role @user Великий художник</code>"
        )
        return
    
    target_info = await get_target_user_roles(message, args[1:])
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    custom_role = args[2]
    
    # Validate role length
    if len(custom_role) > 50:
        await message.reply("❌ Роль не должна превышать 50 символов.")
        return
    
    async for session in get_db():
        try:
            # Update custom role
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(custom_role=custom_role)
            )
            await session.commit()
            
            await message.reply(
                f"✅ <b>Кастомная роль установлена</b>\n"
                f"👤 <b>Пользователь:</b> {target_name}\n"
                f"🎭 <b>Роль:</b> {custom_role}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при установке роли: {e}")


@router.message(Command("remove_custom_role"))
async def remove_custom_role_command(message: Message, user_role: str):
    """Handle /remove_custom_role command to remove custom role."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()[1:]
    if len(args) < 1:
        await message.reply(
            "📝 <b>Удаление кастомной роли</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/remove_custom_role @username</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/remove_custom_role @user</code>"
        )
        return
    
    target_info = await get_target_user_roles(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    async for session in get_db():
        try:
            # Get current custom role
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            if not user.custom_role:
                await message.reply("❌ У пользователя нет кастомной роли.")
                return
            
            old_role = user.custom_role
            
            # Remove custom role
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(custom_role=None)
            )
            await session.commit()
            
            await message.reply(
                f"✅ <b>Кастомная роль удалена</b>\n"
                f"👤 <b>Пользователь:</b> {target_name}\n"
                f"🎭 <b>Была роль:</b> {old_role}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при удалении роли: {e}")


@router.message(Command("list_custom_roles"))
async def list_custom_roles_command(message: Message, user_role: str):
    """Handle /list_custom_roles command to list users with custom roles."""
    if not await check_admin_permissions(message, user_role):
        return
    
    async for session in get_db():
        try:
            # Get users with custom roles
            result = await session.execute(
                select(User)
                .where(User.custom_role.isnot(None))
                .order_by(User.custom_role)
            )
            users = result.scalars().all()
            
            if not users:
                await message.reply("📋 Пользователей с кастомными ролями не найдено.")
                return
            
            roles_text = "🎭 <b>Пользователи с кастомными ролями:</b>\n\n"
            
            for user in users:
                display_name = user.first_name or "Неизвестно"
                if user.username:
                    display_name = f"@{user.username}"
                
                roles_text += f"👤 {display_name}\n"
                roles_text += f"🎭 <i>{user.custom_role}</i>\n\n"
            
            await message.reply(roles_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении списка ролей: {e}")


@router.message(Command("role_stats"))
async def role_stats_command(message: Message, user_role: str):
    """Handle /role_stats command to show role statistics."""
    if not await check_admin_permissions(message, user_role):
        return
    
    async for session in get_db():
        try:
            from sqlalchemy import func
            
            # Get system roles count
            result = await session.execute(
                select(User.role, func.count(User.user_id))
                .group_by(User.role)
            )
            system_roles = dict(result.fetchall())
            
            # Get custom roles count
            result = await session.execute(
                select(func.count(User.user_id))
                .where(User.custom_role.isnot(None))
            )
            custom_roles_count = result.scalar()
            
            # Get total users
            result = await session.execute(select(func.count(User.user_id)))
            total_users = result.scalar()
            
            stats_text = (
                f"📊 <b>Статистика ролей</b>\n\n"
                f"👥 <b>Всего пользователей:</b> {total_users}\n\n"
                f"🎭 <b>Системные роли:</b>\n"
            )
            
            role_names = {
                "member": "👤 Участники",
                "moderator": "🛡️ Модераторы",
                "admin": "👑 Администраторы",
                "art_leader": "🎨 Арт-лидеры"
            }
            
            for role, count in system_roles.items():
                role_name = role_names.get(role, role)
                percentage = (count / total_users) * 100 if total_users > 0 else 0
                stats_text += f"• {role_name}: {count} ({percentage:.1f}%)\n"
            
            stats_text += f"\n🌟 <b>Кастомные роли:</b> {custom_roles_count}"
            
            await message.reply(stats_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении статистики ролей: {e}")