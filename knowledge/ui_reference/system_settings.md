# ⚙️ Sistem Ayarları (System Settings)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-settings)

---

## 📋 Genel Bakış

**Sistem Ayarları** sekmesi, botun tüm yapılandırma parametrelerini (Risk, Bot, WFO, ML, HTF, API Keys) yönetmek için kullanılan merkezi kontrol panelidir.

---

## 📁 Konum

```
Sol Menü → ⚙️ Sistem Ayarları
```

**Tab ID:** `tab-settings`

---

## 🏗️ Arayüz Düzeni

```
┌─────────────────────────────────────────────────────────┐
│  1. BOT BAŞLATMA MERKEZİ                                │
│     - Sembol, Strateji, Timeframe, Market, Marjin       │
│     - ▶ Bot Başlat butonu                               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  2. AKTİF BOTLAR                                        │
│     - Çalışan bot listesi                               │
│     - Bot yönetimi (Durdur, Devam, Sil)                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  3. RİSK AYARLARI                                       │
│     - Max Risk (%0.1 - %5.0)                            │
│     - Max Kaldıraç (1x - 50x)                           │
│     - Max Pozisyon (1 - 20)                             │
│     - Ardışık Kayıp (0 - 50)                            │
│     - Kill Switch (Aktif/Pasif)                         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  4. BOT YAPILANDIRMASI                                  │
│     - Borsa (Binance, Testnet)                          │
│     - Ortam (Development, Production)                   │
│     - Log Level (DEBUG, INFO, WARNING, ERROR)           │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  5. WFO & ML AYARLARI                                   │
│     - WFO: Eğitim/Test günleri, Re-opt interval         │
│     - ML: Confidence threshold                          │
│     - HTF: Altın Oran, EMA Stack                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  6. KALMAN FİLTRESİ                                     │
│     - Process Noise (Q)                                 │
│     - Measurement Noise (R)                             │
│     - Plug & Play: Tüm stratejiler için otomatik        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  7. MUM KAPANış KİLİDİ                                  │
│     - Kontrol Aralığı (5-60 saniye)                     │
│     - False sinyal önleme (HTF botları için kritik)     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  8. API YÖNETİMİ                                        │
│     - Binance API Key (Şifreli)                         │
│     - Binance Secret Key (Şifreli)                      │
│     - 🔑 Şifrele ve Kaydet                              │
│     - 🔄 Bağlantıyı Test Et                             │
└─────────────────────────────────────────────────────────┘
```

---

## 1. RİSK LİMİTLERİ (Trading & Finans)

### **1.1 Max Risk Per Trade (%0.1 - %5.0)**

**Input:**
- **ID:** `#risk-max-risk`
- **Tip:** Number Input
- **Min:** `0.1` (%0.1)
- **Max:** `5.0` (%5.0)
- **Step:** `0.1`
- **Varsayılan:** `0.2` (%0.2)

**Validasyon:**
```javascript
// frontend/app.js
function validateRiskSettings() {
    const maxRisk = parseFloat(document.getElementById('risk-max-risk').value);
    
    if (maxRisk < 0.1 || maxRisk > 5.0) {
        showToast('⚠️ Risk %0.1 ile %5.0 arasında olmalı!', 'warning');
        return false;
    }
    
    return true;
}
```

**Matematiksel Formül:**
```
Position Size = (Balance × Risk%) / |Entry - Stop|

Örnek:
  Balance: $10,000
  Risk: %0.2 → $20
  Entry: $50,000
  Stop: $49,000 (mesafe: $1,000)
  
  Position Size = $20 / $1,000 = 0.02 BTC
  Position Value = 0.02 × $50,000 = $1,000
```

**Risk Seviyeleri:**

| Risk % | Trader Tipi | 10 Kayıp Sonrası |
|--------|-------------|------------------|
| **%0.1** | Ultra Konservatif | -%1 kayıp |
| **%0.5** | Konservatif | -%5 kayıp |
| **%1.0** | Orta (Önerilen) | -%10 kayıp |
| **%2.0** | Agresif | -%20 kayıp |
| **%5.0** | Çok Agresif | -%50 kayıp ⚠️ |

---

### **1.2 Max Leverage (1x - 50x)**

**Input:**
- **ID:** `#risk-max-leverage`
- **Tip:** Number Input
- **Min:** `1` (1x)
- **Max:** `50` (50x)
- **Step:** `1`
- **Varsayılan:** `10` (10x)

**Validasyon:**
```javascript
function validateLeverage() {
    const maxLeverage = parseInt(document.getElementById('risk-max-leverage').value);
    
    if (maxLeverage < 1 || maxLeverage > 50) {
        showToast('⚠️ Kaldıraç 1x ile 50x arasında olmalı!', 'warning');
        return false;
    }
    
    return true;
}
```

