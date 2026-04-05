"""
Security Module - AES-128-CBC Encryption (Fernet)

API anahtarlarını şifrelemek ve çözmek için kullanılır.
cryptography.fernet kütüphanesi kullanır (AES-128-CBC standart).

Usage:
    from core.security import KeyManager
    
    key_manager = KeyManager()
    
    # Şifrele
    encrypted = key_manager.encrypt("my_api_key")
    
    # Çöz
    decrypted = key_manager.decrypt(encrypted)
    
    # API anahtarlarını kaydet
    key_manager.save_api_keys(api_key, api_secret)
    
    # API anahtarlarını oku
    api_key, api_secret = key_manager.load_api_keys()
"""

import os
from pathlib import Path
from cryptography.fernet import Fernet
from core.logger import logger


class KeyManager:
    """
    API Key Manager with AES-128-CBC Encryption.
    
    .secret.key dosyasından şifreleme anahtarı üretir/yükler.
    API anahtarlarını şifreleyerek .env dosyasına kaydeder.
    """
    
    def __init__(self):
        self.key_file = Path(".secret.key")
        self.env_file = Path(".env")
        self.fernet = None
        
        # Şifreleme anahtarını yükle veya oluştur
        self._load_or_create_key()
        
        logger.info("🔐 [SECURITY] KeyManager initialized (AES-128-CBC)")
    
    def _load_or_create_key(self):
        """
        .secret.key dosyasından anahtar yükle veya yeni oluştur.
        """
        if self.key_file.exists():
            # Mevcut anahtarı yükle
            try:
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                self.fernet = Fernet(key)
                logger.debug("🔑 [SECURITY] Şifreleme anahtarı yüklendi")
            except Exception as e:
                logger.error(f"❌ [SECURITY] Anahtar yükleme hatası: {e}")
                self._create_new_key()
        else:
            # Yeni anahtar oluştur
            self._create_new_key()
    
    def _create_new_key(self):
        """
        Yeni şifreleme anahtarı oluştur ve kaydet.
        Dosya izinleri: 0o600 (sadece owner okuyabilir)
        """
        try:
            # Fernet anahtarı oluştur
            key = Fernet.generate_key()
            
            # Dosyaya kaydet
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Dosya izinlerini ayarla (0o600 = sadece owner)
            os.chmod(self.key_file, 0o600)
            
            self.fernet = Fernet(key)
            
            logger.info("🔑 [SECURITY] Yeni şifreleme anahtarı oluşturuldu (.secret.key)")
            logger.info("📁 [SECURITY] Dosya izinleri: 0o600 (sadece owner)")
            
        except Exception as e:
            logger.error(f"❌ [SECURITY] Anahtar oluşturma hatası: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """
        Veriyi şifrele.
        
        Args:
            data: Şifrelenecek veri
        
        Returns:
            Şifrelenmiş veri (gAAAAABh... formatında)
        """
        try:
            encrypted = self.fernet.encrypt(data.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ [SECURITY] Şifreleme hatası: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Veriyi çöz.
        
        Args:
            encrypted_data: Şifrelenmiş veri
        
        Returns:
            Çözülmüş veri
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ [SECURITY] Şifre çözme hatası: {e}")
            raise
    
    def save_api_keys(self, api_key: str, api_secret: str):
        """
        API anahtarlarını şifreleyerek .env dosyasına kaydet.
        
        Args:
            api_key: Binance API Key
            api_secret: Binance API Secret
        """
        try:
            # Şifrele
            encrypted_key = self.encrypt(api_key)
            encrypted_secret = self.encrypt(api_secret)
            
            # .env dosyasını oku
            env_data = {}
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env_data[key] = value
            
            # API anahtarlarını güncelle
            env_data['BINANCE_API_KEY'] = encrypted_key
            env_data['BINANCE_API_SECRET'] = encrypted_secret
            
            # .env dosyasına yaz
            with open(self.env_file, 'w', encoding='utf-8') as f:
                for key, value in env_data.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("✅ [SECURITY] API anahtarları şifrelenerek kaydedildi")
            
        except Exception as e:
            logger.error(f"❌ [SECURITY] API anahtarı kaydetme hatası: {e}")
            raise
    
    def load_api_keys(self) -> tuple:
        """
        .env dosyasından şifrelenmiş API anahtarlarını yükle ve çöz.
        
        Returns:
            (api_key, api_secret) tuple
        """
        try:
            if not self.env_file.exists():
                logger.warning("⚠️ [SECURITY] .env dosyası yok")
                return None, None
            
            # .env dosyasını oku
            env_data = {}
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_data[key] = value
            
            # Şifrelenmiş anahtarları al
            encrypted_key = env_data.get('BINANCE_API_KEY')
            encrypted_secret = env_data.get('BINANCE_API_SECRET')
            
            if not encrypted_key or not encrypted_secret:
                logger.warning("⚠️ [SECURITY] API anahtarları bulunamadı")
                return None, None
            
            # Çöz
            api_key = self.decrypt(encrypted_key)
            api_secret = self.decrypt(encrypted_secret)
            
            logger.debug("🔓 [SECURITY] API anahtarları çözüldü")
            
            return api_key, api_secret
            
        except Exception as e:
            logger.error(f"❌ [SECURITY] API anahtarı yükleme hatası: {e}")
            return None, None


# Singleton instance
key_manager = KeyManager()

# Export
__all__ = ['KeyManager', 'key_manager']
