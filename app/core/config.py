from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings. Environment variables can be used to override these values.
    """
    # API Settings
    API_VERSION: str = "v1"
    API_TITLE: str = "Educational Content Generation API"
    API_DESCRIPTION: str = "API for generating and managing educational content for K-8 students"
    DEBUG: bool = False
    API_BASE_URL: str = "http://localhost:8000"

    # Auto Calibration
    AUTO_CALIBRATE: bool = False

    # Supabase Settings
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SECRET_KEY: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # OpenAI Settings
    OPENAI_API_KEY: str
    GPT_MODEL: str = "gpt-4-turbo-preview"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env file


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Returns:
        Settings: Application settings instance
    """
    return Settings() 