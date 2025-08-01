"""
Admin handlers for the Telegram moderation bot.
Handles administrative commands like experience modification, rights management, etc.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from middleware.auth import admin_required
from database.database import Database
from utils.experience import modify_user_experience, set_user_level, set_xp_multiplier
from utils.user_parser import parse_username
from config import MIN_XP_MULTIPLIER, MAX_XP_MULTIPLIER

router = Router()

@router.message(Command("xpmodify"))
@admin_required
async def xpmodify_command(message: Message, **kwargs):
    """Handle /xpmodify command to modify user experience."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/xpmodify [@username|user_id] [количество]</code>\n"
            "🔍 Пример: <code>/xpmodify @user +500</code> или <code>/xpmodify 123456 -100</code>"
        )
        return
    
    # Parse target user
    target_arg = args[0]
    target_user_id = None
    
    if target_arg.startswith('@'):
        target_user_id = await get_user_id_by_username(target_arg[1:])
    elif target_arg.isdigit():
        target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Parse XP amount
    try:
        xp_change = int(args[1])
    except ValueError:
        await message.reply("❌ Неверное количество опыта.")
        return
    
    # Get user data before modification
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    old_exp = user_data.get('experience', 0)
    old_level = user_data.get('level', 1)
    
    # Apply modification
    success = await modify_user_experience(target_user_id, xp_change)
    
    if not success:
        await message.reply("❌ Ошибка при изменении опыта.")
        return
    
    # Get updated data
    updated_user_data = await Database.get_user(target_user_id)
    new_exp = updated_user_data.get('experience', 0)
    new_level = updated_user_data.get('level', 1)
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    change_text = f"+{xp_change}" if xp_change > 0 else str(xp_change)
    level_change = ""
    if new_level != old_level:
        level_change = f"\n🏆 <b>Уровень изменен:</b> {old_level} → {new_level}"
    
    success_text = f"""
✅ <b>Опыт изменен</b>

👤 <b>Пользователь:</b> {target_display}
⭐ <b>Изменение:</b> {change_text} XP
📊 <b>Опыт:</b> {old_exp} → {new_exp} XP{level_change}
👮 <b>Администратор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("levelmodify"))
@admin_required
async def levelmodify_command(message: Message, **kwargs):
    """Handle /levelmodify command to set user level."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/levelmodify [@username|user_id] [уровень]</code>\n"
            "🔍 Пример: <code>/levelmodify @user 25</code>"
        )
        return
    
    # Parse target user
    target_arg = args[0]
    target_user_id = None
    
    if target_arg.startswith('@'):
        target_user_id = await get_user_id_by_username(target_arg[1:])
    elif target_arg.isdigit():
        target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Parse level
    try:
        target_level = int(args[1])
        if target_level < 1 or target_level > 100:
            await message.reply("❌ Уровень должен быть от 1 до 100.")
            return
    except ValueError:
        await message.reply("❌ Неверный уровень.")
        return
    
    # Get user data before modification
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    old_level = user_data.get('level', 1)
    old_exp = user_data.get('experience', 0)
    
    # Set new level
    success = await set_user_level(target_user_id, target_level)
    
    if not success:
        await message.reply("❌ Ошибка при изменении уровня.")
        return
    
    # Get updated data
    updated_user_data = await Database.get_user(target_user_id)
    new_exp = updated_user_data.get('experience', 0)
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    success_text = f"""
✅ <b>Уровень изменен</b>

👤 <b>Пользователь:</b> {target_display}
🏆 <b>Уровень:</b> {old_level} → {target_level}
⭐ <b>Опыт:</b> {old_exp} → {new_exp} XP
👮 <b>Администратор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("multiplier"))
@admin_required
async def multiplier_command(message: Message, **kwargs):
    """Handle /multiplier command to set XP multiplier."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            f"❌ Неверный формат команды.\n\n"
            f"📝 Использование: <code>/multiplier [@username|user_id] [множитель]</code>\n"
            f"🔍 Пример: <code>/multiplier @user 1.5</code>\n"
            f"📊 Диапазон: {MIN_XP_MULTIPLIER} - {MAX_XP_MULTIPLIER}"
        )
        return
    
    # Parse target user
    target_arg = args[0]
    target_user_id = None
    
    if target_arg.startswith('@'):
        target_user_id = await get_user_id_by_username(target_arg[1:])
    elif target_arg.isdigit():
        target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Parse multiplier
    try:
        multiplier = float(args[1])
        if not (MIN_XP_MULTIPLIER <= multiplier <= MAX_XP_MULTIPLIER):
            await message.reply(f"❌ Множитель должен быть от {MIN_XP_MULTIPLIER} до {MAX_XP_MULTIPLIER}.")
            return
    except ValueError:
        await message.reply("❌ Неверный множитель.")
        return
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    old_multiplier = user_data.get('xp_multiplier', 1.0)
    
    # Set new multiplier
    success = await set_xp_multiplier(target_user_id, multiplier)
    
    if not success:
        await message.reply("❌ Ошибка при изменении множителя.")
        return
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    success_text = f"""
✅ <b>Множитель опыта изменен</b>

👤 <b>Пользователь:</b> {target_display}
⚡ <b>Множитель:</b> {old_multiplier}x → {multiplier}x
👮 <b>Администратор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("give_rights"))
@admin_required
async def give_rights_command(message: Message, **kwargs):
    """Handle /give_rights command to grant user rights."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/give_rights [@username|user_id] [права]</code>\n"
            "🔍 Пример: <code>/give_rights @user moderator</code>\n\n"
            "📋 <b>Доступные права:</b>\n"
            "• <code>admin</code> - администратор\n"
            "• <code>moderator</code> - модератор\n"
            "• <code>art_leader</code> - арт-лидер"
        )
        return
    
    # Parse target user
    target_arg = args[0]
    target_user_id = None
    
    if target_arg.startswith('@'):
        target_user_id = await get_user_id_by_username(target_arg[1:])
    elif target_arg.isdigit():
        target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Parse rights
    rights = args[1].lower()
    valid_rights = ['admin', 'moderator', 'art_leader']
    
    if rights not in valid_rights:
        await message.reply(f"❌ Неверные права. Доступные: {', '.join(valid_rights)}")
        return
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Update rights in database
    import aiosqlite
    from config import DATABASE_PATH
    
    field_name = f"is_{rights}"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"""
            UPDATE users SET {field_name} = TRUE
            WHERE user_id = ?
        """, (target_user_id,))
        await db.commit()
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    rights_display = {
        'admin': '🔧 Администратор',
        'moderator': '⚖️ Модератор',
        'art_leader': '🎨 Арт-лидер'
    }
    
    success_text = f"""
✅ <b>Права выданы</b>

👤 <b>Пользователь:</b> {target_display}
🎭 <b>Права:</b> {rights_display[rights]}
👮 <b>Администратор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("remove_rights"))
@admin_required
async def remove_rights_command(message: Message, **kwargs):
    """Handle /remove_rights command to remove user rights."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/remove_rights [@username|user_id] [права]</code>\n"
            "🔍 Пример: <code>/remove_rights @user moderator</code>\n\n"
            "📋 <b>Доступные права:</b>\n"
            "• <code>admin</code> - администратор\n"
            "• <code>moderator</code> - модератор\n"
            "• <code>art_leader</code> - арт-лидер"
        )
        return
    
    # Parse target user
    target_arg = args[0]
    target_user_id = None
    
    if target_arg.startswith('@'):
        target_user_id = await get_user_id_by_username(target_arg[1:])
    elif target_arg.isdigit():
        target_user_id = int(target_arg)
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Parse rights
    rights = args[1].lower()
    valid_rights = ['admin', 'moderator', 'art_leader']
    
    if rights not in valid_rights:
        await message.reply(f"❌ Неверные права. Доступные: {', '.join(valid_rights)}")
        return
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Update rights in database
    import aiosqlite
    from config import DATABASE_PATH
    
    field_name = f"is_{rights}"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"""
            UPDATE users SET {field_name} = FALSE
            WHERE user_id = ?
        """, (target_user_id,))
        await db.commit()
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    rights_display = {
        'admin': '🔧 Администратор',
        'moderator': '⚖️ Модератор',
        'art_leader': '🎨 Арт-лидер'
    }
    
    success_text = f"""
✅ <b>Права убраны</b>

👤 <b>Пользователь:</b> {target_display}
🎭 <b>Права:</b> {rights_display[rights]}
👮 <b>Администратор:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

# Utility function
async def get_user_id_by_username(username: str) -> int:
    """Get user ID by username."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None