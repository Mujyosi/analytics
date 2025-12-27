# app/utils.py
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def get_ip_address(request: Request) -> str:
    """Extract IP address from request, handling Cloudflare headers"""
    # Cloudflare passes real IP in cf-connecting-ip header
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    
    # Fallback to X-Forwarded-For (common with proxies)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # X-Forwarded-For can contain multiple IPs, first is original
        return xff.split(",")[0].strip()
    
    # Last resort: client host
    return request.client.host

def sanitize_int(value: Optional[Any]) -> Optional[int]:
    """Convert empty string or invalid value to None for integer fields"""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

async def update_session(hashed_ip: str, session_id: Optional[str], db):
    """Update or create session for IP with session_id"""
    logger = logging.getLogger("app.utils")
    try:
        with db.get_cursor() as cursor:
            if session_id:
                # Use session_id if available
                cursor.execute("""
                    SELECT id, page_count 
                    FROM sessions 
                    WHERE session_id = %s 
                    AND session_end IS NULL 
                    AND session_start > NOW() - INTERVAL '30 minutes'
                    ORDER BY session_start DESC 
                    LIMIT 1
                """, (session_id,))
            else:
                # Fallback to IP
                cursor.execute("""
                    SELECT id, page_count 
                    FROM sessions 
                    WHERE hashed_ip = %s 
                    AND session_end IS NULL 
                    AND session_start > NOW() - INTERVAL '30 minutes'
                    ORDER BY session_start DESC 
                    LIMIT 1
                """, (hashed_ip,))
            
            session = cursor.fetchone()
            
            if session:
                # Update existing session
                cursor.execute("""
                    UPDATE sessions 
                    SET page_count = %s 
                    WHERE id = %s
                """, (sanitize_int(session['page_count']) + 1, session['id']))
            else:
                # End previous sessions for this hashed_ip
                cursor.execute("""
                    UPDATE sessions 
                    SET session_end = NOW() 
                    WHERE hashed_ip = %s 
                    AND session_end IS NULL
                """, (hashed_ip,))
                
                # Create new session
                cursor.execute("""
                    INSERT INTO sessions (hashed_ip, session_id, page_count) 
                    VALUES (%s, %s, 1)
                """, (hashed_ip, session_id))
    except Exception as e:
        logger.error(f"Session update error for {hashed_ip}: {e}")
