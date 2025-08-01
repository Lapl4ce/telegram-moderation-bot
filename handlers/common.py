"""
Common handlers for the Telegram moderation bot.
Contains basic commands and utilities.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def start_command(message: Message, **kwargs):
    """Handle /start command."""
    user_data = kwargs.get('user_data', {})
    is_admin = kwargs.get('is_admin', False)
    is_moderator = kwargs.get('is_moderator', False)
    
    welcome_text = f"""
🌟 <b>Добро пожаловать в систему модерации!</b>

👤 Ваш уровень доступа:
{'🔧 Администратор' if is_admin else '⚖️ Модератор' if is_moderator else '👤 Пользователь'}

📋 <b>Доступные команды:</b>

<b>👤 Пользователь:</b>
/profile - посмотреть свой профиль
/top - топ участников
/ticket - создать тикет в поддержку

<b>⚖️ Модератор:</b>
/warn - выдать предупреждение
/mute - заблокировать отправку сообщений
/ban - заблокировать пользователя
/unwarn, /unmute, /unban - снять наказания

<b>🔧 Администратор:</b>
/xpmodify - изменить опыт пользователя
/levelmodify - изменить уровень пользователя
/multiplier - установить множитель опыта
/give_rights, /remove_rights - управление правами
/add_badword, /remove_badword - управление запрещенными словами

Используйте команды для управления сообществом! 🚀
    """
    
    await message.reply(welcome_text)

@router.message(Command("help"))
async def help_command(message: Message, **kwargs):
    """Handle /help command."""
    is_admin = kwargs.get('is_admin', False)
    is_moderator = kwargs.get('is_moderator', False)
    
    help_text = """
📖 <b>Справка по командам</b>

<b>👤 Команды пользователя:</b>
/start - начать работу с ботом
/help - показать эту справку
/profile [@username|user_id] - посмотреть профиль
/top [страница] - топ участников по опыту
/ticket - создать тикет в поддержку

<b>📊 Система уровней:</b>
• За сообщения начисляется 5-20 XP (кулдаун 20 сек)
• Формула уровня: exp = 3×level² + 50×level + 100
• На 25 уровне разблокируются стикеры
• Титулы от "Землянин" до "Суперкластер"
    """
    
    if is_moderator:
        help_text += """
<b>⚖️ Команды модератора:</b>
/warn [@username|user_id] [причина] - предупреждение
/mute [@username|user_id] [время] [причина] - мут
/ban [@username|user_id] [время] [причина] - бан
/unwarn [@username|user_id] - снять предупреждение
/unmute [@username|user_id] - снять мут
/unban [@username|user_id] - снять бан
/reply [номер_тикета] [ответ] - ответить на тикет
        """
    
    if is_admin:
        help_text += """
<b>🔧 Команды администратора:</b>
/xpmodify [@username|user_id] [количество] - изменить XP
/levelmodify [@username|user_id] [уровень] - установить уровень
/multiplier [@username|user_id] [множитель] - множитель XP
/give_rights [@username|user_id] [права] - выдать права
/remove_rights [@username|user_id] [права] - убрать права
/assign_role [@username|user_id] [роль] - назначить роль
/unassign_role [@username|user_id] [роль] - убрать роль
/modify_artpoints [@username|user_id] [количество] - арт-очки
/add_badword [слово] - добавить запрещенное слово
/remove_badword [слово] - убрать запрещенное слово
/badwords_list - список запрещенных слов

<b>💡 Форматы времени:</b>
1m, 5m, 1h, 2h, 1d, 7d (минуты, часы, дни)
        """
    
    await message.reply(help_text)

@router.message(F.text)
async def handle_text_message(message: Message, **kwargs):
    """Handle regular text messages for bad word filtering."""
    from database.database import Database
    
    if not message.text or message.text.startswith('/'):
        return
    
    # Check for bad words
    badwords = await Database.get_badwords()
    text_lower = message.text.lower()
    
    found_badwords = []
    for badword in badwords:
        if badword in text_lower:
            found_badwords.append(badword)
    
    if found_badwords:
        # Delete the message
        try:
            await message.delete()
        except Exception:
            pass  # Ignore errors if bot can't delete
        
        # Notify user
        warning_text = f"""
⚠️ <b>Сообщение удалено</b>

👤 {message.from_user.mention_html()}
🚫 Обнаружены запрещенные слова: {', '.join(found_badwords)}

Пожалуйста, следите за своей речью в чате.
        """
        
        notification = await message.answer(warning_text)
        
        # Auto-delete notification after 10 seconds
        import asyncio
        asyncio.create_task(delete_after_delay(notification, 10))

async def delete_after_delay(message: Message, delay: int):
    """Delete message after specified delay."""
    import asyncio
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass  # Ignore errors