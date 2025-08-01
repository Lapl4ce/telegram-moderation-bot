"""
Ticket system handlers for the Telegram moderation bot.
Handles ticket creation, management, and responses.
"""
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from middleware.auth import moderator_required
from database.database import Database
from config import MODERATOR_GROUP_ID

router = Router()

class TicketStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_message = State()

@router.message(Command("ticket"))
async def ticket_command(message: Message, state: FSMContext, **kwargs):
    """Handle /ticket command to start ticket creation process."""
    # Only work in private messages
    if message.chat.type != 'private':
        await message.reply("🎫 Для создания тикета напишите мне в личные сообщения: /ticket")
        return
    
    await message.reply(
        "🎫 <b>Создание тикета поддержки</b>\n\n"
        "📝 Введите краткую тему вашего обращения:"
    )
    await state.set_state(TicketStates.waiting_for_subject)

@router.message(TicketStates.waiting_for_subject)
async def process_ticket_subject(message: Message, state: FSMContext, **kwargs):
    """Process ticket subject input."""
    if not message.text or len(message.text.strip()) < 3:
        await message.reply("❌ Тема должна содержать минимум 3 символа. Попробуйте еще раз:")
        return
    
    await state.update_data(subject=message.text.strip())
    await message.reply(
        "📋 <b>Тема получена!</b>\n\n"
        "📝 Теперь опишите вашу проблему подробно:"
    )
    await state.set_state(TicketStates.waiting_for_message)

@router.message(TicketStates.waiting_for_message)
async def process_ticket_message(message: Message, state: FSMContext, **kwargs):
    """Process ticket message and create the ticket."""
    if not message.text or len(message.text.strip()) < 10:
        await message.reply("❌ Описание должно содержать минимум 10 символов. Попробуйте еще раз:")
        return
    
    # Get ticket data
    data = await state.get_data()
    subject = data.get('subject')
    ticket_message = message.text.strip()
    user_id = message.from_user.id
    
    # Create ticket in database
    ticket_id = await Database.create_ticket(user_id, subject, ticket_message)
    
    # Clear state
    await state.clear()
    
    # Send confirmation to user
    await message.reply(
        f"✅ <b>Тикет создан!</b>\n\n"
        f"🎫 <b>Номер тикета:</b> #{ticket_id}\n"
        f"📋 <b>Тема:</b> {subject}\n\n"
        f"⏰ Ваше обращение передано модераторам. "
        f"Ожидайте ответа в течение 24 часов."
    )
    
    # Send ticket to moderator group
    if MODERATOR_GROUP_ID:
        await send_ticket_to_moderators(message.bot, ticket_id, user_id, subject, ticket_message)

async def send_ticket_to_moderators(bot, ticket_id: int, user_id: int, subject: str, ticket_message: str):
    """Send new ticket notification to moderator group."""
    # Get user info
    user_data = await Database.get_user(user_id)
    username = user_data.get('username') if user_data else None
    first_name = user_data.get('first_name') if user_data else 'Неизвестный'
    
    user_display = f"@{username}" if username else first_name
    
    moderator_text = f"""
🎫 <b>Новый тикет #{ticket_id}</b>

👤 <b>От:</b> {user_display} (<code>{user_id}</code>)
📋 <b>Тема:</b> {subject}

📝 <b>Сообщение:</b>
{ticket_message}
    """
    
    # Create inline keyboard for moderator actions
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Взять в работу",
                callback_data=f"ticket_assign:{ticket_id}"
            ),
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data=f"ticket_close:{ticket_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💬 Ответить",
                callback_data=f"ticket_reply:{ticket_id}"
            )
        ]
    ])
    
    try:
        await bot.send_message(
            chat_id=MODERATOR_GROUP_ID,
            text=moderator_text,
            reply_markup=keyboard
        )
    except Exception as e:
        # Log error but don't fail ticket creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send ticket to moderator group: {e}")

