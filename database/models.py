from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRight(Enum):
    """User rights enumeration"""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    ART_LEADER = "art_leader"

class PunishmentType(Enum):
    """Punishment types"""
    WARN = "warn"
    MUTE = "mute"
    BAN = "ban"

@dataclass
class User:
    """User model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    experience: int = 0
    level: int = 1
    messages_count: int = 0
    art_points: int = 0
    rights: UserRight = UserRight.USER
    custom_role: Optional[str] = None
    custom_title: Optional[str] = None
    last_xp_time: Optional[datetime] = None
    xp_multiplier: float = 1.0
    is_blocked_tickets: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Punishment:
    """Punishment model"""
    id: Optional[int] = None
    user_id: int = 0
    moderator_id: int = 0
    punishment_type: PunishmentType = PunishmentType.WARN
    reason: Optional[str] = None
    duration_minutes: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

@dataclass
class Ticket:
    """Ticket model"""
    id: Optional[int] = None
    user_id: int = 0
    message: str = ""
    status: str = "open"  # open, closed, answered
    admin_message_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class BadWord:
    """Bad word model"""
    id: Optional[int] = None
    word: str = ""
    added_by: int = 0
    created_at: Optional[datetime] = None

@dataclass
class UserRole:
    """Custom user role model"""
    id: Optional[int] = None
    user_id: int = 0
    role_name: str = ""
    assigned_by: int = 0
    created_at: Optional[datetime] = None