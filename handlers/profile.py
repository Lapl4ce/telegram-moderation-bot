"""Profile handlers for user profiles and level system."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from database.database import get_db
from database.models import User
from utils.experience import calculate_experience_for_next_level, calculate_experience_progress
from utils.titles import get_title_by_level, format_title_progress
from utils.user_parser import parse_username

router = Router()


@router.message(Command("profile"))
async def profile_command(message: Message):
    """Handle /profile command."""
    target_user = None
    
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    # Check if username provided
    elif len(message.text.split()) > 1:
        username = parse_username(message.text.split()[1])
        async for session in get_db():
            result = await session.execute(
                select(User).where(User.username == username)
            )
            target_user = result.scalar_one_or_none()
            if target_user:
                target_user_id = target_user.user_id
            else:
                await message.reply("❌ Пользователь не найден.")
                return
    else:
        # Show own profile
        target_user_id = message.from_user.id
    
    # Get user data
    async for session in get_db():
        result = await session.execute(
            select(User).where(User.user_id == target_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.reply("❌ Пользователь не найден в базе данных.")
            return
        
        # Calculate experience progress
        current_level_exp, next_level_exp, progress_in_level = calculate_experience_progress(
            user.experience, user.level
        )
        needed_exp = next_level_exp - user.experience
        
        # Get title
        title = get_title_by_level(user.level)
        title_progress = format_title_progress(user.level)
        
        # Format display name
        display_name = user.first_name or "Неизвестно"
        if user.last_name:
            display_name += f" {user.last_name}"
        if user.username:
            display_name += f" (@{user.username})"
        
        # Create profile text
        profile_text = (
            f"👤 <b>Профиль пользователя</b>\n\n"
            f"📝 <b>Имя:</b> {display_name}\n"
            f"🆔 <b>ID:</b> <code>{user.user_id}</code>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"⭐ <b>Уровень:</b> {user.level}\n"
            f"💎 <b>Опыт:</b> {user.experience:,} XP\n"
            f"📈 <b>До следующего уровня:</b> {needed_exp:,} XP\n\n"
            f"{title_progress}\n\n"
            f"🎭 <b>Роль:</b> {get_role_display(user.role)}\n"
        )
        
        if user.custom_role:
            profile_text += f"🎨 <b>Кастомная роль:</b> {user.custom_role}\n"
        
        if user.art_points > 0:
            profile_text += f"🎨 <b>Арт-очки:</b> {user.art_points}\n"
        
        profile_text += f"\n🛡️ <b>Модерация:</b>\n"
        profile_text += f"⚠️ <b>Предупреждения:</b> {user.warns}\n"
        
        if user.is_muted:
            profile_text += f"🔇 <b>Статус:</b> Заглушен"
            if user.mute_until:
                profile_text += f" до {user.mute_until.strftime('%d.%m.%Y %H:%M')}"
            profile_text += "\n"
        
        if user.is_banned:
            profile_text += f"🚫 <b>Статус:</b> Заблокирован"
            if user.ban_until:
                profile_text += f" до {user.ban_until.strftime('%d.%m.%Y %H:%M')}"
            profile_text += "\n"
        
        if user.created_at:
            profile_text += f"\n📅 <b>Присоединился:</b> {user.created_at.strftime('%d.%m.%Y')}"
        
        await message.reply(profile_text)


def get_role_display(role: str) -> str:
    """Get display name for user role."""
    role_names = {
        "member": "👤 Участник",
        "moderator": "🛡️ Модератор", 
        "admin": "👑 Администратор",
        "art_leader": "🎨 Арт-лидер"
    }
    return role_names.get(role, role)