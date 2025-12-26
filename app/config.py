from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Redis
    redis_url: str
    redis_tls: bool = True
    
    # Database
    database_url: str
    
    # IP Service (optional)
    ipinfo_token: Optional[str] = None
    
    # App
    environment: str = "development"
    log_level: str = "INFO"
    cache_ttl_days: int = 14
    
    # Security
    allowed_origins: list = ["*"]
    
    class Config:
        env_file = ".env"

settings = Settings()