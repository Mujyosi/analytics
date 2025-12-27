from pydantic import BaseModel, Field,validator
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    url: str
    page_id: str = Field(..., max_length=50)
    action: str = Field(..., max_length=20)
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow extra fields
    
    @validator('url', pre=True, always=True)
    def set_url(cls, v):
        return v or "unknown"
    
    @validator('page_id', pre=True, always=True)
    def set_page_id(cls, v):
        return v or "unknown"
    
    @validator('action', pre=True, always=True)
    def set_action(cls, v):
        return v or "unknown"


# Add this class - it's what endpoints.py is looking for
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
