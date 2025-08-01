import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Bot configuration class"""
    
    # Bot settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_GROUP_ID: int = int(os.getenv("ADMIN_GROUP_ID", "0"))
    TICKETS_GROUP_ID: int = int(os.getenv("TICKETS_GROUP_ID", "0"))
    
    # Database settings
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
    
    # Experience settings
    XP_MIN: int = 5
    XP_MAX: int = 20
    XP_COOLDOWN: int = 20  # seconds
    
    # Moderation settings
    MAX_WARNS: int = 3
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            logging.error("BOT_TOKEN is required")
            return False
        if not cls.ADMIN_GROUP_ID:
            logging.warning("ADMIN_GROUP_ID not set - some features may not work")
        if not cls.TICKETS_GROUP_ID:
            logging.warning("TICKETS_GROUP_ID not set - ticket system disabled")
        return True

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler]
    )