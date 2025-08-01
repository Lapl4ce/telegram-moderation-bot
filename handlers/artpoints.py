"""
Art points management handlers for the Telegram moderation bot.
Handles art points assignment and management.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from middleware.auth import art_leader_required, admin_required
from database.database import Database

router = Router()

@router.message(Command("modify_artpoints"))
@art_leader_required
async def modify_artpoints_command(message: Message, **kwargs):
    """Handle /modify_artpoints command to modify user art points."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/modify_artpoints [@username|user_id] [количество]</code>\n"
            "🔍 Пример: <code>/modify_artpoints @user +10</code> или <code>/modify_artpoints 123456 -5</code>"
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
    
    # Parse art points change
    try:
        points_change = int(args[1])
    except ValueError:
        await message.reply("❌ Неверное количество арт-очков.")
        return
    
    # Get user data before modification
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    old_points = user_data.get('art_points', 0)
    new_points = max(0, old_points + points_change)  # Don't allow negative points
    
    # Update art points in database
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET art_points = ?
            WHERE user_id = ?
        """, (new_points, target_user_id))
        await db.commit()
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    change_text = f"+{points_change}" if points_change > 0 else str(points_change)
    actual_change = new_points - old_points
    
    success_text = f"""
✅ <b>Арт-очки изменены</b>

👤 <b>Пользователь:</b> {target_display}
🎨 <b>Изменение:</b> {change_text} арт-очков
📊 <b>Арт-очки:</b> {old_points} → {new_points}
👮 <b>Арт-лидер:</b> {message.from_user.mention_html()}
    """
    
    if actual_change != points_change:
        success_text += f"\n💡 <i>Фактическое изменение: {actual_change:+d} (минимум 0 очков)</i>"
    
    await message.reply(success_text)

@router.message(Command("art_top"))
async def art_top_command(message: Message, **kwargs):
    """Handle /art_top command to show top users by art points."""
    top_artists = await get_top_artists(10)
    
    if not top_artists:
        await message.reply("❌ Нет данных для отображения топа по арт-очкам.")
        return
    
    # Build leaderboard text
    leaderboard_text = "🎨 <b>Топ по арт-очкам</b>\n\n"
    
    for i, user in enumerate(top_artists, 1):
        username = user['username']
        username_display = f"@{username}" if username else user['first_name'] or "Неизвестный"
        
        # Add medal for top 3
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        leaderboard_text += f"{medal}<b>{i}.</b> {username_display}\n"
        leaderboard_text += f"    🎨 {user['art_points']} арт-очков\n\n"
    
    await message.reply(leaderboard_text)

@router.message(Command("artpoints"))
async def artpoints_command(message: Message, **kwargs):
    """Handle /artpoints command to show user's art points."""
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
        # Show own art points
        target_user_id = message.from_user.id
    
    if not target_user_id:
        await message.reply("❌ Пользователь не найден.")
        return
    
    # Get user data
    user_data = await Database.get_user(target_user_id)
    if not user_data:
        await message.reply("❌ Пользователь не найден в базе данных.")
        return
    
    # Get user's rank in art points
    rank = await get_user_art_rank(target_user_id)
    
    # Format response
    target_username = user_data.get('username')
    target_display = f"@{target_username}" if target_username else user_data.get('first_name', 'Неизвестный')
    
    art_points = user_data.get('art_points', 0)
    
    points_text = f"""
🎨 <b>Арт-очки пользователя</b>

👤 <b>Пользователь:</b> {target_display}
🎨 <b>Арт-очки:</b> {art_points}
🏆 <b>Позиция в рейтинге:</b> {rank}

💡 <i>Арт-очки начисляются за творческие работы</i>
    """
    
    await message.reply(points_text)

@router.message(Command("give_artpoints"))
@art_leader_required
async def give_artpoints_command(message: Message, **kwargs):
    """Handle /give_artpoints command (alias for modify_artpoints with positive values)."""
    args = message.text.split()[1:] if message.text else []
    
    if len(args) < 2:
        await message.reply(
            "❌ Неверный формат команды.\n\n"
            "📝 Использование: <code>/give_artpoints [@username|user_id] [количество]</code>\n"
            "🔍 Пример: <code>/give_artpoints @user 10</code>"
        )
        return
    
    # Parse points amount
    try:
        points = int(args[1])
        if points <= 0:
            await message.reply("❌ Количество арт-очков должно быть положительным.")
            return
    except ValueError:
        await message.reply("❌ Неверное количество арт-очков.")
        return
    
    # Reuse modify_artpoints logic
    modified_args = [args[0], f"+{points}"]
    message.text = f"/modify_artpoints {' '.join(modified_args)}"
    await modify_artpoints_command(message, **kwargs)

# Utility functions

async def get_user_id_by_username(username: str) -> int:
    """Get user ID by username."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE username = ? COLLATE NOCASE", (username,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def get_top_artists(limit: int = 10) -> list:
    """Get top users by art points."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, username, first_name, art_points
            FROM users
            WHERE art_points > 0
            ORDER BY art_points DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_art_rank(user_id: int) -> int:
    """Get user's rank by art points."""
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) + 1
            FROM users
            WHERE art_points > (
                SELECT COALESCE(art_points, 0)
                FROM users
                WHERE user_id = ?
            )
        """, (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 1