**Timeframe-Aware Kaldıraç Sınırlandırması:**

| Timeframe | Max Kaldıraç | Sebep |
|-----------|--------------|-------|
| **1m, 3m** | 10x | Yüksek gürültü (noise) + komisyon etkisi |
| **5m-30m** | 20x | Orta gürültü |
| **1h+** | 50x | Normal (düşük gürültü) |

**Dinamik Kaldıraç (ML Confidence Bazlı):**
```python
# core/risk/risk_engine.py
def calculate_dynamic_leverage(confidence_score, timeframe):
    if confidence_score < 0.50:
        return 1.0  # Düşük güven
    
    if timeframe in ["1m", "3m"]:
        max_leverage = 10  # Gürültü limiti
    elif timeframe in ["5m", "15m"]:
        max_leverage = 20
    else:
        max_leverage = 50
    
    # Power curve hesaplama
    raw_ratio = (confidence_score - 0.50) / 0.50
    boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))
    
    calculated = 1.0 + (boosted_ratio * (max_leverage - 1.0))
    final_leverage = int(round(min(max_leverage, calculated)))
    
    return final_leverage
```

---

### **1.3 Max Open Positions (1 - 20)**

**Input:**
- **ID:** `#risk-max-positions`
- **Min:** `1`
- **Max:** `20`
- **Varsayılan:** `5`

**Formül:**
```
Max Margin Per Trade = Balance / MaxPositions

Örnek:
  Balance: $10,000
  MaxPositions: 5
  
  Max Margin Per Trade = $10,000 / 5 = $2,000
```

---

### **1.4 Max Consecutive Losses (0 - 50)**

**Input:**
- **ID:** `#risk-max-losses`
- **Min:** `0` (Sınırsız)
- **Max:** `50`
- **Varsayılan:** `10`

**Kill Switch Mantığı:**
```python
# core/risk/risk_engine.py
def check_kill_switch(self):
    if not self.config.kill_switch_enabled:
        return False
    
    if self.config.max_consecutive_losses > 0 and \
       self.consecutive_losses >= self.config.max_consecutive_losses:
        logger.warning(f"🚨 KILL SWITCH: {self.consecutive_losses} ardışık kayıp")
        return True
    
    if self.daily_pnl <= -self.config.max_daily_loss:
        logger.critical(f"🚨 KILL SWITCH: Günlük kayıp {self.daily_pnl:.2%}")
        return True
    
    return False
```

---

## 2. GÜVENLİK (Mühendislik)

### **2.1 AES-128-CBC (Fernet) Şifreleme**

**API Anahtarları ASLA Düz Metin (Plaintext) Olarak Saklanmaz!**

**Şifreleme Mimarisi:**
```
┌─────────────────────────────────────────────────────────┐
│  .env Dosyası                                           │
├─────────────────────────────────────────────────────────┤
│  BINANCE_API_KEY = gAAAAABhZ... (Şifrelenmiş)          │
│  BINANCE_API_SECRET = gAAAAABhZ... (Şifrelenmiş)       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  .secret.key (AES-128-CBC Anahtarı)                     │
│  - 32-byte random key                                   │
│  - 0o600 izni (sadece owner okur/yazar)                 │
│  - cryptography.fernet kütüphanesi                      │
└─────────────────────────────────────────────────────────┘
```

**Kod Implementasyonu:**
```python
# core/security.py
from cryptography.fernet import Fernet
from pathlib import Path

class KeyManager:
    def __init__(self):
        self.key_file = Path(".secret.key")
        self.fernet = None
        self._load_or_create_key()
    
    def _load_or_create_key(self):
        """
        .secret.key dosyasından anahtar yükle veya yeni oluştur.
        0o600 izni ile koru (sadece owner okur/yazar).
        """
        if self.key_file.exists():
            # Mevcut anahtarı yükle
            self.key_file.chmod(0o600)  # İzinleri ayarla
            key = self.key_file.read_bytes()
            self.fernet = Fernet(key)
        else:
            # Yeni anahtar oluştur
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Sadece owner erişebilir
            self.fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """AES-128-CBC ile şifrele."""
        encrypted = self.fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """AES-128-CBC ile çöz."""
        decrypted = self.fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted.decode('utf-8')
```

**API Key Kaydetme:**
```python
# core/security.py
def save_api_keys(self, api_key: str, api_secret: str):
    """API anahtarlarını şifrele ve .env'e kaydet."""
    # Şifrele
    encrypted_key = self.encrypt(api_key)
    encrypted_secret = self.encrypt(api_secret)
    
    # .env dosyasını güncelle
    env_data = self._load_env()
    env_data['BINANCE_API_KEY'] = encrypted_key
    env_data['BINANCE_API_SECRET'] = encrypted_secret
    self._save_env(env_data)
```

