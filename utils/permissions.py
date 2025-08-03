"""Permission checking utilities."""

from typing import List

from aiogram.types import Message, CallbackQuery
from config import UserRoles


def is_admin(user_role: str) -> bool:
    """Check if user is admin."""
    return user_role == UserRoles.ADMIN


def is_moderator(user_role: str) -> bool:
    """Check if user is moderator or higher."""
    return user_role in [UserRoles.MODERATOR, UserRoles.ADMIN]


def is_art_leader(user_role: str) -> bool:
    """Check if user is art leader."""
    return user_role == UserRoles.ART_LEADER


def can_moderate(user_role: str) -> bool:
    """Check if user can perform moderation actions."""
    return user_role in [UserRoles.MODERATOR, UserRoles.ADMIN]


def can_modify_experience(user_role: str) -> bool:
    """Check if user can modify experience and levels."""
    return user_role == UserRoles.ADMIN


def can_manage_roles(user_role: str) -> bool:
    """Check if user can manage roles."""
    return user_role == UserRoles.ADMIN


def can_manage_art_points(user_role: str) -> bool:
    """Check if user can manage art points."""
    return user_role in [UserRoles.ART_LEADER, UserRoles.ADMIN]


def can_access_tickets(user_role: str) -> bool:
    """Check if user can access and respond to tickets."""
    return user_role in [UserRoles.MODERATOR, UserRoles.ADMIN]


def has_permission(user_role: str, required_permissions: List[str]) -> bool:
    """Check if user has any of the required permissions."""
    permission_map = {
        "admin": is_admin,
        "moderator": is_moderator,
        "art_leader": is_art_leader,
        "can_moderate": can_moderate,
        "can_modify_experience": can_modify_experience,
        "can_manage_roles": can_manage_roles,
        "can_manage_art_points": can_manage_art_points,
        "can_access_tickets": can_access_tickets,
    }
    
    for permission in required_permissions:
        if permission in permission_map and permission_map[permission](user_role):
            return True
    
    return False


async def check_admin_permissions(event: Message | CallbackQuery, user_role: str) -> bool:
    """Check if user has admin permissions and send error message if not."""
    if not is_admin(user_role):
        text = "❌ У вас нет прав для выполнения этой команды."
        if isinstance(event, Message):
            await event.answer(text)
        else:
            await event.answer(text, show_alert=True)
        return False
    return True


async def check_moderator_permissions(event: Message | CallbackQuery, user_role: str) -> bool:
    """Check if user has moderator permissions and send error message if not."""
    if not can_moderate(user_role):
        text = "❌ У вас нет прав для выполнения этой команды."
        if isinstance(event, Message):
            await event.answer(text)
        else:
            await event.answer(text, show_alert=True)
        return False
    return True