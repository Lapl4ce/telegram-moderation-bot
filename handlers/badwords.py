from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.models import User
from database.database import Database
from middleware.auth import require_admin
from utils.validators import sanitize_text, format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("add_badword"))
@require_admin
async def cmd_add_badword(message: Message, user: User, db: Database):
    """Handle /add_badword command - add bad word to filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("""
🚫 **Добавление запрещённого слова**

Используйте: `/add_badword слово_или_фраза`

Пример:
`/add_badword спам`
`/add_badword плохое слово`

Слово будет автоматически удаляться из сообщений.
""", parse_mode="Markdown")
        return
    
    word = sanitize_text(args[1]).lower().strip()
    
    if len(word) < 2:
        await message.reply("❌ Слово должно содержать минимум 2 символа")
        return
    
    if len(word) > 100:
        await message.reply("❌ Слово не может быть длиннее 100 символов")
        return
    
    # Add to database
    success = await db.add_bad_word(word, user.user_id)
    
    if success:
        admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
        
        result_text = f"""
✅ **Запрещённое слово добавлено**

🚫 **Слово:** `{word}`
👑 **Администратор:** {admin_name}

Сообщения с этим словом будут автоматически удаляться.
"""
        await message.reply(result_text, parse_mode="Markdown")
        
        logger.info(f"Admin {user.user_id} added bad word: {word}")
    else:
        await message.reply("❌ Это слово уже находится в списке запрещённых")

@router.message(Command("remove_badword"))
@require_admin
async def cmd_remove_badword(message: Message, user: User, db: Database):
    """Handle /remove_badword command - remove bad word from filter"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply("""
✅ **Удаление запрещённого слова**

Используйте: `/remove_badword слово_или_фраза`

Пример:
`/remove_badword спам`
`/remove_badword плохое слово`

Слово будет удалено из фильтра.
""", parse_mode="Markdown")
        return
    
    word = sanitize_text(args[1]).lower().strip()
    
    # Remove from database
    success = await db.remove_bad_word(word)
    
    if success:
        admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
        
        result_text = f"""
✅ **Запрещённое слово удалено**

🆓 **Слово:** `{word}`
👑 **Администратор:** {admin_name}

Это слово больше не будет фильтроваться.
"""
        await message.reply(result_text, parse_mode="Markdown")
        
        logger.info(f"Admin {user.user_id} removed bad word: {word}")
    else:
        await message.reply("❌ Это слово не найдено в списке запрещённых")

@router.message(Command("list_badwords"))
@require_admin
async def cmd_list_badwords(message: Message, user: User, db: Database):
    """Handle /list_badwords command - list all bad words"""
    
    bad_words = await db.get_bad_words()
    
    if not bad_words:
        await message.reply("📝 Список запрещённых слов пуст")
        return
    
    # Group words for better display
    words_text = ""
    for i, word in enumerate(bad_words, 1):
        words_text += f"{i}. `{word}`\n"
        
        # Split into multiple messages if too long
        if len(words_text) > 3000:
            await message.reply(f"🚫 **Запрещённые слова (часть {i//50 + 1}):**\n\n{words_text}", parse_mode="Markdown")
            words_text = ""
    
    if words_text:
        header = f"🚫 **Запрещённые слова ({len(bad_words)} всего):**\n\n"
        await message.reply(header + words_text, parse_mode="Markdown")

@router.message(Command("clear_badwords"))
@require_admin
async def cmd_clear_badwords(message: Message, user: User, db: Database):
    """Handle /clear_badwords command - clear all bad words (dangerous!)"""
    
    # This is a dangerous operation, so we require confirmation
    await message.reply("""
⚠️ **ВНИМАНИЕ!**

Вы хотите удалить ВСЕ запрещённые слова из базы данных.
Это действие нельзя отменить!

Для подтверждения отправьте:
`/confirm_clear_badwords`

Для отмены ничего не делайте.
""", parse_mode="Markdown")

@router.message(Command("confirm_clear_badwords"))
@require_admin
async def cmd_confirm_clear_badwords(message: Message, user: User, db: Database):
    """Handle /confirm_clear_badwords command - confirm clearing all bad words"""
    
    # Get count of words before clearing
    bad_words = await db.get_bad_words()
    words_count = len(bad_words)
    
    # Clear all bad words by removing each one
    # Note: This is inefficient but works with current database structure
    # In production, you'd want a proper "clear all" method
    for word in bad_words:
        await db.remove_bad_word(word)
    
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    result_text = f"""
🗑️ **Все запрещённые слова удалены**

📊 **Удалено:** {words_count} слов
👑 **Администратор:** {admin_name}

Фильтр запрещённых слов отключён до добавления новых слов.
"""
    
    await message.reply(result_text, parse_mode="Markdown")
    logger.warning(f"Admin {user.user_id} cleared all bad words ({words_count} words)")

@router.message(Command("badwords_stats"))
@require_admin
async def cmd_badwords_stats(message: Message, user: User, db: Database):
    """Handle /badwords_stats command - show bad words statistics"""
    
    bad_words = await db.get_bad_words()
    words_count = len(bad_words)
    
    if words_count == 0:
        stats_text = """
📊 **Статистика фильтра слов**

🚫 **Запрещённых слов:** 0
⚠️ **Статус:** Фильтр отключён

Добавьте запрещённые слова командой `/add_badword`
"""
    else:
        # Calculate some basic stats
        avg_length = sum(len(word) for word in bad_words) / words_count
        longest_word = max(bad_words, key=len) if bad_words else ""
        shortest_word = min(bad_words, key=len) if bad_words else ""
        
        stats_text = f"""
📊 **Статистика фильтра слов**

🚫 **Запрещённых слов:** {words_count}
✅ **Статус:** Активен

📏 **Средняя длина:** {avg_length:.1f} символов
🔤 **Самое длинное:** `{longest_word}` ({len(longest_word)} символов)
🔡 **Самое короткое:** `{shortest_word}` ({len(shortest_word)} символов)

Используйте `/list_badwords` для просмотра всех слов.
"""
    
    await message.reply(stats_text, parse_mode="Markdown")