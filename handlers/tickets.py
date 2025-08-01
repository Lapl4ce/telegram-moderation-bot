from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import logging

from database.models import User, Ticket
from database.database import Database
from config import Config
from utils.validators import sanitize_text, format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("ticket"))
async def cmd_ticket(message: Message, user: User, db: Database):
    """Handle /ticket command - create support ticket"""
    
    # Check if command is used in private chat
    if message.chat.type != "private":
        await message.reply("❌ Команда /ticket работает только в личных сообщениях с ботом")
        return
    
    # Check if user is blocked from creating tickets
    if user.is_blocked_tickets:
        await message.reply("❌ Вы заблокированы от создания тикетов")
        return
    
    # Get ticket message
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("""
📋 **Создание тикета**

Для создания тикета используйте:
`/ticket ваше сообщение`

Пример:
`/ticket У меня проблема с модерацией`

Ваш тикет будет передан администраторам для рассмотрения.
""", parse_mode="Markdown")
        return
    
    ticket_message = sanitize_text(args[1])
    if len(ticket_message) < 10:
        await message.reply("❌ Сообщение тикета должно содержать минимум 10 символов")
        return
    
    # Create ticket in database
    ticket = Ticket(
        user_id=user.user_id,
        message=ticket_message
    )
    
    ticket_id = await db.create_ticket(ticket)
    
    # Send confirmation to user
    user_name = format_user_display_name(user.username, user.first_name, user.last_name)
    await message.reply(f"""
✅ **Тикет создан**

🆔 **ID тикета:** #{ticket_id}
📝 **Сообщение:** {ticket_message}

Ваш тикет отправлен администраторам. Ожидайте ответа.
""", parse_mode="Markdown")
    
    # Send ticket to admin group if configured
    if Config.TICKETS_GROUP_ID:
        try:
            admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ответить", callback_data=f"ticket_reply:{ticket_id}"),
                    InlineKeyboardButton(text="❌ Закрыть", callback_data=f"ticket_close:{ticket_id}")
                ],
                [
                    InlineKeyboardButton(text="🚫 Заблокировать пользователя", callback_data=f"ticket_block:{user.user_id}")
                ]
            ])
            
            admin_message = f"""
🎫 **Новый тикет #{ticket_id}**

👤 **От:** {user_name} (ID: `{user.user_id}`)
📝 **Сообщение:** {ticket_message}
📅 **Создан:** {ticket.created_at or "сейчас"}
"""
            
            # Send to admin group
            from aiogram import Bot
            bot = message.bot
            sent_message = await bot.send_message(
                Config.TICKETS_GROUP_ID,
                admin_message,
                parse_mode="Markdown",
                reply_markup=admin_keyboard
            )
            
            # Update ticket with admin message ID
            await db.update_ticket(ticket_id, admin_message_id=sent_message.message_id)
            
        except Exception as e:
            logger.error(f"Failed to send ticket to admin group: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("ticket_reply:"))
async def handle_ticket_reply_callback(callback: CallbackQuery, user: User, db: Database):
    """Handle ticket reply button"""
    try:
        ticket_id = int(callback.data.split(":")[1])
        
        await callback.message.reply(f"""
📝 **Ответ на тикет #{ticket_id}**

Для ответа на тикет используйте команду:
`/reply {ticket_id} ваш ответ`

Пример:
`/reply {ticket_id} Проблема решена, спасибо за обращение`
""", parse_mode="Markdown")
        
        await callback.answer()
        
    except (ValueError, IndexError):
        await callback.answer("Ошибка обработки тикета")

@router.callback_query(lambda c: c.data and c.data.startswith("ticket_close:"))
async def handle_ticket_close_callback(callback: CallbackQuery, user: User, db: Database):
    """Handle ticket close button"""
    try:
        ticket_id = int(callback.data.split(":")[1])
        
        # Update ticket status
        await db.update_ticket(ticket_id, status="closed")
        
        # Update the message
        original_text = callback.message.text
        updated_text = original_text + "\n\n❌ **Тикет закрыт**"
        
        await callback.message.edit_text(
            updated_text,
            parse_mode="Markdown"
        )
        
        await callback.answer("Тикет закрыт")
        
    except (ValueError, IndexError):
        await callback.answer("Ошибка закрытия тикета")
    except Exception as e:
        logger.error(f"Error closing ticket: {e}")
        await callback.answer("Ошибка при закрытии тикета")

@router.callback_query(lambda c: c.data and c.data.startswith("ticket_block:"))
async def handle_ticket_block_callback(callback: CallbackQuery, user: User, db: Database):
    """Handle ticket user block button"""
    # Only admins can block users
    from database.models import UserRight
    if user.rights not in [UserRight.ADMIN]:
        await callback.answer("❌ Недостаточно прав")
        return
    
    try:
        blocked_user_id = int(callback.data.split(":")[1])
        
        # Get the user and block them
        blocked_user = await db.get_or_create_user(blocked_user_id)
        blocked_user.is_blocked_tickets = True
        await db.update_user(blocked_user)
        
        # Update the message
        original_text = callback.message.text
        updated_text = original_text + f"\n\n🚫 **Пользователь заблокирован от создания тикетов администратором {format_user_display_name(user.username, user.first_name, user.last_name)}**"
        
        await callback.message.edit_text(
            updated_text,
            parse_mode="Markdown"
        )
        
        await callback.answer("Пользователь заблокирован от создания тикетов")
        
    except (ValueError, IndexError):
        await callback.answer("Ошибка блокировки пользователя")
    except Exception as e:
        logger.error(f"Error blocking user from tickets: {e}")
        await callback.answer("Ошибка при блокировке пользователя")

@router.message(Command("reply"))
async def cmd_reply(message: Message, user: User, db: Database):
    """Handle /reply command - reply to ticket"""
    
    # Only admins and moderators can reply to tickets
    from database.models import UserRight
    if user.rights not in [UserRight.ADMIN, UserRight.MODERATOR]:
        await message.reply("❌ Недостаточно прав для ответа на тикеты")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("""
📝 **Ответ на тикет**

Используйте: `/reply ID_тикета ваш_ответ`

Пример:
`/reply 123 Проблема решена, спасибо за обращение`
""", parse_mode="Markdown")
        return
    
    try:
        ticket_id = int(args[1])
        reply_text = sanitize_text(args[2])
        
        # Get ticket
        ticket = await db.get_ticket(ticket_id)
        if not ticket:
            await message.reply("❌ Тикет не найден")
            return
        
        if ticket.status == "closed":
            await message.reply("❌ Тикет уже закрыт")
            return
        
        # Send reply to user
        admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
        reply_message = f"""
📬 **Ответ на ваш тикет #{ticket_id}**

👤 **От:** {admin_name}
📝 **Ответ:** {reply_text}

Если у вас остались вопросы, создайте новый тикет.
"""
        
        try:
            await message.bot.send_message(
                ticket.user_id,
                reply_message,
                parse_mode="Markdown"
            )
            
            # Update ticket status
            await db.update_ticket(ticket_id, status="answered")
            
            await message.reply(f"✅ Ответ отправлен пользователю (тикет #{ticket_id})")
            
        except Exception as e:
            logger.error(f"Failed to send reply to user: {e}")
            await message.reply("❌ Не удалось отправить ответ пользователю")
    
    except ValueError:
        await message.reply("❌ Неверный ID тикета")
    except Exception as e:
        logger.error(f"Error replying to ticket: {e}")
        await message.reply("❌ Ошибка при ответе на тикет")