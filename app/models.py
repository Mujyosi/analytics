from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    url: str
    page_id: str = Field(..., max_length=50)
    action: str = Field(..., max_length=20)
    referrer: Optional[str] = None
    user_agent: Optional[str] = None

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