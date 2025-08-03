"""Ticket system handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update

from config import TICKET_GROUP_ID
from database.database import get_db
from database.models import Ticket, TicketResponse
from utils.permissions import can_access_tickets

router = Router()


@router.message(Command("ticket"))
async def ticket_command(message: Message):
    """Handle /ticket command - only works in private messages."""
    if message.chat.type != "private":
        await message.reply(
            "🎫 Создание тикетов доступно только в личных сообщениях с ботом.\n"
            "Напишите боту в ЛС и используйте команду /ticket там."
        )
        return
    
    # Get message after /ticket command
    ticket_text = message.text[7:].strip()  # Remove "/ticket" from the beginning
    
    if not ticket_text:
        await message.reply(
            "📝 <b>Создание тикета</b>\n\n"
            "Для создания тикета отправьте сообщение в формате:\n"
            "<code>/ticket Ваше сообщение</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/ticket У меня проблема с доступом к каналу</code>"
        )
        return
    
    # Create ticket in database
    async for session in get_db():
        try:
            ticket = Ticket(
                user_id=message.from_user.id,
                username=message.from_user.username,
                message=ticket_text,
                status="open"
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            
            # Send ticket to admin group if configured
            if TICKET_GROUP_ID:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📋 Взять в работу",
                            callback_data=f"ticket_take_{ticket.id}"
                        ),
                        InlineKeyboardButton(
                            text="✅ Закрыть",
                            callback_data=f"ticket_close_{ticket.id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="💬 Ответить",
                            callback_data=f"ticket_reply_{ticket.id}"
                        )
                    ]
                ])
                
                ticket_text_admin = (
                    f"🎫 <b>Новый тикет #{ticket.id}</b>\n\n"
                    f"👤 <b>От:</b> {message.from_user.first_name or 'Неизвестно'}"
                )
                
                if message.from_user.username:
                    ticket_text_admin += f" (@{message.from_user.username})"
                
                ticket_text_admin += f"\n🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n\n"
                ticket_text_admin += f"📝 <b>Сообщение:</b>\n{ticket_text}"
                
                # Send to admin group
                try:
                    from aiogram import Bot
                    from config import BOT_TOKEN
                    bot = Bot(token=BOT_TOKEN)
                    sent_message = await bot.send_message(
                        chat_id=TICKET_GROUP_ID,
                        text=ticket_text_admin,
                        reply_markup=keyboard
                    )
                    
                    # Save message ID for future reference
                    await session.execute(
                        update(Ticket)
                        .where(Ticket.id == ticket.id)
                        .values(telegram_message_id=sent_message.message_id)
                    )
                    await session.commit()
                    
                except Exception as e:
                    print(f"Error sending ticket to admin group: {e}")
            
            await message.reply(
                f"✅ <b>Тикет #{ticket.id} создан!</b>\n\n"
                f"📝 <b>Ваше сообщение:</b>\n{ticket_text}\n\n"
                f"⏳ Ожидайте ответа от администраторов."
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при создании тикета: {e}")


@router.callback_query(lambda c: c.data.startswith("ticket_"))
async def ticket_callback_handler(callback: CallbackQuery, user_role: str):
    """Handle ticket callback buttons."""
    if not can_access_tickets(user_role):
        await callback.answer("❌ У вас нет прав для работы с тикетами.", show_alert=True)
        return
    
    action_data = callback.data.split("_")
    action = action_data[1]
    ticket_id = int(action_data[2])
    
    async for session in get_db():
        try:
            # Get ticket
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                await callback.answer("❌ Тикет не найден.", show_alert=True)
                return
            
            if action == "take":
                if ticket.status != "open":
                    await callback.answer("❌ Тикет уже взят в работу или закрыт.", show_alert=True)
                    return
                
                # Take ticket
                await session.execute(
                    update(Ticket)
                    .where(Ticket.id == ticket_id)
                    .values(status="in_progress", assigned_to=callback.from_user.id)
                )
                await session.commit()
                
                # Update message
                new_text = callback.message.text + f"\n\n🔄 <b>Взят в работу:</b> {callback.from_user.first_name}"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Закрыть",
                            callback_data=f"ticket_close_{ticket.id}"
                        ),
                        InlineKeyboardButton(
                            text="💬 Ответить",
                            callback_data=f"ticket_reply_{ticket.id}"
                        )
                    ]
                ])
                
                await callback.message.edit_text(new_text, reply_markup=keyboard)
                await callback.answer("✅ Тикет взят в работу!")
                
            elif action == "close":
                # Close ticket
                await session.execute(
                    update(Ticket)
                    .where(Ticket.id == ticket_id)
                    .values(status="closed")
                )
                await session.commit()
                
                # Update message
                new_text = callback.message.text + f"\n\n✅ <b>Закрыт:</b> {callback.from_user.first_name}"
                
                await callback.message.edit_text(new_text, reply_markup=None)
                await callback.answer("✅ Тикет закрыт!")
                
                # Notify user
                try:
                    from aiogram import Bot
                    from config import BOT_TOKEN
                    bot = Bot(token=BOT_TOKEN)
                    await bot.send_message(
                        chat_id=ticket.user_id,
                        text=f"✅ <b>Тикет #{ticket.id} закрыт</b>\n\nСпасибо за обращение!"
                    )
                except Exception as e:
                    print(f"Error notifying user about ticket closure: {e}")
                
            elif action == "reply":
                await callback.answer(
                    f"💬 Для ответа на тикет #{ticket.id} используйте команду:\n"
                    f"/reply {ticket.id} Ваш ответ",
                    show_alert=True
                )
                
        except Exception as e:
            await session.rollback()
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.message(Command("reply"))
async def reply_command(message: Message, user_role: str):
    """Handle /reply command for responding to tickets."""
    if not can_access_tickets(user_role):
        await message.reply("❌ У вас нет прав для ответа на тикеты.")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply(
            "📝 <b>Ответ на тикет</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/reply номер_тикета ваш_ответ</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/reply 123 Ваша проблема решена</code>"
        )
        return
    
    try:
        ticket_id = int(args[1])
        reply_text = args[2]
    except ValueError:
        await message.reply("❌ Неверный номер тикета.")
        return
    
    async for session in get_db():
        try:
            # Get ticket
            result = await session.execute(
                select(Ticket).where(Ticket.id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            
            if not ticket:
                await message.reply("❌ Тикет не найден.")
                return
            
            if ticket.status == "closed":
                await message.reply("❌ Тикет уже закрыт.")
                return
            
            # Create response
            response = TicketResponse(
                ticket_id=ticket_id,
                responder_user_id=message.from_user.id,
                message=reply_text
            )
            session.add(response)
            await session.commit()
            
            # Send response to user
            try:
                from aiogram import Bot
                from config import BOT_TOKEN
                bot = Bot(token=BOT_TOKEN)
                await bot.send_message(
                    chat_id=ticket.user_id,
                    text=(
                        f"💬 <b>Ответ на тикет #{ticket.id}</b>\n\n"
                        f"👤 <b>От:</b> {message.from_user.first_name}\n\n"
                        f"📝 <b>Сообщение:</b>\n{reply_text}"
                    )
                )
                
                await message.reply(
                    f"✅ Ответ отправлен пользователю\n"
                    f"🎫 <b>Тикет:</b> #{ticket.id}"
                )
                
            except Exception as e:
                await message.reply(f"❌ Ошибка при отправке ответа: {e}")
                
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при обработке ответа: {e}")


@router.message(Command("tickets"))
async def tickets_list_command(message: Message, user_role: str):
    """Handle /tickets command to list open tickets."""
    if not can_access_tickets(user_role):
        await message.reply("❌ У вас нет прав для просмотра тикетов.")
        return
    
    async for session in get_db():
        try:
            # Get open tickets
            result = await session.execute(
                select(Ticket)
                .where(Ticket.status.in_(["open", "in_progress"]))
                .order_by(Ticket.created_at.desc())
                .limit(10)
            )
            tickets = result.scalars().all()
            
            if not tickets:
                await message.reply("📋 Нет открытых тикетов.")
                return
            
            tickets_text = "📋 <b>Открытые тикеты:</b>\n\n"
            
            for ticket in tickets:
                status_emoji = "🟡" if ticket.status == "open" else "🔄"
                tickets_text += (
                    f"{status_emoji} <b>#{ticket.id}</b> - {ticket.status}\n"
                    f"👤 {ticket.username or 'Неизвестно'} (ID: {ticket.user_id})\n"
                    f"📅 {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"📝 {ticket.message[:50]}{'...' if len(ticket.message) > 50 else ''}\n\n"
                )
            
            await message.reply(tickets_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении списка тикетов: {e}")