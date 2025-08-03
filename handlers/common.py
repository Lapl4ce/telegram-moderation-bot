"""Common handlers for basic bot commands."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command."""
    welcome_text = (
        "🤖 <b>Добро пожаловать в бота модерации!</b>\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "• /profile - ваш профиль\n"
        "• /top - рейтинг пользователей\n"
        "• /ticket - создать тикет поддержки (только в ЛС)\n\n"
        "🛡️ <b>Команды модерации:</b>\n"
        "• /warn - предупреждение\n"
        "• /mute - заглушить\n"
        "• /ban - заблокировать\n"
        "• /unwarn - снять предупреждение\n"
        "• /unmute - снять заглушение\n"
        "• /unban - разблокировать\n\n"
        "⚙️ <b>Админ команды:</b>\n"
        "• /xpmodify - изменить опыт\n"
        "• /levelmodify - изменить уровень\n"
        "• /multiplier - множитель опыта\n"
        "• /give_rights - выдать права\n"
        "• /remove_rights - снять права\n\n"
        "ℹ️ Для получения помощи используйте команды или обратитесь к администраторам."
    )
    
    await message.answer(welcome_text)


@router.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command."""
    help_text = (
        "🆘 <b>Справка по командам</b>\n\n"
        "<b>Пользовательские команды:</b>\n"
        "• <code>/start</code> - приветствие и список команд\n"
        "• <code>/profile</code> - показать ваш профиль\n"
        "• <code>/profile @username</code> - профиль пользователя\n"
        "• <code>/top</code> - рейтинг пользователей\n"
        "• <code>/ticket</code> - создать тикет (только в ЛС)\n\n"
        "<b>Команды модерации:</b>\n"
        "• <code>/warn @user [причина]</code> - предупредить\n"
        "• <code>/mute @user [время] [причина]</code> - заглушить\n"
        "• <code>/ban @user [время] [причина]</code> - заблокировать\n"
        "• <code>/unwarn @user</code> - снять предупреждение\n"
        "• <code>/unmute @user</code> - снять заглушение\n"
        "• <code>/unban @user</code> - разблокировать\n\n"
        "<b>Формат времени:</b> 1d, 2h, 30m, 60s\n\n"
        "❓ Если у вас есть вопросы, создайте тикет через /ticket"
    )
    
    await message.answer(help_text)