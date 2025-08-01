import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Import configuration and setup
from config import Config, setup_logging
from database import Database
from middleware import AuthMiddleware

# Import all handlers
from handlers import (
    common, moderation, tickets, profile, 
    admin, top, roles, artpoints, badwords
)

async def main():
    """Main bot function"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed")
        return
    
    # Initialize database
    db = Database(Config.DATABASE_PATH)
    await db.init_db()
    logger.info("Database initialized")
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Setup middleware
    dp.message.middleware(AuthMiddleware(db))
    dp.callback_query.middleware(AuthMiddleware(db))
    
    # Include routers
    dp.include_router(common.router)
    dp.include_router(moderation.router)
    dp.include_router(tickets.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)
    dp.include_router(top.router)
    dp.include_router(roles.router)
    dp.include_router(artpoints.router)
    dp.include_router(badwords.router)
    
    logger.info("Bot handlers registered")
    
    # Start bot
    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot session closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Critical error: {e}")
        logging.critical(f"Critical error: {e}")