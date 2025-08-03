"""Configuration file for the Telegram moderation bot."""

import os
from typing import List

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
TICKET_GROUP_ID = int(os.getenv("TICKET_GROUP_ID", "0"))

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Moderation settings
WARN_LIMIT = 3
MUTE_DURATION_DEFAULT = 3600  # 1 hour in seconds
BAN_DURATION_DEFAULT = 86400  # 1 day in seconds

# Experience settings
XP_PER_MESSAGE_MIN = 5
XP_PER_MESSAGE_MAX = 20
XP_COOLDOWN = 20  # seconds
STICKER_LEVEL_REQUIREMENT = 25

# Forbidden words list
FORBIDDEN_WORDS: List[str] = [
    # Add forbidden words here
    "spam", "scam", "hack"
]

# User roles
class UserRoles:
    MEMBER = "member"
    MODERATOR = "moderator"
    ADMIN = "admin"
    ART_LEADER = "art_leader"

# Titles based on levels
TITLES = {
    0: "Землянин",
    5: "Спутник",
    10: "Планета",
    15: "Звезда",
    20: "Созвездие",
    25: "Галактика",
    30: "Квазар",
    35: "Скопление",
    40: "Суперкластер"
}