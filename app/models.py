from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

class EventBase(BaseModel):
    url: str
    page_id: str = Field(..., max_length=50)
    action: str = Field(..., max_length=20)
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    timestamp: Optional[str] = None
    # Allow any extra fields that might be sent
    extra_data: Optional[Dict[str, Any]] = {}
    
    class Config:
        extra = "allow"  # This allows extra fields
    
    @validator('url', pre=True, always=True)
    def set_url(cls, v):
        return v or "unknown"
    
    @validator('page_id', pre=True, always=True)
    def set_page_id(cls, v):
        return v or "unknown"
    
    @validator('action', pre=True, always=True)
    def set_action(cls, v):
        return v or "unknown"
    
    @validator('screen_width', 'screen_height', pre=True)
    def validate_screen_dimensions(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


class EventCreate(EventBase):
    pass


class EventResponse(BaseModel):
    id: int
    hashed_ip: str
    country: Optional[str]
    asn: Optional[int]
    device: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    page_id: str
    url: str
    action: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class IPMetadata(BaseModel):
    country: Optional[str] = None
    asn: Optional[int] = None
    device: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
