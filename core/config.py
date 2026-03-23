import os
import yaml
from dotenv import load_dotenv
from pathlib import Path

# Çevresel değişkenleri yükle (.env)
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# yaml konfigürasyon dosyasını yükle
config_path = BASE_DIR / 'config.yaml'

def load_config():
    if not config_path.exists():
        raise FileNotFoundError(f"Konfigürasyon dosyası bulunamadı: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

CONFIG = load_config()

# ============================================================================
# API KEY YÖNETİMİ (Şifrelenmiş)
# ============================================================================

def load_api_keys():
    """
    API anahtarlarını şifrelenmiş .env dosyasından yükle ve çöz.
    Eğer şifrelenmiş veri yoksa, düz metin ortam değişkenlerini kullan.
    """
    try:
        from core.security import key_manager
        
        # Şifrelenmiş anahtarları yükle ve çöz
        api_key, api_secret = key_manager.load_api_keys()
        
        if api_key and api_secret:
            return api_key, api_secret
        
        # Şifrelenmiş veri yoksa, ortam değişkenlerinden al (düz metin)
        return (
            os.getenv("BINANCE_API_KEY", ""),
            os.getenv("BINANCE_API_SECRET", "")
        )
    except Exception as e:
        # Hata durumunda ortam değişkenlerine fallback
        logger = None
        try:
            from core.logger import logger
            logger.error(f"API key yükleme hatası: {e}, ortam değişkenlerine fallback")
        except:
            pass
        
        return (
            os.getenv("BINANCE_API_KEY", ""),
            os.getenv("BINANCE_API_SECRET", "")
        )

# API Anahtarları (Şifrelenmiş veya Düz Metin)
BINANCE_API_KEY, BINANCE_API_SECRET = load_api_keys()

# Çevresel Değişkenler Sabitleri
TIMESCALE_DB_URL = os.getenv("TIMESCALE_DB_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
API_HOST = os.getenv("API_HOST", "127.0.0.1")
