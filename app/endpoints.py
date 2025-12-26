from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import json
import logging

from app.models import EventCreate, EventResponse
from app.database import db, init_tables
from app.redis_client import redis_client
from app.ip_utils import ip_utils
from app.utils import get_ip_address, update_session

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_ip_metadata_cached(ip_address: str) -> Dict[str, Any]:
    """
    Get IP metadata with Redis caching
    """
    hashed_ip = ip_utils.hash_ip(ip_address)
    
    # Check Redis cache first
    cached = redis_client.get(hashed_ip)
    if cached:
        logger.info(f"Cache hit for IP: {hashed_ip[:8]}...")
        return ip_utils.deserialize_metadata(cached)
    
    # Cache miss, fetch from external API
    logger.info(f"Cache miss for IP: {hashed_ip[:8]}..., fetching metadata")
    metadata = await ip_utils.get_ip_metadata(ip_address)
    
    # Store in Redis
    if metadata["country"] or metadata["asn"]:  # Only cache if we got useful data
        redis_client.set(
            hashed_ip,
            ip_utils.serialize_metadata(metadata)
        )
        logger.info(f"Cached metadata for IP: {hashed_ip[:8]}...")
    
    return metadata

@router.post("/collect", response_model=Dict[str, str])
async def collect_event(
    event: EventCreate,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Collect analytics event from movie site
    """
    try:
        # 1. Extract and hash IP
        ip_address = get_ip_address(request)
        hashed_ip = ip_utils.hash_ip(ip_address)
        
        # 2. Get IP metadata (cached or from API)
        ip_metadata = await get_ip_metadata_cached(ip_address)
        
        # 3. Parse user agent if provided
        user_agent_info = {}
        if event.user_agent:
            user_agent_info = ip_utils.parse_user_agent(event.user_agent)
        
        # 4. Insert event into PostgreSQL
        with db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO events (
                    hashed_ip, country, asn, device, browser, os,
                    page_id, url, action, referrer
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                hashed_ip,
                ip_metadata.get("country"),
                ip_metadata.get("asn"),
                user_agent_info.get("device"),
                user_agent_info.get("browser"),
                user_agent_info.get("os"),
                event.page_id,
                event.url,
                event.action,
                event.referrer
            ))
            
            event_id = cursor.fetchone()["id"]
            logger.info(f"Event recorded: {event_id} for IP: {hashed_ip[:8]}...")
        
        # 5. Update session in background
        background_tasks.add_task(update_session, hashed_ip, db)
        
        return {"status": "ok", "message": "Event recorded"}
        
    except Exception as e:
        logger.error(f"Error collecting event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        redis_client.client.ping()
        
        # Check PostgreSQL
        with db.get_cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "redis": "connected",
            "postgresql": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# Optional: Add endpoint to view stats (for debugging)
@router.get("/stats")
async def get_stats():
    """Get basic statistics"""
    try:
        with db.get_cursor() as cursor:
            # Total events
            cursor.execute("SELECT COUNT(*) as total_events FROM events")
            total_events = cursor.fetchone()["total_events"]
            
            # Events today
            cursor.execute("""
                SELECT COUNT(*) as today_events 
                FROM events 
                WHERE created_at >= CURRENT_DATE
            """)
            today_events = cursor.fetchone()["today_events"]
            
            # Unique IPs
            cursor.execute("SELECT COUNT(DISTINCT hashed_ip) as unique_ips FROM events")
            unique_ips = cursor.fetchone()["unique_ips"]
            
            # Top pages
            cursor.execute("""
                SELECT page_id, COUNT(*) as views 
                FROM events 
                WHERE action = 'view' 
                GROUP BY page_id 
                ORDER BY views DESC 
                LIMIT 10
            """)
            top_pages = cursor.fetchall()
            
        return {
            "total_events": total_events,
            "today_events": today_events,
            "unique_ips": unique_ips,
            "top_pages": top_pages
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")