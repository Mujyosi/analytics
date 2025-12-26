import redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_url = settings.redis_url
        self.redis_tls = settings.redis_tls
        self.client = None
        self.connect()
    
    def connect(self):
        try:
            # Ensure URL has proper scheme
            url = self.redis_url
            if not url.startswith(('redis://', 'rediss://', 'unix://')):
                # Add scheme based on TLS setting
                scheme = 'rediss://' if self.redis_tls else 'redis://'
                url = f"{scheme}{url}"
            
            self.client = redis.from_url(
                url,
                decode_responses=True
            )
            
            # Test connection
            self.client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    def get(self, key: str):
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl_days: int = None):
        try:
            if ttl_days is None:
                ttl_days = settings.cache_ttl_days
            ttl_seconds = ttl_days * 24 * 60 * 60
            return self.client.setex(key, ttl_seconds, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str):
        try:
            return self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

redis_client = RedisClient()