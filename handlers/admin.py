from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

from database.models import User, UserRight
from database.database import Database
from middleware.auth import require_admin
from utils.validators import extract_user_id, sanitize_text, format_user_display_name
from utils.experience import calculate_level_from_exp

logger = logging.getLogger(__name__)
router = Router()

async def get_target_user_admin(message: Message, db: Database, args: list) -> User:
    """Get target user for admin commands"""
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

@router.message(Command("xpmodify"))
@require_admin
async def cmd_xp_modify(message: Message, user: User, db: Database):
    """Handle /xpmodify command - modify user experience"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
⚡ **Изменение опыта**

Используйте: `/xpmodify пользователь количество`

Пример:
`/xpmodify @username +500` - добавить 500 XP
`/xpmodify 123456789 -200` - убрать 200 XP
`/xpmodify @username =1000` - установить 1000 XP
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_admin(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Parse XP amount
    xp_str = args[1] if len(args) > 1 else args[0]
    
    try:
        old_experience = target_user.experience
        old_level = target_user.level
        
        if xp_str.startswith('+'):
            # Add XP
            amount = int(xp_str[1:])
            target_user.experience += amount
        elif xp_str.startswith('-'):
            # Subtract XP
            amount = int(xp_str[1:])
            target_user.experience = max(0, target_user.experience - amount)
        elif xp_str.startswith('='):
            # Set XP
            amount = int(xp_str[1:])
            target_user.experience = max(0, amount)
        else:
            # Default to setting XP
            amount = int(xp_str)
            target_user.experience = max(0, amount)
        
        # Recalculate level
        target_user.level = calculate_level_from_exp(target_user.experience)
        
        # Update in database
        await db.update_user(target_user)
        
        target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
        admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
        
        result_text = f"""
⚡ **Опыт изменён**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

📊 **Изменения:**
• Опыт: {old_experience:,} → {target_user.experience:,}
• Уровень: {old_level} → {target_user.level}
"""
        
        await message.reply(result_text, parse_mode="Markdown")
        
    except ValueError:
        await message.reply("❌ Неверный формат количества опыта")
    except Exception as e:
        logger.error(f"Error modifying XP: {e}")
        await message.reply("❌ Ошибка при изменении опыта")

@router.message(Command("levelmodify"))
@require_admin
async def cmd_level_modify(message: Message, user: User, db: Database):
    """Handle /levelmodify command - modify user level"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
🏆 **Изменение уровня**

Используйте: `/levelmodify пользователь уровень`

Пример:
`/levelmodify @username 25` - установить 25 уровень
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_admin(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Parse level
    level_str = args[1] if len(args) > 1 else args[0]
    
    try:
        new_level = int(level_str)
        if new_level < 1:
            await message.reply("❌ Уровень должен быть больше 0")
            return
        
        old_level = target_user.level
        old_experience = target_user.experience
        
        # Calculate required experience for the new level
        from utils.experience import calculate_exp_for_level
        required_exp = calculate_exp_for_level(new_level)
        
        # Set new level and experience
        target_user.level = new_level
        target_user.experience = required_exp
        
        # Update in database
        await db.update_user(target_user)
        
        target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
        admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
        
        result_text = f"""
🏆 **Уровень изменён**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

📊 **Изменения:**
• Уровень: {old_level} → {target_user.level}
• Опыт: {old_experience:,} → {target_user.experience:,}
"""
        
        await message.reply(result_text, parse_mode="Markdown")
        
    except ValueError:
        await message.reply("❌ Неверный формат уровня")
    except Exception as e:
        logger.error(f"Error modifying level: {e}")
        await message.reply("❌ Ошибка при изменении уровня")

@router.message(Command("give_rights"))
@require_admin
async def cmd_give_rights(message: Message, user: User, db: Database):
    """Handle /give_rights command - give user rights"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
👑 **Выдача прав**

Используйте: `/give_rights пользователь права`

Доступные права:
• `moderator` - модератор
• `admin` - администратор  
• `art_leader` - арт-лидер

Пример:
`/give_rights @username moderator`
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_admin(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Parse rights
    rights_str = args[1] if len(args) > 1 else args[0]
    rights_str = rights_str.lower()
    
    rights_map = {
        "moderator": UserRight.MODERATOR,
        "admin": UserRight.ADMIN,
        "art_leader": UserRight.ART_LEADER,
        "user": UserRight.USER
    }
    
    if rights_str not in rights_map:
        await message.reply("❌ Неверный тип прав. Доступные: moderator, admin, art_leader")
        return
    
    old_rights = target_user.rights
    target_user.rights = rights_map[rights_str]
    
    # Update in database
    await db.update_user(target_user)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    rights_names = {
        UserRight.USER: "Пользователь",
        UserRight.MODERATOR: "Модератор",
        UserRight.ADMIN: "Администратор",
        UserRight.ART_LEADER: "Арт-лидер"
    }
    
    result_text = f"""
👑 **Права изменены**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

📊 **Изменения:**
• Права: {rights_names[old_rights]} → {rights_names[target_user.rights]}
"""
    
    await message.reply(result_text, parse_mode="Markdown")

@router.message(Command("remove_rights"))
@require_admin
async def cmd_remove_rights(message: Message, user: User, db: Database):
    """Handle /remove_rights command - remove user rights"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Get target user
    target_user = await get_target_user_admin(message, db, args)
    if not target_user:
        await message.reply("❌ Укажите пользователя для снятия прав")
        return
    
    old_rights = target_user.rights
    target_user.rights = UserRight.USER
    
    # Update in database
    await db.update_user(target_user)
    
    target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
    admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
    
    result_text = f"""
👑 **Права сняты**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

Права пользователя сброшены до обычного пользователя.
"""
    
    await message.reply(result_text, parse_mode="Markdown")

@router.message(Command("multiplier"))
@require_admin
async def cmd_multiplier(message: Message, user: User, db: Database):
    """Handle /multiplier command - set XP multiplier"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.reply("""
⚡ **Множитель опыта**

Используйте: `/multiplier пользователь множитель`

Пример:
`/multiplier @username 2.0` - двойной опыт
`/multiplier 123456789 0.5` - половинный опыт
`/multiplier @username 1.0` - обычный опыт
""", parse_mode="Markdown")
        return
    
    # Get target user
    target_user = await get_target_user_admin(message, db, args)
    if not target_user:
        await message.reply("❌ Пользователь не найден")
        return
    
    # Parse multiplier
    multiplier_str = args[1] if len(args) > 1 else args[0]
    
    try:
        multiplier = float(multiplier_str)
        if multiplier < 0:
            await message.reply("❌ Множитель не может быть отрицательным")
            return
        
        if multiplier > 10:
            await message.reply("❌ Множитель не может быть больше 10")
            return
        
        old_multiplier = target_user.xp_multiplier
        target_user.xp_multiplier = multiplier
        
        # Update in database
        await db.update_user(target_user)
        
        target_name = format_user_display_name(target_user.username, target_user.first_name, target_user.last_name, target_user.user_id)
        admin_name = format_user_display_name(user.username, user.first_name, user.last_name)
        
        result_text = f"""
⚡ **Множитель опыта изменён**

👤 **Пользователь:** {target_name}
👑 **Администратор:** {admin_name}

📊 **Изменения:**
• Множитель: {old_multiplier}x → {multiplier}x
"""
        
        await message.reply(result_text, parse_mode="Markdown")
        
    except ValueError:
        await message.reply("❌ Неверный формат множителя")
    except Exception as e:
        logger.error(f"Error setting multiplier: {e}")
        await message.reply("❌ Ошибка при установке множителя")