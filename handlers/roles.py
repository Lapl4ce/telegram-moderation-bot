"""
Role management handlers for the Telegram moderation bot.
Handles custom role assignment and management.
"""
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from middleware.auth import admin_required
from database.database import Database

router = Router()

@router.message(Command("assign_role"))
@admin_required
async def assign_role_command(message: Message, **kwargs):
    """Handle /assign_role command to assign a custom role to a user."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/assign_role [@username|user_id] [роль]</code>\n"
            "🔍 Пример: <code>/assign_role @user VIP-участник</code>"
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
    
    # Parse role name
    role_name = " ".join(args[1:]).strip()
    
    if len(role_name) < 2 or len(role_name) > 50:
        await message.reply("❌ Название роли должно быть от 2 до 50 символов.")
        return
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Check if user already has this role
    existing_role = await get_user_custom_role(target_user_id, role_name)
    if existing_role:
        await message.reply(f"❌ Пользователь уже имеет роль '<code>{role_name}</code>'.")
        return
    
    # Add role to database
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO custom_roles (user_id, role_name, assigned_by)
            VALUES (?, ?, ?)
        """, (target_user_id, role_name, message.from_user.id))
        await db.commit()
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    success_text = f"""
✅ <b>Роль назначена</b>

👤 <b>Пользователь:</b> {target_display}
🎭 <b>Роль:</b> {role_name}
👮 <b>Назначил:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("unassign_role"))
@admin_required
async def unassign_role_command(message: Message, **kwargs):
    """Handle /unassign_role command to remove a custom role from a user."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/unassign_role [@username|user_id] [роль]</code>\n"
            "🔍 Пример: <code>/unassign_role @user VIP-участник</code>"
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
    
    # Parse role name
    role_name = " ".join(args[1:]).strip()
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Remove role from database
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            DELETE FROM custom_roles
            WHERE user_id = ? AND role_name = ?
        """, (target_user_id, role_name))
        await db.commit()
        
        if cursor.rowcount == 0:
            await message.reply(f"❌ Пользователь не имеет роль '<code>{role_name}</code>'.")
            return
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    success_text = f"""
✅ <b>Роль снята</b>

👤 <b>Пользователь:</b> {target_display}
🎭 <b>Роль:</b> {role_name}
👮 <b>Снял:</b> {message.from_user.mention_html()}
    """
    
    await message.reply(success_text)

@router.message(Command("user_roles"))
async def user_roles_command(message: Message, **kwargs):
    """Handle /user_roles command to show user's custom roles."""
    args = message.text.split()[1:] if message.text else []
    target_user_id = None
    
    # Determine target user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif args:
        target_arg = args[0]
        if target_arg.startswith('@'):
            target_user_id = await get_user_id_by_username(target_arg[1:])
        elif target_arg.isdigit():
            target_user_id = int(target_arg)
    else:
        # Show own roles
        target_user_id = message.from_user.id
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Get user's custom roles
    roles = await get_user_custom_roles(target_user_id)
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    if not roles:
        roles_text = f"""
🎭 <b>Роли пользователя</b>

👤 <b>Пользователь:</b> {target_display}
📝 <b>Кастомные роли:</b> Нет
        """
    else:
        roles_list = []
        for role in roles:
            import datetime
            assign_date = datetime.datetime.fromtimestamp(role['assign_date']).strftime("%d.%m.%Y")
            roles_list.append(f"• <b>{role['role_name']}</b> (с {assign_date})")
        
        roles_text = f"""
🎭 <b>Роли пользователя</b>

👤 <b>Пользователь:</b> {target_display}

📝 <b>Кастомные роли:</b>
{chr(10).join(roles_list)}
        """
    
    await message.reply(roles_text)

# Utility functions

async def get_user_id_by_username(username: str) -> int:
    """Get user ID by username."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def get_user_custom_role(user_id: int, role_name: str) -> dict:
    """Get specific custom role for a user."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM custom_roles
            WHERE user_id = ? AND role_name = ?
        """, (user_id, role_name)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_user_custom_roles(user_id: int) -> list:
    """Get all custom roles for a user."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM custom_roles
            WHERE user_id = ?
            ORDER BY assign_date DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]