@router.callback_query(F.data.startswith("ticket_assign:"))
async def ticket_assign_callback(callback: CallbackQuery, **kwargs):
    """Handle ticket assignment callback."""
    if not kwargs.get('is_moderator', False):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    ticket_id = int(callback.data.split(":")[1])
    moderator_id = callback.from_user.id
    
    # Update ticket assignment in database
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE tickets SET assigned_moderator = ?
            WHERE id = ? AND status = 'open'
        """, (moderator_id, ticket_id))
        await db.commit()
    
    # Update message to show assignment
    current_text = callback.message.text or callback.message.caption
    updated_text = f"{current_text}\n\n👮 <b>Взято в работу:</b> {callback.from_user.mention_html()}"
    
    # Update keyboard to remove assign button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Закрыть",
                callback_data=f"ticket_close:{ticket_id}"
            ),
            InlineKeyboardButton(
                text="💬 Ответить",
                callback_data=f"ticket_reply:{ticket_id}"
            )
        ]
    ])
    
    try:
        await callback.message.edit_text(updated_text, reply_markup=keyboard)
        await callback.answer("✅ Тикет взят в работу")
    except Exception:
        await callback.answer("❌ Ошибка при обновлении тикета")

@router.callback_query(F.data.startswith("ticket_close:"))
async def ticket_close_callback(callback: CallbackQuery, **kwargs):
    """Handle ticket closing callback."""
    if not kwargs.get('is_moderator', False):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    ticket_id = int(callback.data.split(":")[1])
    
    # Close ticket in database
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get ticket info first
        async with db.execute("SELECT user_id FROM tickets WHERE id = ?", (ticket_id,)) as cursor:
            ticket_row = await cursor.fetchone()
        
        if not ticket_row:
            await callback.answer("❌ Тикет не найден")
            return
        
        user_id = ticket_row[0]
        
        # Close the ticket
        await db.execute("""
            UPDATE tickets SET status = 'closed', close_date = strftime('%s', 'now')
            WHERE id = ?
        """, (ticket_id,))
        await db.commit()
    
    # Update message
    current_text = callback.message.text or callback.message.caption
    updated_text = f"{current_text}\n\n❌ <b>Закрыт:</b> {callback.from_user.mention_html()}"
    
    try:
        await callback.message.edit_text(updated_text, reply_markup=None)
        await callback.answer("✅ Тикет закрыт")
        
        # Notify user about closure
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=f"❌ <b>Тикет #{ticket_id} закрыт</b>\n\n"
                     f"Если у вас остались вопросы, создайте новый тикет командой /ticket"
            )
        except Exception:
            pass  # Ignore if we can't send to user
            
    except Exception:
        await callback.answer("❌ Ошибка при закрытии тикета")

@router.message(Command("reply"))
@moderator_required
async def reply_command(message: Message, **kwargs):
    """Handle /reply command to respond to a ticket."""
    args = message.text.split(maxsplit=2)[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/reply [номер_тикета] [ответ]</code>\n"
            "🔍 Пример: <code>/reply 123 Ваш вопрос решен</code>"
        )
        return
    
    try:
        ticket_id = int(args[0])
        reply_text = args[1]
    except ValueError:
        await message.reply("❌ Неверный номер тикета.")
        return
    
    # Get ticket info
    ticket = await Database.get_ticket(ticket_id)
    if not ticket:
        await message.reply("❌ Тикет не найден.")
        return
    
    if ticket['status'] != 'open':
        await message.reply("❌ Тикет уже закрыт.")
        return
    
    # Send reply to user
    user_id = ticket['user_id']
    moderator = message.from_user
    
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"💬 <b>Ответ на тикет #{ticket_id}</b>\n\n"
                 f"👮 <b>От модератора:</b> {moderator.mention_html()}\n\n"
                 f"📝 <b>Ответ:</b>\n{reply_text}\n\n"
                 f"💡 Если у вас есть дополнительные вопросы, создайте новый тикет."
        )
        
        await message.reply(f"✅ Ответ на тикет #{ticket_id} отправлен пользователю.")
        
    except Exception as e:
        await message.reply(f"❌ Не удалось отправить ответ пользователю: {str(e)}")

@router.callback_query(F.data.startswith("ticket_reply:"))
async def ticket_reply_callback(callback: CallbackQuery, **kwargs):
    """Handle ticket reply button callback."""
    if not kwargs.get('is_moderator', False):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    ticket_id = int(callback.data.split(":")[1])
    
    await callback.answer(
        f"💬 Для ответа на тикет используйте команду:\n/reply {ticket_id} [ваш_ответ]",
        show_alert=True
    )