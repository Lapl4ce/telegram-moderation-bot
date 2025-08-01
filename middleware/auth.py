from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import logging

from database.models import UserRight
from database.database import Database

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    """Middleware for user authentication and rights management"""
    
    def __init__(self, database: Database):
        self.db = database
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process authentication for incoming updates"""
        
        user_id = None
        
        # Extract user info from different event types
        if isinstance(event, Message):
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username
                first_name = event.from_user.first_name
                last_name = event.from_user.last_name
        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username
                first_name = event.from_user.first_name
                last_name = event.from_user.last_name
        
        if user_id:
            try:
                # Get or create user
                user = await self.db.get_or_create_user(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Add user to data for handlers
                data['user'] = user
                data['db'] = self.db
                
            except Exception as e:
                logger.error(f"Error in auth middleware: {e}")
        
        return await handler(event, data)

def require_rights(*required_rights: UserRight):
    """Decorator to require specific user rights"""
    def decorator(handler):
        async def wrapper(message: Message, user=None, **kwargs):
            if not user:
                await message.reply("❌ Authentication failed")
                return
            
            if user.rights not in required_rights:
                await message.reply("❌ Insufficient permissions")
                return
            
            return await handler(message, user=user, **kwargs)
        return wrapper
    return decorator

def require_admin(handler):
    """Decorator to require admin rights"""
    return require_rights(UserRight.ADMIN)(handler)

def require_moderator(handler):
    """Decorator to require moderator or higher rights"""
    return require_rights(UserRight.MODERATOR, UserRight.ADMIN)(handler)

def require_art_leader(handler):
    """Decorator to require art leader rights"""
    return require_rights(UserRight.ART_LEADER, UserRight.ADMIN)(handler)