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
    async def get_ip_metadata(ip_address: str) -> Dict[str, Any]:
        """
        Get IP metadata from external service.
        You can use IPinfo, ipapi, or any other service.
        """
        metadata = {
            "country": None,
            "asn": None,
            "device": None,
            "browser": None,
            "os": None
        }
        
        # Method 1: Use IPinfo (requires token)
        if settings.ipinfo_token:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    url = f"https://ipinfo.io/{ip_address}/json?token={settings.ipinfo_token}"
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        metadata["country"] = data.get("country")
                        
                        # Parse ASN from org field (format: "AS12345 Org Name")
                        org = data.get("org", "")
                        asn_match = re.search(r'AS(\d+)', org)
                        if asn_match:
                            metadata["asn"] = int(asn_match.group(1))
            except Exception as e:
                logger.error(f"IPinfo API error: {e}")
        
        # Method 2: Fallback to free service (ip-api.com)
        if not metadata["country"]:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    url = f"http://ip-api.com/json/{ip_address}"
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success":
                            metadata["country"] = data.get("countryCode")
                            metadata["asn"] = data.get("asn", "").replace("AS", "")
            except Exception as e:
                logger.error(f"ip-api.com error: {e}")
        
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

ip_utils = IPUtils()