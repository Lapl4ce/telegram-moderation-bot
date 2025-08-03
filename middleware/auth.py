"""Authentication middleware for the bot."""

from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import UserRoles
from database.database import AsyncSessionLocal
from database.models import User


class AuthMiddleware(BaseMiddleware):
    """Middleware for user authentication and registration."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            if user and not user.is_bot:
                # Get or create user in database
                user_data = await self._get_or_create_user(user)
                data["user"] = user_data
                data["user_role"] = user_data.role if user_data else UserRoles.MEMBER
        
        return await handler(event, data)
    
    async def _get_or_create_user(self, telegram_user) -> User:
        """Get existing user or create new one."""
        async with AsyncSessionLocal() as session:
            try:
                # Try to get existing user
                result = await session.execute(
                    select(User).where(User.user_id == telegram_user.id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    # Update user info if needed
                    needs_update = False
                    if user.username != telegram_user.username:
                        user.username = telegram_user.username
                        needs_update = True
                    if user.first_name != telegram_user.first_name:
                        user.first_name = telegram_user.first_name
                        needs_update = True
                    if user.last_name != telegram_user.last_name:
                        user.last_name = telegram_user.last_name
                        needs_update = True
                    
                    if needs_update:
                        user.updated_at = datetime.utcnow()
                        await session.commit()
                    
                    return user
                else:
                    # Create new user
                    new_user = User(
                        user_id=telegram_user.id,
                        username=telegram_user.username,
                        first_name=telegram_user.first_name,
                        last_name=telegram_user.last_name,
                        role=UserRoles.MEMBER
                    )
                    session.add(new_user)
                    await session.commit()
                    await session.refresh(new_user)
                    return new_user
            
            except Exception as e:
                await session.rollback()
                print(f"Error in auth middleware: {e}")
                # Return a default user object in case of error
                return User(
                    user_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    role=UserRoles.MEMBER
                )