import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MedMirror Agent"
    API_V1_STR: str = "/api/v1"
    
    # LLM Settings
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = "sk-proj-placeholder"
    LLM_MODEL: str = "gpt-3.5-turbo"

    model_config = SettingsConfigDict(
        env_file=".env.local", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

