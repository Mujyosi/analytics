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
def init_tables():
    """Create tables if they don't exist"""
    create_events_table = """
    CREATE TABLE IF NOT EXISTS public.events (
        id serial NOT NULL,
        hashed_ip character(64) NOT NULL,
        country character(2) NULL,
        asn integer NULL,
        device character varying(20) NULL,
        browser character varying(50) NULL,
        os character varying(50) NULL,
        page_id character varying(50) NULL,
        url text NULL,
        action character varying(20) NULL,
        referrer text NULL,
        created_at timestamp without time zone NULL DEFAULT now(),
        CONSTRAINT events_pkey PRIMARY KEY (id)
    );
    """
    
    create_ip_cache_table = """
    CREATE TABLE IF NOT EXISTS public.ip_cache (
        hashed_ip character(64) NOT NULL,
        country character(2) NULL,
        asn integer NULL,
        device character varying(20) NULL,
        browser character varying(50) NULL,
        os character varying(50) NULL,
        last_updated timestamp without time zone NULL DEFAULT now(),
        CONSTRAINT ip_cache_pkey PRIMARY KEY (hashed_ip)
    );
    """
    
    create_sessions_table = """
    CREATE TABLE IF NOT EXISTS public.sessions (
        id serial NOT NULL,
        hashed_ip character(64) NOT NULL,
        session_start timestamp without time zone NULL DEFAULT now(),
        session_end timestamp without time zone NULL,
        page_count integer NULL DEFAULT 1,
        CONSTRAINT sessions_pkey PRIMARY KEY (id)
    );
    """
    
    create_indexes = """
    CREATE INDEX IF NOT EXISTS idx_hashed_ip ON public.events USING btree (hashed_ip);
    CREATE INDEX IF NOT EXISTS idx_page_id ON public.events USING btree (page_id);
    CREATE INDEX IF NOT EXISTS idx_created_at ON public.events USING btree (created_at);
    CREATE INDEX IF NOT EXISTS idx_session_hashed_ip ON public.sessions USING btree (hashed_ip);
    CREATE INDEX IF NOT EXISTS idx_session_start ON public.sessions USING btree (session_start);
    """
    
    try:
        with db.get_cursor() as cursor:
            cursor.execute(create_events_table)
            cursor.execute(create_ip_cache_table)
            cursor.execute(create_sessions_table)
            cursor.execute(create_indexes)
            logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")
        raise