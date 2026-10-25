import os
import asyncio
import ssl
import asyncpg
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН_СЮДА")
# Строка подключения от pghost.ru
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bothost_db_a8082ad66c45:3lEv7RUeVM2gC05wtPlhRReeYyrPQZ4esCv7FKfNq1w@node1.pghost.ru:16251/bothost_db_a8082ad66c45")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура
robot_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="🤖 Я не робот", callback_data="not_robot")]]
)

# --- БАЗА ДАННЫХ (ИНИЦИАЛИЗАЦИЯ) ---
async def init_db(pool: asyncpg.Pool):
    """Создает таблицу при первом запуске"""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                first_name VARCHAR(255),
                username VARCHAR(255),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    print("✅ База данных готова. Таблица users создана.")

# --- ХЕНДЛЕРЫ ---
@dp.message(F.text == "/start")
async def start_handler(message: Message, pool: asyncpg.Pool):
    # Сохраняем юзера в БД (быстро и асинхронно, берем соединение из пула)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, first_name, username) 
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE 
            SET first_name = EXCLUDED.first_name, username = EXCLUDED.username
        """, message.from_user.id, message.from_user.first_name, message.from_user.username)
    
    await message.answer(
        "Добро пожаловать!\n\nНажми на кнопку ниже 👇",
        reply_markup=robot_kb
    )

@dp.callback_query(F.data == "not_robot")
async def not_robot_handler(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    
    greeting = await callback.message.answer(f"Привет, {callback.from_user.first_name}!")
    
    await asyncio.sleep(5)
    await greeting.delete()

# --- ЗАПУСК ---
async def main():
    # Создаем SSL контекст (pghost.ru часто требует)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    # СОЗДАЕМ ПУЛ ОДИН РАЗ ПРИ СТАРТЕ (min 1, max 10 соединений)
    pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=1,
        max_size=10,
        ssl=ssl_ctx
    )
    
    # Инициализируем БД
    await init_db(pool)
    
    # Передаем пул в диспетчер, чтобы он был доступен в хендлерах
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот запущен!")
    await dp.start_polling(bot, pool=pool)

if __name__ == "__main__":
    asyncio.run(main())
