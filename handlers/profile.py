"""
Profile handlers for the Telegram moderation bot.
Handles user profile display and related commands.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from utils.experience import get_user_profile
from utils.user_parser import parse_username, parse_user_id
from database.database import Database
import re

router = Router()

@router.message(Command("profile"))
async def profile_command(message: Message, **kwargs):
    """Handle /profile command to display user profile."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    target_username = None
    
    # Determine target user
    if message.reply_to_message and message.reply_to_message.from_user:
        # Reply to message
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username
    elif args:
        # Username or user ID provided
        arg = args[0]
        if arg.startswith('@'):
            target_username = parse_username(arg)
            # Look up user ID by username
            user_data = await get_user_by_username(target_username)
            if user_data:
                target_user_id = user_data['user_id']
        elif arg.isdigit():
            target_user_id = int(arg)
    else:
        # Show own profile
        target_user_id = message.from_user.id
        target_username = message.from_user.username
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Get profile data
    profile = await get_user_profile(target_user_id)
    if not profile:
        await message.reply("❌ Профиль пользователя не найден.")
        return
    
    # Format profile text
    username_display = f"@{profile['username']}" if profile['username'] else "Не указан"
    
    # Calculate progress bar for current level
    exp_in_level = profile['exp_in_level']
    next_level_exp = profile['next_level_exp']
    progress = exp_in_level / next_level_exp if next_level_exp > 0 else 1
    progress_bar = create_progress_bar(progress)
    
    # Format join date
    join_date = "Не указана"
    if profile['join_date']:
        import datetime
        join_date = datetime.datetime.fromtimestamp(profile['join_date']).strftime("%d.%m.%Y")
    
    # Role badges
    role_badges = []
    if profile['is_admin']:
        role_badges.append("🔧 Администратор")
    elif profile['is_moderator']:
        role_badges.append("⚖️ Модератор")
    if profile['is_art_leader']:
        role_badges.append("🎨 Арт-лидер")
    
    role_text = " | ".join(role_badges) if role_badges else "👤 Пользователь"
    
    # Warnings text
    warnings_text = ""
    if profile['warnings_count'] > 0:
        warnings_text = f"\n⚠️ Предупреждения: {profile['warnings_count']}"
    
    # Special features
    features = []
    if profile['can_use_stickers']:
        features.append("🎭 Стикеры разблокированы")
    if profile['xp_multiplier'] != 1.0:
        features.append(f"⚡ Множитель XP: {profile['xp_multiplier']}x")
    
    features_text = "\n" + "\n".join(features) if features else ""
    
    profile_text = f"""
👤 <b>Профиль пользователя</b>

🏷️ <b>Имя:</b> {profile['first_name']}
📝 <b>Username:</b> {username_display}
🎭 <b>Роль:</b> {role_text}

📊 <b>Статистика:</b>
🏆 <b>Уровень:</b> {profile['level']} ({profile['title']})
⭐ <b>Опыт:</b> {profile['experience']} XP
📈 <b>Прогресс:</b> {exp_in_level}/{next_level_exp} XP
{progress_bar}

🎨 <b>Арт-очки:</b> {profile['art_points']}
📅 <b>Дата регистрации:</b> {join_date}{warnings_text}{features_text}
    """
    
    await message.reply(profile_text)

def create_progress_bar(progress: float, length: int = 10) -> str:
    """Create a visual progress bar."""
    filled = int(progress * length)
    empty = length - filled
    return "█" * filled + "░" * empty + f" {progress:.1%}"

async def get_user_by_username(username: str) -> dict:
    """Get user data by username."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None