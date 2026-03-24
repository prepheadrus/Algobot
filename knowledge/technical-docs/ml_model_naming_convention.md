# ML Model İsimlendirme ve Yükleme Konvansiyonu

## Genel Bakış

ML model dosyalarının tutarlı isimlendirme ve yükleme standartlarını belirler. XGBoost + Random Forest Ensemble modellerinin doğru dosya yollarıyla kaydedilmesini ve yüklenmesini sağlar.

## Sorun (Önceki Durum)

### Dosya Yolu Uyuşmazlığı (Path Mismatch)

**Eğitim (Training) Tarafı:**
- Sadece XGBoost `.json` dosyası kaydediliyordu
- Random Forest `.joblib` ve Metadata `.json` dosyaları kaydedilmiyordu

**Yükleme (Inference) Tarafı:**
- `ModelTrainer.load_model()` 3 dosyayı da arıyordu
- Dosyalar bulunamadığı için warning logları çıkıyordu

**Terminal Hataları:**
```
⚠️ Random Forest model bulunamadı: artifacts/models/xgb_model_dogeusdtusdt_1m_rf.joblib
⚠️ Metadata dosyası bulunamadı: artifacts/models/xgb_model_dogeusdtusdt_1m_metadata.json
🧠 [ML] Model belleğe yüklendi: artifacts/models/xgb_model_dogeusdtusdt_1m.json
```

---

## Çözüm: Merkezi Path Generator

### `get_model_paths()` Fonksiyonu

**Dosya:** `ml/model_training.py`

```python
def get_model_paths(symbol: str, timeframe: str, base_dir: str = "artifacts/models") -> dict:
    """
    ML model dosyaları için standartlaştırılmış dosya yollarını üretir.
    
    Args:
        symbol: Sembol (örn: 'DOGE/USDT:USDT', 'BTC/USDT')
        timeframe: Zaman dilimi (örn: '1m', '1h')
        base_dir: Model dosyalarının kaydedileceği temel dizin
    
    Returns:
        dict: 3 dosya yolunu içeren dictionary
            - xgboost_path: XGBoost model dosyası (.json)
            - rf_path: Random Forest model dosyası (.joblib)
            - metadata_path: Metadata dosyası (.json)
    """
    symbol_clean = _clean_symbol(symbol)
    
    return {
        'xgboost_path': f"{base_dir}/xgb_model_{symbol_clean}_{timeframe}.json",
        'rf_path': f"{base_dir}/xgb_model_{symbol_clean}_{timeframe}_rf.joblib",
        'metadata_path': f"{base_dir}/xgb_model_{symbol_clean}_{timeframe}_metadata.json"
    }
```

### `_clean_symbol()` Helper

```python
def _clean_symbol(symbol: str) -> str:
    """
    Sembol isimlerini standart formata temizler.
    
    Örnekler:
        'DOGE/USDT:USDT' → 'dogeusdtusdt'
        'BTC/USDT' → 'btcusdt'
        'ETH/USDT:USDT' → 'ethusdtusdt'
    """
    return symbol.replace('/', '').replace(':', '').replace('-', '').lower()
```

---

## Dosya İsimlendirme Standardı

### Format

```
artifacts/models/xgb_model_{symbol_clean}_{timeframe}.{ext}
```

### Dosya Türleri

| Dosya | Uzantı | Örnek |
|-------|--------|-------|
| **XGBoost** | `.json` | `xgb_model_dogeusdtusdt_1m.json` |
| **Random Forest** | `.joblib` | `xgb_model_dogeusdtusdt_1m_rf.joblib` |
| **Metadata** | `.json` | `xgb_model_dogeusdtusdt_1m_metadata.json` |

### Sembol Temizleme Örnekleri

| Orijinal | Temizlenmiş |
|----------|-------------|
| `DOGE/USDT:USDT` | `dogeusdtusdt` |
| `BTC/USDT` | `btcusdt` |
| `ETH/USDT:USDT` | `ethusdtusdt` |
| `SOL/USDT:USDT` | `solusdtusdt` |

