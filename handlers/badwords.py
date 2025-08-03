"""Bad words filtering handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, delete

from config import FORBIDDEN_WORDS
from database.database import get_db
from database.models import BannedWord, User
from utils.permissions import check_admin_permissions

router = Router()


@router.message(Command("add_badword"))
async def add_badword_command(message: Message, user_role: str):
    """Handle /add_badword command to add word to banned list."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply(
            "📝 <b>Добавление запрещенного слова</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/add_badword слово [тип_наказания]</code>\n\n"
            "📋 <b>Типы наказаний:</b>\n"
            "• <code>warn</code> - предупреждение (по умолчанию)\n"
            "• <code>mute</code> - заглушение\n"
            "• <code>ban</code> - бан\n\n"
            "📋 <b>Примеры:</b>\n"
            "<code>/add_badword спам</code>\n"
            "<code>/add_badword реклама mute</code>"
        )
        return
    
    word = args[1].lower().strip()
    severity = args[2].lower() if len(args) > 2 else "warn"
    
    if severity not in ["warn", "mute", "ban"]:
        await message.reply("❌ Неверный тип наказания. Доступные: warn, mute, ban")
        return
    
    if len(word) < 2:
        await message.reply("❌ Слово должно содержать минимум 2 символа.")
        return
    
    async for session in get_db():
        try:
            # Check if word already exists
            result = await session.execute(
                select(BannedWord).where(BannedWord.word == word)
            )
            existing_word = result.scalar_one_or_none()
            
            if existing_word:
                await message.reply(f"❌ Слово '{word}' уже в списке запрещенных.")
                return
            
            # Add new banned word
            banned_word = BannedWord(
                word=word,
                severity=severity
            )
            session.add(banned_word)
            await session.commit()
            
            severity_names = {
                "warn": "⚠️ Предупреждение",
                "mute": "🔇 Заглушение",
                "ban": "🚫 Бан"
            }
            
            await message.reply(
                f"✅ <b>Слово добавлено в список запрещенных</b>\n"
                f"📝 <b>Слово:</b> {word}\n"
                f"⚖️ <b>Наказание:</b> {severity_names[severity]}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при добавлении слова: {e}")


