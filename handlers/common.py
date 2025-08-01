from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import logging
import random
from datetime import datetime, timedelta

from database.models import User
from database.database import Database
from config import Config
from utils.experience import calculate_level_from_exp
from utils.validators import format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, user: User, db: Database):
    """Handle /start command"""
    welcome_text = f"""
👋 Добро пожаловать, {format_user_display_name(user.username, user.first_name, user.last_name)}!

🤖 Я бот для модерации чата с системой опыта и рейтингов.

📋 Основные команды:
• /profile - ваш профиль и статистика
• /top - топ пользователей по опыту
• /help - полный список команд
• /ticket - создать тикет в ЛС

📈 Зарабатывайте опыт, отправляя сообщения!
🏆 Поднимайтесь в рейтинге и получайте новые уровни!
"""
    await message.reply(welcome_text)

@router.message(Command("help"))
async def cmd_help(message: Message, user: User):
    """Handle /help command"""
    help_text = f"""
📖 **Список команд бота**

👤 **Пользовательские команды:**
• /start - приветствие и информация о боте
• /profile - показать ваш профиль
• /top - топ пользователей по опыту
• /ticket - создать тикет (только в ЛС)

🛡️ **Команды модерации** (для модераторов):
• /warn [пользователь] [причина] - выдать предупреждение
• /mute [пользователь] [время] [причина] - заглушить пользователя
• /ban [пользователь] [время] [причина] - заблокировать пользователя
• /unwarn [пользователь] - снять предупреждение
• /unmute [пользователь] - разглушить пользователя
• /unban [пользователь] - разблокировать пользователя

🎨 **Арт-команды** (для арт-лидеров):
• /modify_artpoints [пользователь] [количество] - изменить арт-очки

👑 **Админ-команды** (для администраторов):
• /xpmodify [пользователь] [количество] - изменить опыт
• /levelmodify [пользователь] [уровень] - изменить уровень
• /give_rights [пользователь] [права] - выдать права
• /remove_rights [пользователь] - убрать права
• /multiplier [пользователь] [множитель] - изменить множитель опыта
• /assign_role [пользователь] [роль] - назначить кастомную роль
• /unassign_role [пользователь] - убрать кастомную роль
• /add_badword [слово] - добавить запрещенное слово
• /remove_badword [слово] - убрать запрещенное слово
• /reply [ID_тикета] [ответ] - ответить на тикет

📊 Система опыта: 5-20 XP за сообщение (кулдаун 20 сек)
🏆 Формула уровня: exp = 3 * level² + 50 * level + 100
"""
    
    await message.reply(help_text, parse_mode="Markdown")

@router.message(F.content_type == "text")
async def handle_text_message(message: Message, user: User, db: Database):
    """Handle regular text messages for experience gain and moderation"""
    try:
        # Check for bad words
        bad_words = await db.get_bad_words()
        if bad_words:
            from utils.validators import contains_bad_words
            found_words = contains_bad_words(message.text, bad_words)
            if found_words:
                try:
                    await message.delete()
                    # Notify moderators (you might want to send to admin group)
                    logger.info(f"Deleted message from user {user.user_id} containing bad words: {found_words}")
                except Exception as e:
                    logger.error(f"Failed to delete message with bad words: {e}")
                return
        
        # Experience gain logic
        now = datetime.now()
        
        # Check cooldown
        if user.last_xp_time and (now - user.last_xp_time).total_seconds() < Config.XP_COOLDOWN:
            return
        
        # Calculate XP gain
        base_xp = random.randint(Config.XP_MIN, Config.XP_MAX)
        gained_xp = int(base_xp * user.xp_multiplier)
        
        # Update user stats
        old_level = user.level
        user.experience += gained_xp
        user.messages_count += 1
        user.last_xp_time = now
        user.level = calculate_level_from_exp(user.experience)
        
        # Save to database
        await db.update_user(user)
        
        # Check for level up
        if user.level > old_level:
            level_up_text = f"🎉 {format_user_display_name(user.username, user.first_name, user.last_name)} достиг {user.level} уровня!"
            await message.reply(level_up_text)
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}")

# Experience gaining is handled by the text message handler above