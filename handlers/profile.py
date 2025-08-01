from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.models import User
from database.database import Database
from utils.experience import format_experience_bar, get_level_progress, calculate_exp_for_level
from utils.validators import format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("profile"))
async def cmd_profile(message: Message, user: User, db: Database):
    """Handle /profile command"""
    
    # Get user rank
    rank = await db.get_user_rank(user.user_id)
    
    # Calculate level progress
    current_level, current_level_exp, next_level_exp = get_level_progress(user.experience)
    
    # Calculate experience needed for next level
    if current_level == 1:
        exp_for_current = 100
        exp_for_next = calculate_exp_for_level(2)
        progress_exp = user.experience - 100
        needed_exp = exp_for_next - user.experience
    else:
        exp_for_current = calculate_exp_for_level(current_level)
        exp_for_next = calculate_exp_for_level(current_level + 1)
        progress_exp = user.experience - exp_for_current
        needed_exp = exp_for_next - user.experience
    
    # Format experience bar
    exp_bar = format_experience_bar(user.experience)
    
    # Get punishments info
    from database.models import PunishmentType
    warns = await db.get_active_punishments(user.user_id, PunishmentType.WARN)
    mutes = await db.get_active_punishments(user.user_id, PunishmentType.MUTE)
    bans = await db.get_active_punishments(user.user_id, PunishmentType.BAN)
    
    # Format user display name
    display_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    # Format rights
    rights_emoji = {
        "user": "👤",
        "moderator": "🛡️", 
        "admin": "👑",
        "art_leader": "🎨"
    }
    
    rights_name = {
        "user": "Пользователь",
        "moderator": "Модератор",
        "admin": "Администратор", 
        "art_leader": "Арт-лидер"
    }
    
    profile_text = f"""
👤 **Профиль пользователя**

🏷️ **Имя:** {display_name}
🆔 **ID:** `{user.user_id}`
{rights_emoji.get(user.rights.value, "👤")} **Права:** {rights_name.get(user.rights.value, "Пользователь")}

📊 **Статистика:**
🏆 **Уровень:** {user.level}
⭐ **Опыт:** {user.experience:,}
📈 **Рейтинг:** #{rank or "N/A"}
💬 **Сообщений:** {user.messages_count:,}

📊 **Прогресс уровня:**
{exp_bar}
📈 {progress_exp:,}/{exp_for_next - exp_for_current:,} XP до {current_level + 1} уровня
🎯 Нужно ещё: {needed_exp:,} XP

🎨 **Арт-очки:** {user.art_points}
⚡ **Множитель опыта:** {user.xp_multiplier}x
"""
    
    # Add custom role/title if exists
    if user.custom_role:
        profile_text += f"\n🏅 **Кастомная роль:** {user.custom_role}"
    
    if user.custom_title:
        profile_text += f"\n👑 **Титул:** {user.custom_title}"
    
    # Add punishments info
    if warns or mutes or bans:
        profile_text += "\n\n⚠️ **Активные наказания:**"
        if warns:
            profile_text += f"\n🔸 Предупреждений: {len(warns)}"
        if mutes:
            profile_text += f"\n🔸 Заглушен: Да"
        if bans:
            profile_text += f"\n🔸 Заблокирован: Да"
    
    await message.reply(profile_text, parse_mode="Markdown")