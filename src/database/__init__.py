from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from .models import Base
import logging
import os

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///tesseracts_world.db")

class DatabaseManager:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.async_session_factory = None
    
    async def initialize(self):
        """Initialize database connection and create tables."""
        self.engine = create_async_engine(
            self.database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            future=True
        )
        
        self.async_session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info(f"Database initialized at {self.database_url}")
    
    async def get_session(self) -> AsyncSession:
        """Get an async database session."""
        if not self.async_session_factory:
            await self.initialize()
        return self.async_session_factory()
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

async def get_db_session() -> AsyncSession:
    """Dependency for getting database session."""
    async with db_manager.get_session() as session:
        try:
            yield session
        finally:
            await session.close()