**Dosya İzinleri:**
```bash
# Linux/Mac
chmod 600 .secret.key
# -rw------- 1 user user 44 Mar 17 12:00 .secret.key
# (Sadece dosya sahibi okur/yazar)

# Windows (PowerShell)
icacls .secret.key /inheritance:r /grant:r "%USERNAME%:R"
```

---

### **2.2 API Bağlantı Testi**

**Buton:** `🔄 Bağlantıyı Test Et`

**Endpoint:**
```http
GET /api/v1/config/api-keys/test
```

**Response:**
```json
{
    "status": "success",
    "message": "API bağlantısı başarılı",
    "account_type": "futures",
    "rate_limit": 2400
}
```

**Test Mantığı:**
```python
# api/routers/system.py
@router.get("/config/api-keys/test")
async def test_api_connection():
    try:
        # Binance API'ye basit bir istek
        account = await exchange.fetch_balance()
        
        return {
            "status": "success",
            "message": "API bağlantısı başarılı",
            "account_type": "futures",
            "rate_limit": 2400  # API key ile yüksek limit
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"API hatası: {e}")
```

---

## 3. KALMAN FİLTRESİ AYARLARI

### **3.1 Process Noise (Q)**

**Input:**
- **ID:** `#kalman-process-noise`
- **Min:** `0.0001`
- **Max:** `0.01`
- **Step:** `0.0001`
- **Varsayılan:** `0.001`

**Anlamı:**
- **Küçük değer (0.001):** Daha smooth (yumuşak) filtreleme
- **Büyük değer (0.01):** Daha hızlı tepki (daha fazla noise)

---

### **3.2 Measurement Noise (R)**

**Input:**
- **ID:** `#kalman-measurement-noise`
- **Min:** `0.01`
- **Max:** `1.0`
- **Step:** `0.01`
- **Varsayılan:** `0.1`

**Anlamı:**
- **Büyük değer (0.1):** Fiyat değişimlerine daha agresif tepki
- **Küçük değer (0.01):** Daha konservatif tahmin

---

## 4. MUM KAPANış KİLİDİ

### **4.1 Kontrol Aralığı (5-60 saniye)**

**Input:**
- **ID:** `#candle-lock-interval`
- **Min:** `5`
- **Max:** `60`
- **Step:** `5`
- **Varsayılan:** `5`

**Mantık:**
```
HTF botları (15m, 1h) için kritik:
  - Saniyede 100+ tick geliyor
  - Her tick'te hesaplama YAPILMAZ
  - Sadece mum kapandığında hesaplanır
  - CPU tasarrufu: %98
```

**Implementasyon:**
```python
# core/exchange.py
async def run_strategy_poller(self, symbol: str):
    last_candle_time = None
    
    while True:
        # Son mumu al
        df = await self.get_latest_candles(symbol, timeframe='1h', limit=100)
        current_candle_time = df.index[-1]
        
        # Sadece mum kapandığında hesapla
        if current_candle_time != last_candle_time:
            # Yeni mum kapandı → Hesapla
            strategy.generate_signal(df.iloc[-1])
            last_candle_time = current_candle_time
        else:
            # Mum hala açık → Bekle (CPU tasarrufu)
            await asyncio.sleep(1)
```

---

## 🚨 Sorun Giderme

### **Sorun 1: API Keys Kaydedilmiyor**

**Semptom:** "Şifreleme hatası" mesajı

**Çözüm:**
1. `.secret.key` dosyası var mı:
   ```bash
   ls -la .secret.key
   ```
2. İzinler doğru mu:
   ```bash
   chmod 600 .secret.key
   ```
3. `cryptography` kütüphanesi yüklü mü:
   ```bash
   pip install cryptography
   ```

---

### **Sorun 2: Risk Ayarları Uygulanmıyor**

**Semptom:** Ayarlar kaydediliyor ama bot uygulamıyor

**Çözüm:**
1. Bot yeniden başlatıldı mı:
   ```
   Bot → Durdur → Başlat
   ```
2. Config dosyası güncel mi:
   ```bash
   cat config.yaml | grep risk_management
   ```
3. Risk engine loglarını kontrol et:
   ```python
   logger.info(f"Risk config: {risk_engine.config}")
   ```

---

## 📚 İlgili Dokümanlar

- **Risk Engine:** `features/risk_engine.md`
- **Dynamic Position Sizing:** `concepts/dynamic_position_sizing.md`
- **Kalman Filter:** `concepts/kalman_filter.md`
- **Candle Lock:** `concepts/candle_lock.md`

---

*Bu doküman Sistem Ayarları v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `frontend/index.html` (tab-settings) dosyasını kontrol edin.*