---

## Mimari

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Eğitim Başlatıldı (API)                                  │
│    - request.symbol = 'DOGE/USDT:USDT'                      │
│    - request.timeframe = '1m'                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. get_model_paths() Çağrıldı                               │
│    - symbol_clean = 'dogeusdtusdt'                          │
│    - 3 dosya yolu üretildi                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Ensemble Modeller Kaydedildi                             │
│    - trainer.save_model(xgboost_path, timeframe)            │
│    - XGBoost → .json                                        │
│    - Random Forest → .joblib                                │
│    - Metadata → .json                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Yükleme (Inference)                                      │
│    - get_model_paths() aynı yolları döner                   │
│    - 3 dosya da exists() ile kontrol edilir                 │
│    - Ensemble tam olarak yüklenir                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Kullanım

### 1. Eğitim (Training) Tarafı

**Dosya:** `api/services/ml_service.py`

```python
from ml.model_training import get_model_paths

# Model yollarını al
model_paths = get_model_paths(request.symbol, request.timeframe)

# Ensemble modelleri kaydet
trainer.save_model(
    model_path=model_paths['xgboost_path'],
    timeframe=request.timeframe
)

# Log
logger.info(f"💾 [ML] Ensemble modeller kaydedildi:")
logger.info(f"   XGBoost: {model_paths['xgboost_path']}")
logger.info(f"   RF:      {model_paths['rf_path']}")
logger.info(f"   Meta:    {model_paths['metadata_path']}")
```

### 2. Yükleme (Inference) Tarafı

**Dosya:** `core/paper.py`

```python
from ml.model_training import get_model_paths

# Model yollarını al
model_paths = get_model_paths(symbol, timeframe)
model_path = model_paths['xgboost_path']

# XGBoost modelini kontrol et
if not os.path.exists(model_path):
    logger.debug(f"🧠 [ML] XGBoost model bulunamadı: {model_path}")
    return None

# Modeli yükle
trainer = ModelTrainer()
trainer.load_model(model_path)
```

### 3. Model Kontrol (API)

**Dosya:** `api/services/ml_service.py`

```python
from ml.model_training import get_model_paths

def check_model(self, symbol: str, timeframe: str):
    model_paths = get_model_paths(symbol, timeframe)
    
    xgb_exists = os.path.exists(model_paths['xgboost_path'])
    rf_exists = os.path.exists(model_paths['rf_path'])
    metadata_exists = os.path.exists(model_paths['metadata_path'])
    
    return {
        "status": "success",
        "model_exists": xgb_exists,
        "ensemble_status": {
            "xgboost": xgb_exists,
            "random_forest": rf_exists,
            "metadata": metadata_exists,
            "full_ensemble": xgb_exists and rf_exists and metadata_exists
        }
    }
```

---

## ModelTrainer.save_model()

**Dosya:** `ml/model_training.py`

```python
def save_model(self, model_path: str, timeframe: str) -> str:
    """
    Ensemble modelleri diske kaydeder.
    
    Args:
        model_path: XGBoost model dosya yolu
        timeframe: Eğitim timeframe'i (metadata için)
    """
    # 1. XGBoost modelini kaydet (JSON formatı)
    self.xgb_model.save_model(model_path)
    
    # 2. Random Forest modelini kaydet (Joblib/Pickle)
    import joblib
    rf_model_path = model_path.replace('.json', '_rf.joblib')
    joblib.dump(self.rf_model, rf_model_path)
    
    # 3. Metadata'yi kaydet
    metadata_path = model_path.replace('.json', '_metadata.json')
    metadata = {
        'feature_names': self.feature_names,
        'training_metrics': {...},
        'class_mapping': self.class_mapping,
        'hyperparameters': {...},
        'model_paths': {
            'xgb': model_path,
            'rf': rf_model_path
        },
        'trained_timeframe': timeframe,
        'trained_at': datetime.now().isoformat()
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    return model_path
```

