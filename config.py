from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str  # The ID of your Channel (e.g., -100123456789)
    WEBHOOK_SECRET: str    # A password you invent to secure your webhook
    
    # Database URL (Defaults to a local data folder for Railway Volumes)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/trades.db"
    
    class Config:
        env_file = ".env"

settings = Settings()
