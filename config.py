from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str

    # Secret used in your TradingView webhook URL:
    # https://your-app.up.railway.app/webhook?secret=YOUR_SECRET
    WEBHOOK_SECRET: str

    # Optional.
    # If set, only this Telegram user ID can use bot commands like /stats.
    # Leave empty to allow anyone.
    TELEGRAM_ADMIN_USER_ID: Optional[str] = None

    # Railway volume path:
    # Make sure the volume is mounted at /app/data
    DATABASE_URL: str = "sqlite:///./data/trades.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
