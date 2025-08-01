"""
Authentication middleware for the Telegram moderation bot.
Handles user permissions and access control.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.database import Database
from config import ADMIN_IDS, MODERATOR_IDS, ART_LEADER_IDS

class AuthMiddleware(BaseMiddleware):
    """Middleware for handling user authentication and permissions."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Process the event and add user permission data."""
        
        # Get user from event
        user = event.from_user
        if not user:
            return await handler(event, data)
        
        # Ensure user exists in database
        await Database.create_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Get user data from database
        user_data = await Database.get_user(user.id)
        
        # Determine user permissions
        is_admin = user.id in ADMIN_IDS or (user_data and user_data.get('is_admin', False))
        is_moderator = user.id in MODERATOR_IDS or (user_data and user_data.get('is_moderator', False))
        is_art_leader = user.id in ART_LEADER_IDS or (user_data and user_data.get('is_art_leader', False))
        
        # Add permission data to handler data
        data['user_data'] = user_data
        data['is_admin'] = is_admin
        data['is_moderator'] = is_moderator or is_admin  # Admins have moderator rights
        data['is_art_leader'] = is_art_leader or is_admin  # Admins have art leader rights
        data['can_moderate'] = is_moderator or is_admin
        
        return await handler(event, data)

def admin_required(handler):
    """Decorator to require admin permissions for a handler."""
    async def wrapper(event, **kwargs):
        if not kwargs.get('is_admin', False):
            if isinstance(event, Message):
                await event.reply("❌ У вас нет прав администратора для выполнения этой команды.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У вас нет прав администратора для выполнения этого действия.", show_alert=True)
            return
        return await handler(event, **kwargs)
    return wrapper

def moderator_required(handler):
    """Decorator to require moderator permissions for a handler."""
    async def wrapper(event, **kwargs):
        if not kwargs.get('is_moderator', False):
            if isinstance(event, Message):
                await event.reply("❌ У вас нет прав модератора для выполнения этой команды.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У вас нет прав модератора для выполнения этого действия.", show_alert=True)
            return
        return await handler(event, **kwargs)
    return wrapper

def art_leader_required(handler):
    """Decorator to require art leader permissions for a handler."""
    async def wrapper(event, **kwargs):
        if not kwargs.get('is_art_leader', False):
            if isinstance(event, Message):
                await event.reply("❌ У вас нет прав арт-лидера для выполнения этой команды.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ У вас нет прав арт-лидера для выполнения этого действия.", show_alert=True)
            return
        return await handler(event, **kwargs)
    return wrapper