"""Top/leaderboard handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from database.database import get_db
from database.models import User
from utils.titles import get_title_by_level

router = Router()

USERS_PER_PAGE = 10


@router.message(Command("top"))
async def top_command(message: Message):
    """Handle /top command to show user leaderboard."""
    await show_top_page(message, 0)


async def show_top_page(message: Message, page: int):
    """Show top users page with pagination."""
    async for session in get_db():
        try:
            offset = page * USERS_PER_PAGE
            
            # Get total count
            result = await session.execute(select(User).where(User.level > 0))
            total_users = len(result.scalars().all())
            
            # Get users for current page
            result = await session.execute(
                select(User)
                .where(User.level > 0)
                .order_by(User.level.desc(), User.experience.desc())
                .offset(offset)
                .limit(USERS_PER_PAGE)
            )
            users = result.scalars().all()
            
            if not users:
                await message.reply("📊 В рейтинге пока нет пользователей.")
                return
            
            # Calculate page info
            total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
            current_page = page + 1
            
            # Create leaderboard text
            top_text = f"🏆 <b>Рейтинг пользователей</b>\n"
            top_text += f"📄 Страница {current_page}/{total_pages}\n\n"
            
            for i, user in enumerate(users, start=offset + 1):
                # Medal for top 3
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"{i}."
                
                # User info
                display_name = user.first_name or "Неизвестно"
                if user.username:
                    display_name = f"@{user.username}"
                
                title = get_title_by_level(user.level)
                
                top_text += (
                    f"{medal} <b>{display_name}</b>\n"
                    f"   📊 {user.level} ур. • 💎 {user.experience:,} XP\n"
                    f"   🏆 {title}\n\n"
                )
            
            # Create pagination keyboard
            keyboard = []
            nav_buttons = []
            
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton(text="⬅️ Назад", callback_data=f"top_page_{page-1}")
                )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton(text="Вперед ➡️", callback_data=f"top_page_{page+1}")
                )
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            # Add page info button
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📄 {current_page}/{total_pages}",
                    callback_data="top_page_info"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
            
            if hasattr(message, 'edit_text'):
                # This is a callback query edit
                await message.edit_text(top_text, reply_markup=reply_markup)
            else:
                # This is a new message
                await message.reply(top_text, reply_markup=reply_markup)
                
        except Exception as e:
            error_msg = f"❌ Ошибка при получении рейтинга: {e}"
            if hasattr(message, 'edit_text'):
                await message.edit_text(error_msg)
            else:
                await message.reply(error_msg)


@router.callback_query(lambda c: c.data.startswith("top_page_"))
async def top_page_callback(callback: CallbackQuery):
    """Handle top page navigation callbacks."""
    try:
        if callback.data == "top_page_info":
            await callback.answer("ℹ️ Информация о странице", show_alert=False)
            return
        
        page = int(callback.data.split("_")[-1])
        await show_top_page(callback.message, page)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.message(Command("my_rank"))
async def my_rank_command(message: Message):
    """Handle /my_rank command to show user's rank."""
    user_id = message.from_user.id
    
    async for session in get_db():
        try:
            # Get user's data
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or user.level == 0:
                await message.reply("📊 Вы еще не в рейтинге. Начните писать сообщения, чтобы получать опыт!")
                return
            
            # Get users with higher rank
            result = await session.execute(
                select(User)
                .where(
                    (User.level > user.level) |
                    ((User.level == user.level) & (User.experience > user.experience))
                )
                .where(User.level > 0)
            )
            higher_users = len(result.scalars().all())
            
            user_rank = higher_users + 1
            
            # Get total users in ranking
            result = await session.execute(
                select(User).where(User.level > 0)
            )
            total_users = len(result.scalars().all())
            
            title = get_title_by_level(user.level)
            
            rank_text = (
                f"📊 <b>Ваша позиция в рейтинге</b>\n\n"
                f"🏆 <b>Место:</b> {user_rank} из {total_users}\n"
                f"📊 <b>Уровень:</b> {user.level}\n"
                f"💎 <b>Опыт:</b> {user.experience:,} XP\n"
                f"🏆 <b>Титул:</b> {title}\n\n"
            )
            
            # Calculate percentage
            if total_users > 1:
                percentile = ((total_users - user_rank) / (total_users - 1)) * 100
                rank_text += f"📈 <b>Лучше чем:</b> {percentile:.1f}% пользователей"
            
            await message.reply(rank_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении ранга: {e}")