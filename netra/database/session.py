from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import settings
from models.base import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        # For production we use Alembic, but for initial setup:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
