"""
Example configuration file for the Telegram moderation bot.
Copy this file to config.py and fill in your actual values.
"""
import os
from typing import List, Dict

# Bot configuration - REQUIRED
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Group chat IDs - REQUIRED for full functionality
MAIN_GROUP_ID: int = 0  # Replace with your main group chat ID
MODERATOR_GROUP_ID: int = 0  # Replace with your moderator group chat ID

# Admin and moderator user IDs - REQUIRED
ADMIN_IDS: List[int] = [
    # 123456789,  # Add admin user IDs here
]

MODERATOR_IDS: List[int] = [
    # 987654321,  # Add moderator user IDs here
]

ART_LEADER_IDS: List[int] = [
    # 456789123,  # Add art leader user IDs here
]

# Database configuration
DATABASE_PATH = "bot_database.db"

# Moderation configuration
MAX_WARNINGS = 3
DEFAULT_MUTE_TIME = 3600  # 1 hour in seconds
DEFAULT_BAN_TIME = 86400  # 24 hours in seconds

# Experience system configuration
XP_PER_MESSAGE_MIN = 5
XP_PER_MESSAGE_MAX = 20
XP_COOLDOWN = 20  # seconds between XP gains
STICKER_UNLOCK_LEVEL = 25

# Level calculation: exp = 3 * level² + 50 * level + 100
def calculate_required_exp(level: int) -> int:
    """Calculate required experience for a specific level."""
    return 3 * (level ** 2) + 50 * level + 100

def calculate_level_from_exp(exp: int) -> int:
    """Calculate level from total experience."""
    level = 1
    while calculate_required_exp(level) <= exp:
        level += 1
    return level - 1

# User titles based on level
USER_TITLES: Dict[int, str] = {
    1: "Землянин",
    5: "Исследователь",
    10: "Путешественник",
    15: "Первопроходец",
    20: "Космонавт",
    25: "Планета",
    30: "Звезда",
    35: "Солнечная система",
    40: "Галактика",
    45: "Суперкластер"
}

def get_user_title(level: int) -> str:
    """Get user title based on level."""
    title = "Землянин"
    for req_level, level_title in USER_TITLES.items():
        if level >= req_level:
            title = level_title
        else:
            break
    return title

# Pagination settings
ITEMS_PER_PAGE = 10
TOP_USERS_PER_PAGE = 10

# Experience multiplier limits
MIN_XP_MULTIPLIER = 0.1
MAX_XP_MULTIPLIER = 10.0
DEFAULT_XP_MULTIPLIER = 1.0