---

## ModelTrainer.load_model()

**Dosya:** `ml/model_training.py`

```python
def load_model(self, model_path: str):
    """
    Diskten ensemble modelleri yükler.
    
    Args:
        model_path: XGBoost model dosya yolu
    """
    # 1. XGBoost modelini yükle
    self.xgb_model.load_model(model_path)
    
    # 2. Random Forest modelini yükle
    import joblib
    rf_model_path = model_path.replace('.json', '_rf.joblib')
    if os.path.exists(rf_model_path):
        self.rf_model = joblib.load(rf_model_path)
        logger.info(f"✅ Random Forest model yüklendi: {rf_model_path}")
    else:
        logger.warning(f"⚠️ Random Forest model bulunamadı: {rf_model_path}")
    
    # 3. Metadata'yi yükle
    metadata_path = model_path.replace('.json', '_metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.feature_names = metadata.get('feature_names')
        self.class_mapping = metadata.get('class_mapping')
        self.training_metrics = metadata.get('training_metrics')
        
        logger.info(f"✅ Metadata yüklendi: {metadata_path}")
    else:
        logger.warning(f"⚠️ Metadata dosyası bulunamadı: {metadata_path}")
    
    return self
```

---

## Metadata Yapısı

**Dosya:** `xgb_model_{symbol}_{timeframe}_metadata.json`

```json
{
  "feature_names": ["RSI_14", "MACD_12_26_9", "ATR_14", ...],
  "training_metrics": {
    "accuracy": 0.7234,
    "precision": 0.7156,
    "recall": 0.6892,
    "f1": 0.7021,
    "xgb_accuracy": 0.7123,
    "rf_accuracy": 0.6987,
    "ensemble_accuracy": 0.7234
  },
  "class_mapping": {
    "0": "SHORT",
    "1": "LONG",
    "2": "NEUTRAL"
  },
  "hyperparameters": {
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.1,
    "rf_n_estimators": 200,
    "rf_max_depth": 10
  },
  "model_paths": {
    "xgb": "artifacts/models/xgb_model_dogeusdtusdt_1m.json",
    "rf": "artifacts/models/xgb_model_dogeusdtusdt_1m_rf.joblib"
  },
  "trained_timeframe": "1m",
  "trained_at": "2026-03-13T20:07:45.123456"
}
```

---

## Değişiklikler

### Güncellenen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `ml/model_training.py` | `get_model_paths()` ve `_clean_symbol()` eklendi |
| `api/services/ml_service.py` | `get_model_paths()` kullanıyor |
| `core/paper.py` | `get_model_paths()` kullanıyor |

### Kaldırılan Hardcoded Kodlar

**Önceki:**
```python
# ❌ Hardcoded symbol cleaning
symbol_clean = request.symbol.replace('/', '').replace(':', '').replace('-', '').lower()
model_path = f"artifacts/models/xgb_model_{symbol_clean}_{request.timeframe}.json"
```

**Yeni:**
```python
# ✅ Merkezi path generator
from ml.model_training import get_model_paths
model_paths = get_model_paths(request.symbol, request.timeframe)
```

---

## Log Örnekleri

### Eğitim Başarılı

```
🧠 [ML] Eğitim başlatılıyor: DOGE/USDT:USDT (1m) - 1000 mum
📊 [ML] Veri çekiliyor: DOGE/USDT:USDT, 1m, limit=1000
✅ [ML] 1000 mum çekildi ve DataFrame'e çevrildi
📊 [ML] ML pipeline başlatılıyor...
✅ [ML] ML pipeline tamamlandı: 800 eğitim, 200 test örnek
📊 XGBoost eğitiliyor...
✅ XGBoost eğitimi tamamlandı.
🌲 Random Forest eğitiliyor...
✅ Random Forest eğitimi tamamlandı.
🔗 Ensemble tahminleri hesaplanıyor...
============================================================
EĞİTİM SONUÇLARI
============================================================
Accuracy:  0.7234
Precision: 0.7156
Recall:    0.6892
F1-Score:  0.7021
============================================================
💾 [ML] Ensemble modeller kaydedildi:
   XGBoost: artifacts/models/xgb_model_dogeusdtusdt_1m.json
   RF:      artifacts/models/xgb_model_dogeusdtusdt_1m_rf.joblib
   Meta:    artifacts/models/xgb_model_dogeusdtusdt_1m_metadata.json
🎉 [ML] Eğitim başarıyla tamamlandı: DOGE/USDT:USDT
```

