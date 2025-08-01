from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import logging

from database.models import User
from database.database import Database
from utils.validators import format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

USERS_PER_PAGE = 10

@router.message(Command("top"))
async def cmd_top(message: Message, user: User, db: Database):
    """Handle /top command - show top users by experience"""
    await show_top_page(message, db, 0, user.user_id)

async def show_top_page(message_or_query, db: Database, page: int, requester_id: int):
    """Show a specific page of top users"""
    offset = page * USERS_PER_PAGE
    top_users = await db.get_top_users(USERS_PER_PAGE, offset)
    
    if not top_users:
        text = "📊 Топ пользователей пуст"
        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.answer("Нет данных для этой страницы")
            return
        else:
            await message_or_query.reply(text)
            return
    
    # Get requester's rank
    requester_rank = await db.get_user_rank(requester_id)
    
    text = f"🏆 **Топ пользователей по опыту** (страница {page + 1})\n\n"
    
    for i, top_user in enumerate(top_users):
        position = offset + i + 1
        display_name = format_user_display_name(
            top_user.username, 
            top_user.first_name, 
            top_user.last_name,
            top_user.user_id
        )
        
        # Add medal emojis for top 3
        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"
        else:
            medal = f"{position}."
        
        # Highlight current user
        if top_user.user_id == requester_id:
            text += f"➤ **{medal} {display_name}**\n"
        else:
            text += f"{medal} {display_name}\n"
        
        text += f"   🏆 Уровень {top_user.level} • ⭐ {top_user.experience:,} XP\n\n"
    
    # Add requester's position if not in current page
    if requester_rank and (requester_rank <= offset or requester_rank > offset + USERS_PER_PAGE):
        text += f"─────────────────\n"
        text += f"👤 **Ваша позиция:** #{requester_rank}\n"
    
    # Create navigation buttons
    keyboard = []
    nav_buttons = []
    
    # Previous page button
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"top_page:{page-1}")
        )
    
    # Next page button (check if there might be more users)
    if len(top_users) == USERS_PER_PAGE:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"top_page:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add refresh button
    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"top_page:{page}")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    if isinstance(message_or_query, CallbackQuery):
        try:
            await message_or_query.message.edit_text(
                text, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            # If edit fails, send new message
            await message_or_query.message.reply(
                text,
                parse_mode="Markdown", 
                reply_markup=reply_markup
            )
        await message_or_query.answer()
    else:
        await message_or_query.reply(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

@router.callback_query(lambda c: c.data and c.data.startswith("top_page:"))
async def handle_top_page_callback(callback: CallbackQuery, user: User, db: Database):
    """Handle top page navigation callbacks"""
    try:
        page = int(callback.data.split(":")[1])
        await show_top_page(callback, db, page, user.user_id)
    except (ValueError, IndexError):
        await callback.answer("Ошибка навигации")

@router.message(Command("toplevel"))
async def cmd_top_level(message: Message, user: User, db: Database):
    """Handle /toplevel command - show top users by level"""
    # This is similar to /top but sorts by level instead of experience
    # For simplicity, we'll use the same logic but modify the query
    # You could extend the database to support different sorting
    await show_top_level_page(message, db, 0, user.user_id)

async def show_top_level_page(message_or_query, db: Database, page: int, requester_id: int):
    """Show a specific page of top users by level"""
    # Note: This is a simplified version. You might want to add a separate 
    # database method for sorting by level
    offset = page * USERS_PER_PAGE
    
    # For now, we'll get top users and sort by level in Python
    # In a real implementation, you'd want to do this in the database
    all_top_users = await db.get_top_users(1000, 0)  # Get more users
    top_users_by_level = sorted(all_top_users, key=lambda u: (-u.level, -u.experience))
    top_users = top_users_by_level[offset:offset + USERS_PER_PAGE]
    
    if not top_users:
        text = "📊 Топ пользователей по уровню пуст"
        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.answer("Нет данных для этой страницы")
            return
        else:
            await message_or_query.reply(text)
            return
    
    text = f"🏆 **Топ пользователей по уровню** (страница {page + 1})\n\n"
    
    for i, top_user in enumerate(top_users):
        position = offset + i + 1
        display_name = format_user_display_name(
            top_user.username, 
            top_user.first_name, 
            top_user.last_name,
            top_user.user_id
        )
        
        # Add medal emojis for top 3
        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"
        else:
            medal = f"{position}."
        
        # Highlight current user
        if top_user.user_id == requester_id:
            text += f"➤ **{medal} {display_name}**\n"
        else:
            text += f"{medal} {display_name}\n"
        
        text += f"   🏆 Уровень {top_user.level} • ⭐ {top_user.experience:,} XP\n\n"
    
    # Create navigation buttons
    keyboard = []
    nav_buttons = []
    
    # Previous page button
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"toplevel_page:{page-1}")
        )
    
    # Next page button
    if len(top_users) == USERS_PER_PAGE and offset + USERS_PER_PAGE < len(top_users_by_level):
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"toplevel_page:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add refresh button
    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"toplevel_page:{page}")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    if isinstance(message_or_query, CallbackQuery):
        try:
            await message_or_query.message.edit_text(
                text, 
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            await message_or_query.message.reply(
                text,
                parse_mode="Markdown", 
                reply_markup=reply_markup
            )
        await message_or_query.answer()
    else:
        await message_or_query.reply(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

@router.callback_query(lambda c: c.data and c.data.startswith("toplevel_page:"))
async def handle_top_level_page_callback(callback: CallbackQuery, user: User, db: Database):
    """Handle top level page navigation callbacks"""
    try:
        page = int(callback.data.split(":")[1])
        await show_top_level_page(callback, db, page, user.user_id)
    except (ValueError, IndexError):
        await callback.answer("Ошибка навигации")