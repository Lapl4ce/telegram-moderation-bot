import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.database import init_db
from handlers import (
    moderation, tickets, profile, admin, 
    top, roles, artpoints, badwords, common
)
from middleware.auth import AuthMiddleware
from utils.experience import ExperienceHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота"""
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера
    dp = Dispatcher(storage=MemoryStorage())
    
    # Инициализация базы данных
    await init_db()
    
    # Подключение middleware
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Подключение обработчиков опыта
    experience_handler = ExperienceHandler()
    dp.message.middleware(experience_handler)
    
    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(moderation.router)
    dp.include_router(tickets.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)
    dp.include_router(top.router)
    dp.include_router(roles.router)
    dp.include_router(artpoints.router)
    dp.include_router(badwords.router)
    
    logger.info("Бот запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
