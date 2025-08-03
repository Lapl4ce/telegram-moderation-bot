"""Experience system utilities and middleware."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import XP_PER_MESSAGE_MIN, XP_PER_MESSAGE_MAX, XP_COOLDOWN
from database.database import AsyncSessionLocal
from database.models import User, ExperienceMultiplier


def calculate_level_from_experience(experience: int) -> int:
    """Calculate level from experience using the formula: exp = 3 * level² + 50 * level + 100."""
    level = 0
    while calculate_experience_for_level(level + 1) <= experience:
        level += 1
    return level


def calculate_experience_for_level(level: int) -> int:
    """Calculate required experience for a specific level."""
    return 3 * (level ** 2) + 50 * level + 100


def calculate_experience_for_next_level(current_level: int) -> int:
    """Calculate experience needed for next level."""
    return calculate_experience_for_level(current_level + 1)


def calculate_experience_progress(experience: int, level: int) -> tuple[int, int, int]:
    """Calculate experience progress for current level.
    
    Returns:
        tuple: (current_level_exp, next_level_exp, progress_in_level)
    """
    current_level_exp = calculate_experience_for_level(level)
    next_level_exp = calculate_experience_for_level(level + 1)
    progress_in_level = experience - current_level_exp
    
    return current_level_exp, next_level_exp, progress_in_level


async def get_user_multiplier(session: AsyncSession, user_id: int) -> float:
    """Get current experience multiplier for user."""
    result = await session.execute(
        select(ExperienceMultiplier).where(
            ExperienceMultiplier.user_id == user_id,
            ExperienceMultiplier.expires_at > datetime.utcnow()
        )
    )
    multiplier_obj = result.scalar_one_or_none()
    return multiplier_obj.multiplier if multiplier_obj else 1.0


async def add_experience(session: AsyncSession, user_id: int, amount: int) -> tuple[int, bool]:
    """Add experience to user and return new level and if level changed."""
    # Get current user data
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return 0, False
    
    # Get multiplier
    multiplier = await get_user_multiplier(session, user_id)
    final_amount = int(amount * multiplier)
    
    # Calculate new experience and level
    new_experience = user.experience + final_amount
    old_level = user.level
    new_level = calculate_level_from_experience(new_experience)
    
    # Update user
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(experience=new_experience, level=new_level)
    )
    
    await session.commit()
    
    return new_level, new_level > old_level


class ExperienceHandler(BaseMiddleware):
    """Middleware for handling experience gain from messages."""
    
    def __init__(self):
        self.user_cooldowns: Dict[int, datetime] = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user and not event.from_user.is_bot:
            await self._handle_experience(event)
        
        return await handler(event, data)
    
    async def _handle_experience(self, message: Message) -> None:
        """Handle experience gain from message."""
        user_id = message.from_user.id
        now = datetime.utcnow()
        
        # Check cooldown
        if user_id in self.user_cooldowns:
            if now < self.user_cooldowns[user_id]:
                return
        
        # Set new cooldown
        self.user_cooldowns[user_id] = now + timedelta(seconds=XP_COOLDOWN)
        
        # Clean old cooldowns
        await self._clean_cooldowns(now)
        
        # Add random experience
        xp_amount = random.randint(XP_PER_MESSAGE_MIN, XP_PER_MESSAGE_MAX)
        
        async with AsyncSessionLocal() as session:
            try:
                new_level, level_up = await add_experience(session, user_id, xp_amount)
                
                # Send level up message
                if level_up:
                    await message.reply(
                        f"🎉 Поздравляем! Вы достигли {new_level} уровня!\n"
                        f"✨ Получен опыт: +{xp_amount} XP"
                    )
            except Exception as e:
                print(f"Error adding experience: {e}")
    
    async def _clean_cooldowns(self, current_time: datetime) -> None:
        """Clean expired cooldowns."""
        expired_users = [
            user_id for user_id, expire_time in self.user_cooldowns.items()
            if current_time >= expire_time
        ]
        
        for user_id in expired_users:
            del self.user_cooldowns[user_id]