@router.message(Command("remove_badword"))
async def remove_badword_command(message: Message, user_role: str):
    """Handle /remove_badword command to remove word from banned list."""
    if not await check_admin_permissions(message, user_role):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            "📝 <b>Удаление запрещенного слова</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/remove_badword слово</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/remove_badword спам</code>"
        )
        return
    
    word = args[1].lower().strip()
    
    async for session in get_db():
        try:
            # Check if word exists
            result = await session.execute(
                select(BannedWord).where(BannedWord.word == word)
            )
            banned_word = result.scalar_one_or_none()
            
            if not banned_word:
                await message.reply(f"❌ Слово '{word}' не найдено в списке запрещенных.")
                return
            
            # Remove banned word
            await session.execute(
                delete(BannedWord).where(BannedWord.word == word)
            )
            await session.commit()
            
            await message.reply(
                f"✅ <b>Слово удалено из списка запрещенных</b>\n"
                f"📝 <b>Слово:</b> {word}"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при удалении слова: {e}")


@router.message(Command("list_badwords"))
async def list_badwords_command(message: Message, user_role: str):
    """Handle /list_badwords command to show all banned words."""
    if not await check_admin_permissions(message, user_role):
        return
    
    async for session in get_db():
        try:
            # Get all banned words
            result = await session.execute(
                select(BannedWord).order_by(BannedWord.word)
            )
            banned_words = result.scalars().all()
            
            if not banned_words:
                await message.reply("📋 Список запрещенных слов пуст.")
                return
            
            words_text = "📋 <b>Запрещенные слова:</b>\n\n"
            
            severity_names = {
                "warn": "⚠️",
                "mute": "🔇",
                "ban": "🚫"
            }
            
            for word in banned_words:
                severity_icon = severity_names.get(word.severity, "❓")
                words_text += f"{severity_icon} <code>{word.word}</code> — {word.severity}\n"
            
            await message.reply(words_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении списка слов: {e}")


async def check_message_for_badwords(message: Message):
    """Check message for banned words and apply punishment."""
    if not message.text or message.from_user.is_bot:
        return
    
    message_text = message.text.lower()
    
    async for session in get_db():
        try:
            # Get all banned words
            result = await session.execute(select(BannedWord))
            banned_words = result.scalars().all()
            
            # Check message against banned words
            found_words = []
            for banned_word in banned_words:
                if banned_word.word in message_text:
                    found_words.append(banned_word)
            
            # Also check config forbidden words
            for forbidden_word in FORBIDDEN_WORDS:
                if forbidden_word.lower() in message_text:
                    # Create temporary banned word object for config words
                    temp_word = BannedWord(word=forbidden_word, severity="warn")
                    found_words.append(temp_word)
            
            if not found_words:
                return
            
            # Delete the message
            try:
                await message.delete()
            except Exception:
                pass  # Bot might not have permission to delete
            
            # Apply punishment based on most severe word found
            severities = {"warn": 1, "mute": 2, "ban": 3}
            most_severe = max(found_words, key=lambda w: severities.get(w.severity, 1))
            
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name
            
            if most_severe.severity == "warn":
                # Add warning
                from sqlalchemy import update
                from database.models import ModerationAction
                
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    new_warns = user.warns + 1
                    await session.execute(
                        update(User)
                        .where(User.user_id == user_id)
                        .values(warns=new_warns)
                    )
                    
                    # Log action
                    action = ModerationAction(
                        target_user_id=user_id,
                        moderator_user_id=0,  # System action
                        action_type="warn",
                        reason=f"Использование запрещенного слова: {most_severe.word}"
                    )
                    session.add(action)
                    await session.commit()
                    
                    await message.reply(
                        f"⚠️ {username}, ваше сообщение удалено за использование запрещенных слов.\n"
                        f"Предупреждений: {new_warns}/3"
                    )
            
            elif most_severe.severity == "mute":
                # Mute user
                from datetime import datetime, timedelta
                from sqlalchemy import update
                from database.models import ModerationAction
                
                mute_until = datetime.utcnow() + timedelta(hours=1)
                
                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(is_muted=True, mute_until=mute_until)
                )
                
                # Log action
                action = ModerationAction(
                    target_user_id=user_id,
                    moderator_user_id=0,  # System action
                    action_type="mute",
                    reason=f"Использование запрещенного слова: {most_severe.word}",
                    duration=3600
                )
                session.add(action)
                await session.commit()
                
                await message.reply(
                    f"🔇 {username}, вы заглушены на 1 час за использование запрещенных слов."
                )
            
            elif most_severe.severity == "ban":
                # Ban user
                from datetime import datetime, timedelta
                from sqlalchemy import update
                from database.models import ModerationAction
                
                ban_until = datetime.utcnow() + timedelta(days=1)
                
                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(is_banned=True, ban_until=ban_until)
                )
                
                # Log action
                action = ModerationAction(
                    target_user_id=user_id,
                    moderator_user_id=0,  # System action
                    action_type="ban",
                    reason=f"Использование запрещенного слова: {most_severe.word}",
                    duration=86400
                )
                session.add(action)
                await session.commit()
                
                await message.reply(
                    f"🚫 {username}, вы заблокированы на 1 день за использование запрещенных слов."
                )
                
        except Exception as e:
            await session.rollback()
            print(f"Error checking for bad words: {e}")


# Register message handler for all text messages
@router.message()
async def message_handler(message: Message):
    """Handle all messages to check for banned words and restrictions."""
    # Check for sticker restriction (level 25 requirement)
    if message.sticker and message.from_user and not message.from_user.is_bot:
        async for session in get_db():
            try:
                result = await session.execute(
                    select(User).where(User.user_id == message.from_user.id)
                )
                user = result.scalar_one_or_none()
                
                if user and user.level < 25:
                    try:
                        await message.delete()
                        await message.reply(
                            f"🚫 Стикеры доступны с 25 уровня.\n"
                            f"Ваш уровень: {user.level}/25"
                        )
                    except Exception:
                        pass
                    return
            except Exception as e:
                print(f"Error checking sticker restriction: {e}")
    
    # Check for banned words
    await check_message_for_badwords(message)