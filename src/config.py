from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings."""
    APP_NAME: str = "News Condenser"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 