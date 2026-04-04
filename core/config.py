import yaml
from pathlib import Path
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# yaml konfigürasyon dosyasını yükle
BASE_DIR = Path(__file__).resolve().parent.parent
config_path = BASE_DIR / "config.yaml"


def load_config():
    if not config_path.exists():
        raise FileNotFoundError(f"Konfigürasyon dosyası bulunamadı: {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


CONFIG = load_config()


class Settings(BaseSettings):
    """
    Uygulama ayarlarını (.env) Pydantic BaseSettings ile yönetir.
    Otomatik validasyon ve tip dönüşümü sağlar.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # API Keys
    BINANCE_API_KEY: str = Field(default="")
    BINANCE_API_SECRET: str = Field(default="")

    # Database
    TIMESCALE_DB_URL: str = Field(default="")
    REDIS_URL: str = Field(default="")

    # Application
    ENVIRONMENT: str = Field(default="development")
    API_HOST: str = Field(default="127.0.0.1")
    API_PORT: int = Field(default=3000)

    # CORS
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @field_validator("BINANCE_API_KEY", "BINANCE_API_SECRET", mode="after")
    @classmethod
    def decrypt_api_keys(cls, v: str) -> str:
        """
        Eğer değer şifrelenmişse (gAAAAAB... gibi başlıyorsa) security modülü ile çözer.
        Şifrelenmemişse (düz metin) olduğu gibi döndürür.
        """
        if not v or not v.startswith("gAAAAAB"):
            return v

        try:
            from core.security import key_manager

            return key_manager.decrypt(v)
        except Exception as e:
            # Loglama için logger import edilebilir
            try:
                from core.logger import logger

                logger.error(f"API anahtarı çözme hatası: {e}")
            except ImportError:
                pass
            return ""

    @property
    def allowed_origins_list(self) -> List[str]:
        """CORS listesini döndürür"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Singleton instance
settings = Settings()

# Geriye dönük uyumluluk (Backward Compatibility)
BINANCE_API_KEY = settings.BINANCE_API_KEY
BINANCE_API_SECRET = settings.BINANCE_API_SECRET
TIMESCALE_DB_URL = settings.TIMESCALE_DB_URL
REDIS_URL = settings.REDIS_URL
ENVIRONMENT = settings.ENVIRONMENT
API_HOST = settings.API_HOST
API_PORT = settings.API_PORT
ALLOWED_ORIGINS = settings.allowed_origins_list
