"""
Experience system handler for the Telegram moderation bot.
Manages user experience points, levels, and related features.
"""
import time
import random
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from database.database import Database
from config import (
    XP_PER_MESSAGE_MIN, XP_PER_MESSAGE_MAX, XP_COOLDOWN,
    calculate_required_exp, calculate_level_from_exp,
    get_user_title, STICKER_UNLOCK_LEVEL
)

class ExperienceHandler(BaseMiddleware):
    """Middleware for handling experience point awards."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Process message and award XP if conditions are met."""
        
        # Only process regular messages (not commands)
        if not isinstance(event, Message) or not event.text or event.text.startswith('/'):
            return await handler(event, data)
        
        user = event.from_user
        if not user or user.is_bot:
            return await handler(event, data)
        
        # Get user data
        user_data = await Database.get_user(user.id)
        if not user_data:
            return await handler(event, data)
        
        # Check cooldown
        current_time = int(time.time())
        last_xp_time = user_data.get('last_xp_time', 0)
        
        if current_time - last_xp_time >= XP_COOLDOWN:
            # Award XP
            await self.award_experience(user.id, user_data)
            
            # Update message statistics
            await Database.update_message_stats(user.id)
        
        return await handler(event, data)
    
    async def award_experience(self, user_id: int, user_data: Dict[str, Any]) -> None:
        """Award experience points to a user."""
        # Calculate XP to award
        base_xp = random.randint(XP_PER_MESSAGE_MIN, XP_PER_MESSAGE_MAX)
        multiplier = user_data.get('xp_multiplier', 1.0)
        xp_to_award = int(base_xp * multiplier)
        
        # Update experience
        current_exp = user_data.get('experience', 0)
        current_level = user_data.get('level', 1)
        new_exp = current_exp + xp_to_award
        new_level = calculate_level_from_exp(new_exp)
        
        # Update database
        await Database.update_user_experience(user_id, new_exp, new_level)
        
        # Check for level up
        if new_level > current_level:
            await self.handle_level_up(user_id, new_level, current_level)
    
    async def handle_level_up(self, user_id: int, new_level: int, old_level: int) -> None:
        """Handle level up events and notifications."""
        # This could be extended to send level up notifications
        # For now, we'll just log it
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {user_id} leveled up from {old_level} to {new_level}")
        
        # Check if user unlocked stickers at level 25
        if new_level >= STICKER_UNLOCK_LEVEL and old_level < STICKER_UNLOCK_LEVEL:
            # Update sticker permission in database
            import aiosqlite
            from config import DATABASE_PATH
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute("""
                    UPDATE users SET can_use_stickers = TRUE
                    WHERE user_id = ?
                """, (user_id,))
                await db.commit()

# Utility functions for experience system
async def get_user_profile(user_id: int) -> Dict[str, Any]:
    """Get comprehensive user profile information."""
    user_data = await Database.get_user(user_id)
    if not user_data:
        return {}
    
    level = user_data['level']
    experience = user_data['experience']
    
    # Calculate experience for current and next level
    current_level_exp = calculate_required_exp(level - 1) if level > 1 else 0
    next_level_exp = calculate_required_exp(level)
    exp_in_level = experience - current_level_exp
    exp_needed = next_level_exp - experience
    
    # Get warnings count
    warnings = await Database.get_active_warnings(user_id)
    
    profile = {
        'user_id': user_id,
        'username': user_data.get('username'),
        'first_name': user_data.get('first_name'),
        'level': level,
        'title': get_user_title(level),
        'experience': experience,
        'exp_in_level': exp_in_level,
        'exp_needed': exp_needed,
        'next_level_exp': next_level_exp - current_level_exp,
        'warnings_count': len(warnings),
        'art_points': user_data.get('art_points', 0),
        'can_use_stickers': user_data.get('can_use_stickers', False),
        'xp_multiplier': user_data.get('xp_multiplier', 1.0),
        'join_date': user_data.get('join_date'),
        'is_admin': user_data.get('is_admin', False),
        'is_moderator': user_data.get('is_moderator', False),
        'is_art_leader': user_data.get('is_art_leader', False),
    }
    
    return profile

async def modify_user_experience(user_id: int, experience_change: int) -> bool:
    """Modify user experience by a specific amount."""
    user_data = await Database.get_user(user_id)
    if not user_data:
        return False
    
    current_exp = user_data.get('experience', 0)
    new_exp = max(0, current_exp + experience_change)  # Don't allow negative XP
    new_level = calculate_level_from_exp(new_exp)
    
    await Database.update_user_experience(user_id, new_exp, new_level)
    return True

async def set_user_level(user_id: int, target_level: int) -> bool:
    """Set user to a specific level."""
    if target_level < 1:
        return False
    
    required_exp = calculate_required_exp(target_level - 1) if target_level > 1 else 0
    await Database.update_user_experience(user_id, required_exp, target_level)
    return True

async def set_xp_multiplier(user_id: int, multiplier: float) -> bool:
    """Set XP multiplier for a user."""
    from config import MIN_XP_MULTIPLIER, MAX_XP_MULTIPLIER, DATABASE_PATH
    import aiosqlite
    
    if not (MIN_XP_MULTIPLIER <= multiplier <= MAX_XP_MULTIPLIER):
        return False
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET xp_multiplier = ?
            WHERE user_id = ?
        """, (multiplier, user_id))
        await db.commit()
    
    return True