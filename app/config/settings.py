from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/stayease",
        alias="DATABASE_URL",
    )
    model_name: str = Field(default="llama-3.3-70b-versatile", alias="MODEL_NAME")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "case_sensitive": False,
    }


settings = Settings()