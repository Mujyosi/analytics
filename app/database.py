import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection_string = settings.database_url
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_cursor(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()

db = Database()

# Initialize tables
# Initialize tables
def init_tables():
    """Create tables if they don't exist"""
    # Drop existing tables first to avoid conflicts
    drop_tables = """
    DROP TABLE IF EXISTS events CASCADE;
    DROP TABLE IF EXISTS ip_cache CASCADE;
    DROP TABLE IF EXISTS sessions CASCADE;
    """
    
    create_events_table = """
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        hashed_ip VARCHAR(64) NOT NULL,
        country VARCHAR(10),
        asn INTEGER,
        device VARCHAR(50),
        browser VARCHAR(100),
        os VARCHAR(100),
        page_id VARCHAR(100),
        url TEXT,
        action VARCHAR(50),
        referrer TEXT,
        session_id VARCHAR(255),
        screen_width INTEGER,
        screen_height INTEGER,
        time_on_page INTEGER,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    create_ip_cache_table = """
    CREATE TABLE IF NOT EXISTS ip_cache (
        hashed_ip VARCHAR(64) PRIMARY KEY,
        country VARCHAR(10),
        asn INTEGER,
        device VARCHAR(50),
        browser VARCHAR(100),
        os VARCHAR(100),
        last_updated TIMESTAMP DEFAULT NOW()
    );
    """
    
    create_sessions_table = """
    CREATE TABLE IF NOT EXISTS sessions (
        id SERIAL PRIMARY KEY,
        hashed_ip VARCHAR(64) NOT NULL,
        session_id VARCHAR(255),
        session_start TIMESTAMP DEFAULT NOW(),
        session_end TIMESTAMP,
        page_count INTEGER DEFAULT 1
    );
    """
    
    create_indexes = """
    CREATE INDEX IF NOT EXISTS idx_events_hashed_ip ON events(hashed_ip);
    CREATE INDEX IF NOT EXISTS idx_events_page_id ON events(page_id);
    CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
    CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_hashed_ip ON sessions(hashed_ip);
    CREATE INDEX IF NOT EXISTS idx_sessions_session_start ON sessions(session_start);
    CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
    """
    
    try:
        with db.get_cursor() as cursor:
            # Drop old tables
            cursor.execute(drop_tables)
            logger.info("Dropped old tables")
            
            # Create new tables
            cursor.execute(create_events_table)
            cursor.execute(create_ip_cache_table)
            cursor.execute(create_sessions_table)
            cursor.execute(create_indexes)
            logger.info("Database tables recreated successfully")
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")
        raise
