"""
Database models and initialization
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, JSON, Float
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class MeetingSession(Base):
    """Meeting session model"""
    __tablename__ = "meeting_sessions"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    transcript = Column(Text, nullable=True)
    full_transcript = Column(Text, nullable=True)
    mom = Column(JSON, nullable=True)
    faqs = Column(JSON, nullable=True)
    email_draft = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)


class MicrosoftAuth(Base):
    """Microsoft OAuth token storage"""
    __tablename__ = "microsoft_auth"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, unique=True, default="default")
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    token_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=lambda: datetime.utcnow())


class TodoItem(Base):
    """Todo item model"""
    __tablename__ = "todo_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=False, default="medium")  # low, medium, high, critical
    order = Column(Float, nullable=True, default=0.0)  # Order within same priority level
    is_completed = Column(Boolean, default=False)
    source_type = Column(String, nullable=True)  # email, teams, meeting, action_item, etc.
    source_id = Column(String, nullable=True)  # ID of the source item
    source_data = Column(JSON, nullable=True)  # Additional context about the source
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=lambda: datetime.utcnow())
    completed_at = Column(DateTime, nullable=True)


# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./meetings.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables and run migrations"""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
        # Migration: Add missing columns if they don't exist
        def add_missing_columns(connection):
            try:
                # Get the underlying SQLite connection from aiosqlite
                raw_conn = connection.connection.dbapi_connection
                if raw_conn:
                    cursor = raw_conn.cursor()
                    # Check if table exists and get existing columns
                    cursor.execute("PRAGMA table_info(meeting_sessions)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Add full_transcript column if it doesn't exist
                    if 'full_transcript' not in columns:
                        cursor.execute("ALTER TABLE meeting_sessions ADD COLUMN full_transcript TEXT")
                        raw_conn.commit()
                    
                    # Add risks column if it doesn't exist
                    if 'risks' not in columns:
                        cursor.execute("ALTER TABLE meeting_sessions ADD COLUMN risks TEXT")
                        raw_conn.commit()
                    
                    # Add mom column if it doesn't exist
                    if 'mom' not in columns:
                        cursor.execute("ALTER TABLE meeting_sessions ADD COLUMN mom TEXT")
                        raw_conn.commit()
                    
                    # Add faqs column if it doesn't exist
                    if 'faqs' not in columns:
                        cursor.execute("ALTER TABLE meeting_sessions ADD COLUMN faqs TEXT")
                        raw_conn.commit()
                    
                    # Add email_draft column if it doesn't exist
                    if 'email_draft' not in columns:
                        cursor.execute("ALTER TABLE meeting_sessions ADD COLUMN email_draft TEXT")
                        raw_conn.commit()
                    
                    cursor.close()
                    
                    # Create microsoft_auth table if it doesn't exist
                    cursor = raw_conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS microsoft_auth (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT NOT NULL UNIQUE DEFAULT 'default',
                            access_token TEXT,
                            refresh_token TEXT,
                            expires_at TEXT,
                            token_type TEXT,
                            created_at TEXT,
                            updated_at TEXT
                        )
                    """)
                    raw_conn.commit()
                    cursor.close()
                    
                    # Create todo_items table if it doesn't exist
                    cursor = raw_conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS todo_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            description TEXT,
                            priority TEXT NOT NULL DEFAULT 'medium',
                            "order" REAL DEFAULT 0.0,
                            is_completed INTEGER NOT NULL DEFAULT 0,
                            source_type TEXT,
                            source_id TEXT,
                            source_data TEXT,
                            created_at TEXT,
                            updated_at TEXT,
                            completed_at TEXT
                        )
                    """)
                    raw_conn.commit()
                    
                    # Add order column if it doesn't exist (migration)
                    cursor.execute("PRAGMA table_info(todo_items)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'order' not in columns:
                        cursor.execute('ALTER TABLE todo_items ADD COLUMN "order" REAL DEFAULT 0.0')
                        raw_conn.commit()
                    
                    cursor.close()
            except (AttributeError, Exception) as e:
                # If migration fails, it's okay - column might already exist or table might not exist yet
                print(f"Migration note: {e}")
        
        await conn.run_sync(add_missing_columns)


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
