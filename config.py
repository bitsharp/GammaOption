"""Configuration management for GammaOption application."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

# Load environment variables
load_dotenv()

class Config(BaseModel):
    """Application configuration."""
    
    # API Keys
    polygon_api_key: str = Field(default_factory=lambda: os.getenv("POLYGON_API_KEY", ""))
    
    # Telegram
    telegram_bot_token: Optional[str] = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: Optional[str] = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID"))
    
    # Discord
    discord_webhook_url: Optional[str] = Field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL"))
    
    # Email
    email_smtp_server: Optional[str] = Field(default_factory=lambda: os.getenv("EMAIL_SMTP_SERVER"))
    email_smtp_port: Optional[int] = Field(default_factory=lambda: int(os.getenv("EMAIL_SMTP_PORT", "587")))
    email_from: Optional[str] = Field(default_factory=lambda: os.getenv("EMAIL_FROM"))
    email_password: Optional[str] = Field(default_factory=lambda: os.getenv("EMAIL_PASSWORD"))
    email_to: Optional[str] = Field(default_factory=lambda: os.getenv("EMAIL_TO"))
    
    # Trading parameters
    spx_symbol: str = Field(default_factory=lambda: os.getenv("SPX_SYMBOL", "SPX"))
    es_symbol: str = Field(default_factory=lambda: os.getenv("ES_SYMBOL", "ES"))
    strike_range_percent: float = Field(default_factory=lambda: float(os.getenv("STRIKE_RANGE_PERCENT", "1.5")))
    min_volume_threshold: int = Field(default_factory=lambda: int(os.getenv("MIN_VOLUME_THRESHOLD", "50")))
    top_levels_count: int = Field(default_factory=lambda: int(os.getenv("TOP_LEVELS_COUNT", "5")))
    alert_distance_threshold: float = Field(default_factory=lambda: float(os.getenv("ALERT_DISTANCE_THRESHOLD", "0.5")))
    
    # Timezone
    timezone: str = Field(default_factory=lambda: os.getenv("TIMEZONE", "Europe/Rome"))
    
    # Paths
    data_dir: Path = Path("data")
    logs_dir: Path = Path("logs")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

# Global config instance
config = Config()
