"""Art points management handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update

from database.database import get_db
from database.models import User
from utils.permissions import can_manage_art_points
from utils.user_parser import parse_username

router = Router()


async def get_target_user_art(message: Message, args: list):
    """Get target user for art commands."""
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.first_name or "Пользователь"
    
    if not args:
        return None
    
    username = parse_username(args[0])
    
    async for session in get_db():
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user:
            return user.user_id, user.first_name or user.username or "Пользователь"
    
    return None


@router.message(Command("give_art_points"))
async def give_art_points_command(message: Message, user_role: str):
    """Handle /give_art_points command to give art points to user."""
    if not can_manage_art_points(user_role):
        await message.reply("❌ У вас нет прав для управления арт-очками.")
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 <b>Выдача арт-очков</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/give_art_points @username количество</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/give_art_points @user 50</code>"
        )
        return
    
    target_info = await get_target_user_art(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    try:
        points_arg_index = 1 if not args[0].startswith('@') else 2
        points = int(args[points_arg_index] if len(args) > points_arg_index else args[1])
        if points <= 0:
            raise ValueError()
    except (ValueError, IndexError):
        await message.reply("❌ Неверное количество арт-очков.")
        return
    
    async for session in get_db():
        try:
            # Get current art points
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            old_points = user.art_points
            new_points = old_points + points
            
            # Update art points
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(art_points=new_points)
            )
            await session.commit()
            
            await message.reply(
                f"✅ <b>Арт-очки выданы пользователю {target_name}</b>\n"
                f"🎨 <b>Было:</b> {old_points} арт-очков\n"
                f"🎨 <b>Стало:</b> {new_points} арт-очков\n"
                f"➕ <b>Добавлено:</b> +{points} арт-очков"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при выдаче арт-очков: {e}")


@router.message(Command("remove_art_points"))
async def remove_art_points_command(message: Message, user_role: str):
    """Handle /remove_art_points command to remove art points from user."""
    if not can_manage_art_points(user_role):
        await message.reply("❌ У вас нет прав для управления арт-очками.")
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.reply(
            "📝 <b>Снятие арт-очков</b>\n\n"
            "Используйте команду в формате:\n"
            "<code>/remove_art_points @username количество</code>\n\n"
            "📋 <b>Пример:</b>\n"
            "<code>/remove_art_points @user 25</code>"
        )
        return
    
    target_info = await get_target_user_art(message, args)
    if not target_info:
        await message.reply("❌ Пользователь не найден.")
        return
    
    target_user_id, target_name = target_info
    
    try:
        points_arg_index = 1 if not args[0].startswith('@') else 2
        points = int(args[points_arg_index] if len(args) > points_arg_index else args[1])
        if points <= 0:
            raise ValueError()
    except (ValueError, IndexError):
        await message.reply("❌ Неверное количество арт-очков.")
        return
    
    async for session in get_db():
        try:
            # Get current art points
            result = await session.execute(
                select(User).where(User.user_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Пользователь не найден в базе данных.")
                return
            
            old_points = user.art_points
            new_points = max(0, old_points - points)
            
            # Update art points
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(art_points=new_points)
            )
            await session.commit()
            
            removed_points = old_points - new_points
            
            await message.reply(
                f"✅ <b>Арт-очки сняты с пользователя {target_name}</b>\n"
                f"🎨 <b>Было:</b> {old_points} арт-очков\n"
                f"🎨 <b>Стало:</b> {new_points} арт-очков\n"
                f"➖ <b>Снято:</b> -{removed_points} арт-очков"
            )
            
        except Exception as e:
            await session.rollback()
            await message.reply(f"❌ Ошибка при снятии арт-очков: {e}")


@router.message(Command("art_top"))
async def art_top_command(message: Message):
    """Handle /art_top command to show art points leaderboard."""
    async for session in get_db():
        try:
            # Get top users by art points
            result = await session.execute(
                select(User)
                .where(User.art_points > 0)
                .order_by(User.art_points.desc())
                .limit(10)
            )
            users = result.scalars().all()
            
            if not users:
                await message.reply("🎨 В рейтинге арт-очков пока нет пользователей.")
                return
            
            top_text = "🎨 <b>Топ по арт-очкам</b>\n\n"
            
            for i, user in enumerate(users, 1):
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
                
                top_text += f"{medal} <b>{display_name}</b> — {user.art_points} 🎨\n"
            
            await message.reply(top_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении топа арт-очков: {e}")


@router.message(Command("my_art_points"))
async def my_art_points_command(message: Message):
    """Handle /my_art_points command to show user's art points."""
    user_id = message.from_user.id
    
    async for session in get_db():
        try:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.reply("❌ Ваш профиль не найден в базе данных.")
                return
            
            art_points_text = (
                f"🎨 <b>Ваши арт-очки</b>\n\n"
                f"💎 <b>Количество:</b> {user.art_points} арт-очков\n"
            )
            
            # Get rank among art users if user has points
            if user.art_points > 0:
                result = await session.execute(
                    select(User)
                    .where(User.art_points > user.art_points)
                )
                higher_users = len(result.scalars().all())
                
                result = await session.execute(
                    select(User).where(User.art_points > 0)
                )
                total_art_users = len(result.scalars().all())
                
                rank = higher_users + 1
                art_points_text += f"🏆 <b>Ваше место:</b> {rank} из {total_art_users}"
            else:
                art_points_text += "ℹ️ У вас пока нет арт-очков."
            
            await message.reply(art_points_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении арт-очков: {e}")


@router.message(Command("art_stats"))
async def art_stats_command(message: Message, user_role: str):
    """Handle /art_stats command to show art points statistics."""
    if not can_manage_art_points(user_role):
        await message.reply("❌ У вас нет прав для просмотра статистики арт-очков.")
        return
    
    async for session in get_db():
        try:
            from sqlalchemy import func
            
            # Get total art points distributed
            result = await session.execute(
                select(func.sum(User.art_points))
            )
            total_points = result.scalar() or 0
            
            # Get users with art points
            result = await session.execute(
                select(func.count(User.user_id))
                .where(User.art_points > 0)
            )
            users_with_points = result.scalar()
            
            # Get average art points
            result = await session.execute(
                select(func.avg(User.art_points))
                .where(User.art_points > 0)
            )
            avg_points = result.scalar() or 0
            
            # Get top art user
            result = await session.execute(
                select(User)
                .where(User.art_points > 0)
                .order_by(User.art_points.desc())
                .limit(1)
            )
            top_user = result.scalar_one_or_none()
            
            stats_text = (
                f"📊 <b>Статистика арт-очков</b>\n\n"
                f"💎 <b>Всего выдано:</b> {total_points:,} арт-очков\n"
                f"👥 <b>Пользователей с очками:</b> {users_with_points}\n"
                f"📈 <b>Среднее количество:</b> {avg_points:.1f} очков\n"
            )
            
            if top_user:
                display_name = top_user.first_name or "Неизвестно"
                if top_user.username:
                    display_name = f"@{top_user.username}"
                
                stats_text += f"\n🏆 <b>Лидер:</b> {display_name} ({top_user.art_points} очков)"
            
            await message.reply(stats_text)
            
        except Exception as e:
            await message.reply(f"❌ Ошибка при получении статистики: {e}")