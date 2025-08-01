from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.models import User, UserRight
from database.database import Database
from middleware.auth import require_art_leader
from utils.validators import extract_user_id, format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

async def get_target_user_art(message: Message, db: Database, args: list) -> User:
    """Get target user for art points commands"""
    target_user = None
    
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_user = await db.get_or_create_user(
            user_id=target_user_id,
            username=message.reply_to_message.from_user.username,
            first_name=message.reply_to_message.from_user.first_name,
            last_name=message.reply_to_message.from_user.last_name
        )
    elif args:
        # Try to extract user ID from first argument
        user_id = extract_user_id(args[0])
        if user_id:
            target_user = await db.get_or_create_user(user_id=user_id)
    
    return target_user

@router.message(Command("modify_artpoints"))
@require_art_leader
async def cmd_modify_artpoints(message: Message, user: User, db: Database):
    """Handle /modify_artpoints command - modify user art points"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
🎨 **Изменение арт-очков**

Используйте: `/modify_artpoints пользователь количество`

Пример:
`/modify_artpoints @username +50` - добавить 50 арт-очков
`/modify_artpoints 123456789 -20` - убрать 20 арт-очков
`/modify_artpoints @username =100` - установить 100 арт-очков

Только арт-лидеры и администраторы могут изменять арт-очки.
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_art(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Parse art points amount
    points_str = args[1] if len(args) > 1 else args[0]
    
    try:
        old_points = target_user.art_points
        
        if points_str.startswith('+'):
            # Add art points
            amount = int(points_str[1:])
            target_user.art_points += amount
            operation = f"добавлено {amount}"
        elif points_str.startswith('-'):
            # Subtract art points
            amount = int(points_str[1:])
            target_user.art_points = max(0, target_user.art_points - amount)
            operation = f"убрано {amount}"
        elif points_str.startswith('='):
            # Set art points
            amount = int(points_str[1:])
            target_user.art_points = max(0, amount)
            operation = f"установлено {amount}"
        else:
            # Default to setting art points
            amount = int(points_str)
            target_user.art_points = max(0, amount)
            operation = f"установлено {amount}"
        
        # Update in database
        await db.update_user(target_user)
        
        target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
        
        # Determine who made the change
        if user.rights == UserRight.ART_LEADER:
            modifier_title = "Арт-лидер"
        else:
            modifier_title = "Администратор"
        
        modifier_name = format_user_display_name(user.username, user.first_name, user.last_name)
        
        result_text = f"""
🎨 **Арт-очки изменены**

👤 **Пользователь:** {target_name}
🎨 **{modifier_title}:** {modifier_name}

📊 **Изменения:**
• Арт-очки: {old_points} → {target_user.art_points}
• Операция: {operation}
"""
        
        await message.reply(result_text, parse_mode="Markdown")
        
    except ValueError:
        await message.reply("❌ Неверный формат количества арт-очков")
    except Exception as e:
        logger.error(f"Error modifying art points: {e}")
        await message.reply("❌ Ошибка при изменении арт-очков")

@router.message(Command("artpoints"))
async def cmd_artpoints(message: Message, user: User, db: Database):
    """Handle /artpoints command - show user's art points"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user (self if no args)
    if args:
        target_user = await get_target_user_art(message, db, args)
        if not target_user:
            await message.reply("❌ Пользователь не найден")
            return
    else:
        target_user = user
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    
    if target_user.user_id == user.user_id:
        points_text = f"""
🎨 **Ваши арт-очки**

💎 **Количество:** {target_user.art_points}

Арт-очки выдаются за творческие работы и участие в арт-активностях сообщества.
"""
    else:
        points_text = f"""
🎨 **Арт-очки пользователя**

👤 **Пользователь:** {target_name}
💎 **Количество:** {target_user.art_points}
"""
    
    await message.reply(points_text, parse_mode="Markdown")

@router.message(Command("topartpoints"))
async def cmd_top_artpoints(message: Message, user: User, db: Database):
    """Handle /topartpoints command - show top users by art points"""
    
    # Get top users and sort by art points
    # For simplicity, we'll get many users and sort in Python
    # In production, you'd want to add this to the database layer
    all_users = await db.get_top_users(1000, 0)
    top_art_users = sorted([u for u in all_users if u.art_points > 0], key=lambda u: u.art_points, reverse=True)[:10]
    
    if not top_art_users:
        await message.reply("🎨 Пока никто не имеет арт-очков")
        return
    
    text = "🎨 **Топ пользователей по арт-очкам**\n\n"
    
    for i, top_user in enumerate(top_art_users):
        position = i + 1
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
        if top_user.user_id == user.user_id:
            text += f"➤ **{medal} {display_name}**\n"
        else:
            text += f"{medal} {display_name}\n"
        
        text += f"   💎 {top_user.art_points} арт-очков\n\n"
    
    await message.reply(text, parse_mode="Markdown")