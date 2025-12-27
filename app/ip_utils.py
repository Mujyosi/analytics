# app/ip_utils.py
import hashlib
import json
from typing import Optional, Dict, Any
import httpx
from app.config import settings
import logging
from user_agents import parse
import re

logger = logging.getLogger(__name__)

class IPUtils:
    @staticmethod
    def hash_ip(ip_address: str) -> str:
        """Hash IP address for privacy"""
        return hashlib.sha256(ip_address.encode()).hexdigest()
    
    @staticmethod
    def parse_user_agent(user_agent: str) -> Dict[str, Optional[str]]:
        """Parse user agent string to get device, browser, OS info"""
        try:
            ua = parse(user_agent)
            return {
                "device": "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop"),
                "browser": ua.browser.family[:50] if ua.browser.family else None,
                "os": ua.os.family[:50] if ua.os.family else None
            }
        except Exception as e:
            logger.error(f"Failed to parse user agent: {e}")
            return {"device": None, "browser": None, "os": None}

    @staticmethod
    def _is_local_ip(ip_address: str) -> bool:
        """Check if IP address is local or reserved"""
        # IPv4 localhost
        if ip_address == "127.0.0.1":
            return True
        # IPv6 localhost
        if ip_address == "::1":
            return True
        # Private IPv4 ranges
        if '.' in ip_address:
            parts = ip_address.split('.')
            if len(parts) == 4:
                try:
                    first = int(parts[0])
                    second = int(parts[1])
                    if first == 10:
                        return True
                    if first == 172 and 16 <= second <= 31:
                        return True
                    if first == 192 and second == 168:
                        return True
                    if first == 169 and second == 254:
                        return True
                except ValueError:
                    pass
        return False

    @staticmethod
    async def get_ip_metadata(ip_address: str) -> Dict[str, Any]:
        """
        Get IP metadata from IPinfo Lite.
        Ensures 'asn' is always int or None.
        """
        metadata = {
            "country": None,
            "asn": None,  # Must stay None if missing
            "device": None,
            "browser": None,
            "os": None
        }

        if IPUtils._is_local_ip(ip_address):
            metadata["country"] = "Local"
            return metadata

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                url = f"https://ipinfo.io/{ip_address}/json?token={getattr(settings, 'IPINFO_TOKEN', '')}"
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    metadata["country"] = data.get("country")
                    
                    # Parse ASN safely
                    org = data.get("org", "")
                    if org:
                        match = re.search(r'AS(\d+)', org)
                        if match:
                            try:
                                metadata["asn"] = int(match.group(1))
                            except (ValueError, TypeError):
                                metadata["asn"] = None
                        else:
                            metadata["asn"] = None
                    else:
                        metadata["asn"] = None
                elif res.status_code in (429, 403):
                    logger.warning(f"IPinfo rate limit or access error for IP: {ip_address}")
                else:
                    logger.error(f"IPinfo API returned {res.status_code} for IP: {ip_address}")
        except Exception as e:
            logger.error(f"Error fetching IP metadata for {ip_address}: {e}")

        return metadata

    @staticmethod
    def serialize_metadata(metadata: Dict[str, Any]) -> str:
        """Serialize metadata dict to JSON string for Redis"""
        return json.dumps(metadata)

    @staticmethod
    def deserialize_metadata(metadata_str: str) -> Dict[str, Any]:
        """Deserialize JSON string from Redis to dict"""
        try:
            return json.loads(metadata_str)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    async def get_cached_or_fetch(ip_address: str, cache_client: Optional[Any] = None,
                                  cache_ttl: int = 604800) -> Dict[str, Any]:
        """
        Get IP metadata with optional caching (1 week default TTL)
        cache_client must have async get/setex methods like aioredis.
        """
        cache_key = f"ip_metadata:{ip_address}"
        if cache_client:
            try:
                cached_data = await cache_client.get(cache_key)
                if cached_data:
                    return IPUtils.deserialize_metadata(cached_data)
            except Exception as e:
                logger.error(f"Cache read error for {ip_address}: {e}")

        metadata = await IPUtils.get_ip_metadata(ip_address)

        if cache_client and metadata.get("country"):
            try:
                serialized = IPUtils.serialize_metadata(metadata)
                await cache_client.setex(cache_key, cache_ttl, serialized)
            except Exception as e:
                logger.error(f"Cache write error for {ip_address}: {e}")

        return metadata

ip_utils = IPUtils()
