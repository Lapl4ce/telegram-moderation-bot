from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.models import User
from database.database import Database
from middleware.auth import require_admin
from utils.validators import extract_user_id, validate_role_name, format_user_display_name

logger = logging.getLogger(__name__)
router = Router()

async def get_target_user_role(message: Message, db: Database, args: list) -> User:
    """Get target user for role commands"""
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

@router.message(Command("assign_role"))
@require_admin
async def cmd_assign_role(message: Message, user: User, db: Database):
    """Handle /assign_role command - assign custom role to user"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
🏅 **Назначение кастомной роли**

Используйте: `/assign_role пользователь роль`

Пример:
`/assign_role @username VIP Member`
`/assign_role 123456789 Trusted User`

Роль должна содержать 3-50 символов.
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_role(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Get role name
    role_start_idx = 1 if args and extract_user_id(args[0]) else 0
    role_name = " ".join(args[role_start_idx:])
    
    if not validate_role_name(role_name):
        await message.reply("❌ Неверное название роли. Роль должна содержать 3-50 символов, только буквы, цифры и пробелы")
        return
    
    # Set custom role
    old_role = target_user.custom_role
    target_user.custom_role = role_name.strip()
    
    # Update in database
    await db.update_user(target_user)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    if old_role:
        result_text = f"""
🏅 **Кастомная роль изменена**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

📊 **Изменения:**
• Роль: "{old_role}" → "{role_name}"
"""
    else:
        result_text = f"""
🏅 **Кастомная роль назначена**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

🆕 **Новая роль:** "{role_name}"
"""
    
    await message.reply(result_text, parse_mode="Markdown")

@router.message(Command("unassign_role"))
@require_admin
async def cmd_unassign_role(message: Message, user: User, db: Database):
    """Handle /unassign_role command - remove custom role from user"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user_role(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для снятия роли")
        return
    
    if not target_user.custom_role:
        await message.reply("❌ У пользователя нет кастомной роли")
        return
    
    # Remove custom role
    old_role = target_user.custom_role
    target_user.custom_role = None
    
    # Update in database
    await db.update_user(target_user)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    result_text = f"""
🏅 **Кастомная роль снята**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

❌ **Убрана роль:** "{old_role}"
"""
    
    await message.reply(result_text, parse_mode="Markdown")

@router.message(Command("set_title"))
@require_admin
async def cmd_set_title(message: Message, user: User, db: Database):
    """Handle /set_title command - set custom title for user"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
👑 **Установка титула**

Используйте: `/set_title пользователь титул`

Пример:
`/set_title @username Легенда чата`
`/set_title 123456789 Старожил`

Титул должен содержать 3-50 символов.
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_role(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Get title
    title_start_idx = 1 if args and extract_user_id(args[0]) else 0
    title = " ".join(args[title_start_idx:])
    
    if not validate_role_name(title):  # Same validation as role name
        await message.reply("❌ Неверный титул. Титул должен содержать 3-50 символов, только буквы, цифры и пробелы")
        return
    
    # Set custom title
    old_title = target_user.custom_title
    target_user.custom_title = title.strip()
    
    # Update in database
    await db.update_user(target_user)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    if old_title:
        result_text = f"""
👑 **Титул изменён**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

📊 **Изменения:**
• Титул: "{old_title}" → "{title}"
"""
    else:
        result_text = f"""
👑 **Титул установлен**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

🆕 **Новый титул:** "{title}"
"""
    
    await message.reply(result_text, parse_mode="Markdown")

@router.message(Command("remove_title"))
@require_admin
async def cmd_remove_title(message: Message, user: User, db: Database):
    """Handle /remove_title command - remove custom title from user"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user_role(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для снятия титула")
        return
    
    if not target_user.custom_title:
        await message.reply("❌ У пользователя нет титула")
        return
    
    # Remove custom title
    old_title = target_user.custom_title
    target_user.custom_title = None
    
    # Update in database
    await db.update_user(target_user)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    result_text = f"""
👑 **Титул снят**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

❌ **Убран титул:** "{old_title}"
"""
    
    await message.reply(result_text, parse_mode="Markdown")