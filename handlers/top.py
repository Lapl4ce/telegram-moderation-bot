"""
Top and statistics handlers for the Telegram moderation bot.
Handles leaderboards and user statistics.
"""
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from database.database import Database
from config import TOP_USERS_PER_PAGE, get_user_title
from utils.experience import get_user_profile

router = Router()

@router.message(Command("top"))
async def top_command(message: Message, **kwargs):
    """Handle /top command to display top users."""
    args = message.text.split()[1:] if message.text else []
    page = 1
    
    # Parse page number
    if args and args[0].isdigit():
        page = max(1, int(args[0]))
    
    await send_top_users(message, page)

async def send_top_users(message: Message, page: int = 1):
    """Send top users leaderboard."""
    offset = (page - 1) * TOP_USERS_PER_PAGE
    top_users = await Database.get_top_users(TOP_USERS_PER_PAGE, offset)
    
    if not top_users:
        await message.reply("❌ Нет данных для отображения топа.")
        return
    
    # Build leaderboard text
    leaderboard_text = f"🏆 <b>Топ участников (страница {page})</b>\n\n"
    
    for i, user in enumerate(top_users, start=offset + 1):
        username = user['username']
        username_display = f"@{username}" if username else user['first_name'] or "Неизвестный"
        
        # Add medal for top 3
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        title = get_user_title(user['level'])
        
        leaderboard_text += f"{medal}<b>{i}.</b> {username_display}\n"
        leaderboard_text += f"    🏆 Уровень {user['level']} ({title})\n"
        leaderboard_text += f"    ⭐ {user['experience']} XP\n\n"
    
    # Create pagination keyboard
    keyboard = create_top_pagination_keyboard(page, len(top_users) == TOP_USERS_PER_PAGE)
    
    await message.reply(leaderboard_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("top_page:"))
async def top_page_callback(callback: CallbackQuery, **kwargs):
    """Handle top page navigation callbacks."""
    page = int(callback.data.split(":")[1])
    
    # Edit message with new page
    offset = (page - 1) * TOP_USERS_PER_PAGE
    top_users = await Database.get_top_users(TOP_USERS_PER_PAGE, offset)
    
    if not top_users:
        await callback.answer("❌ Нет данных для отображения.")
        return
    
    # Build leaderboard text
    leaderboard_text = f"🏆 <b>Топ участников (страница {page})</b>\n\n"
    
    for i, user in enumerate(top_users, start=offset + 1):
        username = user['username']
        username_display = f"@{username}" if username else user['first_name'] or "Неизвестный"
        
        # Add medal for top 3
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        title = get_user_title(user['level'])
        
        leaderboard_text += f"{medal}<b>{i}.</b> {username_display}\n"
        leaderboard_text += f"    🏆 Уровень {user['level']} ({title})\n"
        leaderboard_text += f"    ⭐ {user['experience']} XP\n\n"
    
    # Create pagination keyboard
    keyboard = create_top_pagination_keyboard(page, len(top_users) == TOP_USERS_PER_PAGE)
    
    try:
        await callback.message.edit_text(leaderboard_text, reply_markup=keyboard)
        await callback.answer()
    except Exception:
        await callback.answer("❌ Ошибка при обновлении страницы.")

def create_top_pagination_keyboard(current_page: int, has_next: bool) -> InlineKeyboardMarkup:
    """Create pagination keyboard for top users."""
    buttons = []
    
    # Previous page button
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"top_page:{current_page - 1}"
        ))
    
    # Current page indicator
    buttons.append(InlineKeyboardButton(
        text=f"📄 {current_page}",
        callback_data="noop"
    ))
    
    # Next page button
    if has_next:
        buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"top_page:{current_page + 1}"
        ))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

@router.message(Command("stats"))
async def stats_command(message: Message, **kwargs):
    """Handle /stats command to display message statistics."""
    user_id = message.from_user.id
    
    # Get user statistics
    daily_stats = await get_message_stats(user_id, 'day')
    weekly_stats = await get_message_stats(user_id, 'week')
    monthly_stats = await get_message_stats(user_id, 'month')
    
    stats_text = f"""
📊 <b>Статистика сообщений</b>

👤 {message.from_user.mention_html()}

📈 <b>Сообщения:</b>
📅 За сегодня: {daily_stats}
📅 За неделю: {weekly_stats}  
📅 За месяц: {monthly_stats}

💡 <i>Статистика обновляется каждый день</i>
    """
    
    await message.reply(stats_text)

async def get_message_stats(user_id: int, period: str) -> int:
    """Get message statistics for a user for a specific period."""
    import aiosqlite
    from config import DATABASE_PATH
    
    # Determine date condition based on period
    if period == 'day':
        date_condition = "message_date = date('now')"
    elif period == 'week':
        date_condition = "message_date >= date('now', '-7 days')"
    elif period == 'month':
        date_condition = "message_date >= date('now', '-30 days')"
    else:
        return 0
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(f"""
            SELECT COALESCE(SUM(message_count), 0)
            FROM message_stats
            WHERE user_id = ? AND {date_condition}
        """, (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Handle no-operation callbacks."""
    await callback.answer()