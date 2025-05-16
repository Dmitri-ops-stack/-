from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config

# Создание асинхронного движка с оптимизированным пулом
engine = create_async_engine(
    config.DATABASE_URL,
    echo=True,
    pool_size=1,  # Ограничение для SQLite (одно соединение для записи)
    max_overflow=0,  # Без переполнения
    pool_timeout=30.0,  # Таймаут ожидания подключения
    pool_pre_ping=True,  # Проверка соединения перед использованием
)

# Создание декларативной базы
Base = declarative_base()

# Создание фабрики сессий
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Функция для миддлварей (генератор)
async def get_session():
    async with async_session() as session:
        yield session

# Класс-обёртка для поддержки async with
class SessionContext:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = async_session()
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            await self.session.rollback()  # Откат при исключении
        await self.session.close()

# Функция для создания сессии, совместимой с async with
def create_session():
    return SessionContext()

# Функция для закрытия движка
async def dispose_engine():
    await engine.dispose()