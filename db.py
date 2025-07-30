import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SQLITE_PATH = os.getenv("SQLITE_PATH", "canon_media.db")
DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def get_session():
    return AsyncSessionLocal()
