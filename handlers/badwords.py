"""
Bad words management handlers for the Telegram moderation bot.
Handles adding, removing, and listing forbidden words.
"""
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from middleware.auth import admin_required
from database.database import Database
from config import ITEMS_PER_PAGE

router = Router()

@router.message(Command("add_badword"))
@admin_required
async def add_badword_command(message: Message, **kwargs):
    """Handle /add_badword command to add a forbidden word."""
    args = message.text.split()[1:] if message.text else []
    
    if not args:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/add_badword [слово]</code>\n"
            "🔍 Пример: <code>/add_badword спам</code>"
        )
        return
    
    word = " ".join(args).strip().lower()
    
    if len(word) < 2:
        await message.reply("❌ Слово должно содержать минимум 2 символа.")
        return
    
    # Add word to database
    added = await Database.add_badword(word, message.from_user.id)
    
    if added:
        success_text = f"""
✅ <b>Запрещенное слово добавлено</b>

🚫 <b>Слово:</b> <code>{word}</code>
👮 <b>Добавил:</b> {message.from_user.mention_html()}

💡 Сообщения с этим словом будут автоматически удаляться.
        """
        await message.reply(success_text)
    else:
        await message.reply(f"❌ Слово '<code>{word}</code>' уже есть в списке запрещенных.")

@router.message(Command("remove_badword"))
@admin_required
async def remove_badword_command(message: Message, **kwargs):
    """Handle /remove_badword command to remove a forbidden word."""
    args = message.text.split()[1:] if message.text else []
    
    if not args:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/remove_badword [слово]</code>\n"
            "🔍 Пример: <code>/remove_badword спам</code>"
        )
        return
    
    word = " ".join(args).strip().lower()
    
    # Remove word from database
    removed = await Database.remove_badword(word)
    
    if removed:
        success_text = f"""
✅ <b>Запрещенное слово удалено</b>

🚫 <b>Слово:</b> <code>{word}</code>
👮 <b>Удалил:</b> {message.from_user.mention_html()}
        """
        await message.reply(success_text)
    else:
        await message.reply(f"❌ Слово '<code>{word}</code>' не найдено в списке запрещенных.")

@router.message(Command("badwords_list"))
@admin_required
async def badwords_list_command(message: Message, **kwargs):
    """Handle /badwords_list command to show forbidden words."""
    await send_badwords_list(message, 1)

async def send_badwords_list(message: Message, page: int = 1):
    """Send paginated list of bad words."""
    badwords = await Database.get_badwords()
    
    if not badwords:
        await message.reply("📝 Список запрещенных слов пуст.")
        return
    
    # Paginate words
    total_pages = (len(badwords) - 1) // ITEMS_PER_PAGE + 1
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_words = badwords[start_idx:end_idx]
    
    # Build list text
    list_text = f"🚫 <b>Запрещенные слова (страница {page}/{total_pages})</b>\n\n"
    
    for i, word in enumerate(page_words, start=start_idx + 1):
        list_text += f"{i}. <code>{word}</code>\n"
    
    list_text += f"\n📊 <b>Всего слов:</b> {len(badwords)}"
    
    # Create pagination keyboard
    keyboard = create_badwords_pagination_keyboard(page, total_pages)
    
    await message.reply(list_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("badwords_page:"))
async def badwords_page_callback(callback: CallbackQuery, **kwargs):
    """Handle bad words page navigation callbacks."""
    if not kwargs.get('is_admin', False):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    page = int(callback.data.split(":")[1])
    
    badwords = await Database.get_badwords()
    
    if not badwords:
        await callback.answer("❌ Список пуст.")
        return
    
    # Paginate words
    total_pages = (len(badwords) - 1) // ITEMS_PER_PAGE + 1
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_words = badwords[start_idx:end_idx]
    
    # Build list text
    list_text = f"🚫 <b>Запрещенные слова (страница {page}/{total_pages})</b>\n\n"
    
    for i, word in enumerate(page_words, start=start_idx + 1):
        list_text += f"{i}. <code>{word}</code>\n"
    
    list_text += f"\n📊 <b>Всего слов:</b> {len(badwords)}"
    
    # Create pagination keyboard
    keyboard = create_badwords_pagination_keyboard(page, total_pages)
    
    try:
        await callback.message.edit_text(list_text, reply_markup=keyboard)
        await callback.answer()
    except Exception:
        await callback.answer("❌ Ошибка при обновлении страницы.")

def create_badwords_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Create pagination keyboard for bad words list."""
    buttons = []
    
    # Previous page button
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"badwords_page:{current_page - 1}"
        ))
    
    # Current page indicator
    buttons.append(InlineKeyboardButton(
        text=f"📄 {current_page}/{total_pages}",
        callback_data="noop"
    ))
    
    # Next page button
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"badwords_page:{current_page + 1}"
        ))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Handle no-operation callbacks."""
    await callback.answer()