### Yükleme Başarılı

```
🧠 [ML] Model belleğe yüklendi: artifacts/models/xgb_model_dogeusdtusdt_1m.json
✅ Random Forest model yüklendi: artifacts/models/xgb_model_dogeusdtusdt_1m_rf.joblib
✅ Metadata yüklendi: artifacts/models/xgb_model_dogeusdtusdt_1m_metadata.json
📊 Özellik sayısı: 45
```

### Yükleme Hatası (Eksik Dosyalar)

```
⚠️ Random Forest model bulunamadı: artifacts/models/xgb_model_dogeusdtusdt_1m_rf.joblib
⚠️ Metadata dosyası bulunamadı: artifacts/models/xgb_model_dogeusdtusdt_1m_metadata.json
🧠 [ML] Model belleğe yüklendi: artifacts/models/xgb_model_dogeusdtusdt_1m.json
```

---

## Sorun Giderme

### Random Forest Bulunamadı

**Hata:**
```
⚠️ Random Forest model bulunamadı: artifacts/models/xgb_model_btcusdt_1m_rf.joblib
```

**Sebep:** Eğitim API'si sadece XGBoost'u kaydediyor.

**Çözüm:** `api/services/ml_service.py` içinde `trainer.save_model()` kullanın:
```python
# ❌ Eski (sadece XGBoost)
trainer.xgb_model.save_model(model_path)

# ✅ Yeni (Ensemble)
trainer.save_model(model_path=model_paths['xgboost_path'], timeframe=request.timeframe)
```

### Metadata Timeframe Uyuşmazlığı

**Hata:**
```
⚠️ TIMEFRAME UYUMSUZLUĞU! Model 15m için eğitilmiş, ama bot 1h çalışıyor!
```

**Çözüm:** Doğru timeframe seçin veya modeli yeniden eğitin.

### Model Dosyası Yok

**Hata:**
```
❌ ML model dosyası bulunamadı: artifacts/models/xgb_model_btcusdt_1m.json
```

**Çözüm:** Dashboard'dan ML Model Eğitimi yapın.

---

## Test

### Birim Testi

```python
from ml.model_training import get_model_paths, _clean_symbol

# Sembol temizleme testi
assert _clean_symbol('DOGE/USDT:USDT') == 'dogeusdtusdt'
assert _clean_symbol('BTC/USDT') == 'btcusdt'
assert _clean_symbol('ETH/USDT:USDT') == 'ethusdtusdt'

# Path generator testi
paths = get_model_paths('DOGE/USDT:USDT', '1m')
assert paths['xgboost_path'] == 'artifacts/models/xgb_model_dogeusdtusdt_1m.json'
assert paths['rf_path'] == 'artifacts/models/xgb_model_dogeusdtusdt_1m_rf.joblib'
assert paths['metadata_path'] == 'artifacts/models/xgb_model_dogeusdtusdt_1m_metadata.json'
```

---

## İlgili Dökümanlar

- [ML Model Training](./ml_model_training.md)
- [Walk-Forward Optimization](./walk_forward_optimization.md)
- [Bayesian Optimization](./bayesian_optimization.md)
- [Auto-Grid Generator](./auto_grid_generator.md)

---

**Son Güncelleme:** 2026-03-13
**Yazar:** CryptoAlgoBot Team
**Durum:** ✅ Production Ready
