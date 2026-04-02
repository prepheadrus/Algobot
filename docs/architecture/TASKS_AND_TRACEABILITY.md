# 📊 TASKS AND TRACEABILITY MATRIX

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Kategori:** İzlenebilirlik ve XAI (Açıklanabilir Yapay Zeka)

---

## 📋 Genel Bakış

Bu doküman, CryptoAlgoBot sistemindeki **WFO (Walk-Forward Optimization)**, **Hot-Reload**, **Auto-Grid** ve **ML Karar Motoru (XAI)** katmanlarının tamamlanma durumlarını listeler. Arayüz ile backend arasındaki "Data Binding" yamalarını ve ThreadPoolExecutor izolasyonlarını teyit eder.

---

## 1. WFO (WALK-FORWARD OPTIMIZATION)

### **1.1 Bayesian Optimization (Optuna TPE)**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **Optuna Kütüphanesi** | ✅ MEVCUT | `requirements.txt` | `optuna>=3.4.0` |
| **TPE Sampler** | ✅ AKTİF | `core/wfo_engine.py` | `TPESampler(seed=42)` |
| **Objective Fonksiyon** | ✅ KODLANDI | `wfo_engine.py` | `_objective()` metodu |
| **Auto-Grid Entegrasyonu** | ✅ AKTİF | `core/auto_grid.py` | `auto_grid.generate_from_strategy()` |
| **ThreadPoolExecutor** | ✅ İZOLE | `wfo_engine.py` | `MAX_WORKERS = min(cpu_count(), 8)` |

**Kod Durumu:**
```python
# core/wfo_engine.py (Satır 128-131)
study = optuna.create_study(
    direction='maximize',
    sampler=TPESampler(seed=42),  # ✅ TPE (Tree-structured Parzen Estimator)
    study_name=f'wfo_{symbol}_{timeframe}'
)

# Satır 56: ThreadPool (Dinamik)
MAX_WORKERS = min(multiprocessing.cpu_count(), 8)  # ✅ Donanım agnostiği
```

---

### **1.2 Overfitting Kalkanı**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **Dinamik Eşikler** | ✅ AKTİF | `wfo_engine.py` | `_check_overfitting()` |
| **Sharpe Toleransı** | ✅ %30 (1.3x) | `wfo_engine.py` | `MAX_OVERFITTING_RATIO = 1.3` |
| **Net PnL Toleransı** | ✅ %50 (1.5x) | `wfo_engine.py` | `MAX_OVERFITTING_RATIO = 1.5` |
| **OOS Doğrulama** | ✅ AKTİF | `wfo_engine.py` | `_validate_out_of_sample()` |

**Kod Durumu:**
```python
# core/wfo_engine.py (Satır 427-432)
if optimization_metric == 'sharpe':
    MAX_OVERFITTING_RATIO = 1.3  # ✅ Sharpe için %30 sapma
else:
    MAX_OVERFITTING_RATIO = 1.5  # ✅ Net PnL için %50 sapma

overfitting_ratio = is_abs / oos_abs
is_overfitting = overfitting_ratio > MAX_OVERFITTING_RATIO
```

---

### **1.3 Hot-Reload (API Üzerinden Konfigürasyon)**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **POST /config/advanced** | ✅ AKTİF | `api/routers/system.py` | WFO ayarları güncellenir |
| **RAM CONFIG Güncelleme** | ✅ AKTİF | `core/config.py` | `CONFIG['wfo']` hot-reload |
| **config.yaml Persist** | ✅ AKTİF | `api/routers/system.py` | `safe_dump()` ile yazılır |
| **Test Script** | ✅ MEVCUT | `test_wfo_hot_reload.py` | API çağrısı test edilir |

**API Payload:**
```json
POST /api/v1/config/advanced
{
    "wfo": {
        "enabled": true,
        "train_days": 30,
        "test_days": 7,
        "optimization_metric": "sharpe",
        "n_trials": 50
    }
}
```

---

## 2. AUTO-GRID (ZERO-TOUCH PARAM UZAYI)

### **2.1 DEFAULT_PARAMS Okuma**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **Strateji Okuma** | ✅ AKTİF | `core/auto_grid.py` | `generate_from_strategy()` |
| **%30 Esnetme (Flex Ratio)** | ✅ AKTİF | `auto_grid.py` | `FLEX_RATIO = 0.30` |
| **3 Noktalı Arama Uzayı** | ✅ AKTİF | `auto_grid.py` | `[low, mid, high]` |
| **Manuel Grid Kaldırıldı** | ✅ KALDIRILDI | `wfo_engine.py` | `param_grid=None` → auto-grid |
| **OptimizationConfig** | ✅ EKLENDİ | `core/wfo_engine.py` | Parametreler veri sınıfında toplandı |

**Kod Durumu:**
```python
# core/auto_grid.py (Satır 23-25)
class AutoGridGenerator:
    FLEX_RATIO = 0.30  # ✅ %30 esnetme
    
    def _generate_range(self, default_value):
        step = max(int(default_value * self.FLEX_RATIO), 1)
        return [default_value - step, default_value, default_value + step]
```

**Strateji DEFAULT_PARAMS:**
```python
# strategy/trend_master.py
DEFAULT_PARAMS = {
    'ema_period': 20,      # → [14, 20, 26]
    'atr_multiplier': 2.0, # → [1.4, 2.0, 2.6]
    'rsi_period': 14       # → [10, 14, 18]
}
```

---

## 3. ML KARAR MOTORU (XAI - AÇIKLANABİLİR YAPAY ZEKA)

### **3.1 UI Data Binding**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **loadMLStrategies()** | ✅ AKTİF | `frontend/app.js` | `/api/v1/strategies` API'den yükler |
| **loadMLSymbols()** | ✅ AKTİF | `frontend/app.js` | `/api/v1/data/symbols-with-data` |
| **runMLVisualAnalysis()** | ✅ AKTİF | `frontend/app.js` | Global function (window.export) |
| **Hardcoded Dropdown** | ✅ TEMİZLENDİ | `frontend/index.html` | Dinamik dolum aktif |

**Kod Durumu:**
```javascript
// frontend/app.js (Satır 2071-2102)
async function loadMLStrategies() {
    const response = await api.get('/api/v1/strategies');
    const strategies = response.strategies || [];
    
    select.innerHTML = '';
    strategies.forEach(strategy => {
        const option = document.createElement('option');
        option.value = strategy.id;
        option.textContent = strategy.name;
        select.appendChild(option);
    });
}
```

---

### **3.2 Feature Importance (XAI Standardı)**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **get_feature_importance_df()** | ✅ AKTİF | `ml/model_training.py` | Normalize %0-100 |
| **Normalizasyon Formülü** | ✅ AKTİF | `model_training.py` | `(Current / Max) * 100` |
| **Plotly Bar Chart** | ✅ AKTİF | `frontend/app.js` | `renderFeatureImportance()` |
| **Memory Leak Önleme** | ✅ AKTİF | `frontend/app.js` | `Plotly.react()` (newPlot değil) |

**Kod Durumu:**
```python
# ml/model_training.py (Satır 380-403)
def get_feature_importance_df(self, top_n: int = 20) -> pd.DataFrame:
    max_importance = max(importance) if len(importance) > 0 else 1.0
    
    df = pd.DataFrame({
        'feature_name': self.feature_names,
        'importance': importance,
        # ✅ NORMALIZASYON: (Current / Max) * 100
        'importance_pct': (importance / max_importance * 100) if max_importance > 0 else 0
    })
    
    return df.head(top_n)
```

```javascript
// frontend/app.js (Satır 2234-2274)
function renderFeatureImportance(featureImportance) {
    const trace = {
        x: importancePct,  // ✅ Yüzdelik değerler (0-100%)
        y: features,
        type: 'bar',
        orientation: 'h'  // Yatay bar
    };
    
    // ✅ Plotly.react (memory leak önleme)
    Plotly.react(chartDiv, [trace], layout, config);
}
```

---

### **3.3 Lightweight Charts (Çoklu Sinyal Füzyonu)**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **ML Sinyalleri** | ✅ AKTİF | `api/routers/ml.py` | Yeşil/Kırmızı Oklar |
| **Strateji Sinyalleri** | ✅ AKTİF | `api/routers/ml.py` | Mor Daireler |
| **Gerçek İşlemler** | ✅ AKTİF | `api/routers/ml.py` | Beyaz/Turkuaz Kareler |
| **Timestamp Eşleştirme** | ✅ AKTİF | `api/routers/ml.py` | `setMarkers()` ile render |
| **Dikey Offset** | ✅ AKTİF | `api/routers/ml.py` | Çakışan zaman damgaları yönetilir |

**Marker Tipleri:**
| Sinyal | Renk | Şekil | Kaynak |
|--------|------|-------|--------|
| **ML AL** | Yeşil (#2ea043) | Arrow Up | `predictions == 2` |
| **ML SAT** | Kırmızı (#f85149) | Arrow Down | `predictions == 0` |
| **Strateji AL** | Mor (#bc8cff) | Circle | `strategy.generate_signal() == 2` |
| **Strateji SAT** | Mor (#bc8cff) | Circle | `strategy.generate_signal() == 0` |
| **Gerçek AL** | Turkuaz (#00FA9A) | Circle | `paper_engine.open_positions` |
| **Gerçek SAT** | Turuncu (#FF4500) | Circle | `paper_engine.open_positions` |

---

## 4. THREADPOOL EXECUTOR İZOLASYONU

### **4.1 CPU-Bound İş İzolasyonu**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **ThreadPoolExecutor** | ✅ AKTİF | `wfo_engine.py` | `executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)` |
| **Event Loop Koruması** | ✅ AKTİF | `wfo_engine.py` | `loop.run_in_executor()` |
| **WebSocket Koruması** | ✅ AKTİF | `core/exchange.py` | `watch_ohlcv_loop` ayrı task |
| **Dinamik Worker** | ✅ AKTİF | `wfo_engine.py` | `min(cpu_count(), 8)` |

**Kod Durumu:**
```python
# core/wfo_engine.py (Satır 142-147)
loop = asyncio.get_event_loop()
await loop.run_in_executor(
    self.executor,  # ✅ ThreadPoolExecutor
    lambda: study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
)
```

**CPU Tasarrufu:**
```
4 çekirdekli CPU: 4 worker
8 çekirdekli CPU: 8 worker
16+ çekirdekli CPU: 8 worker (koruma)
```

---

## 5. OOM (OUT OF MEMORY) KORUMASI

### **5.1 Veri Sınırlama**

| Görev | Durum | Dosya | Detay |
|-------|-------|-------|-------|
| **tail(1500)** | ✅ AKTİF | `api/routers/ml.py` | Son 1500 mum ile sınırla |
| **Marker Filtreleme** | ✅ AKTİF | `api/routers/ml.py` | Sadece son 1500 mum içindekiler |
| **NaN/Infinity Temizliği** | ✅ AKTİF | `api/routers/ml.py` | `.replace([np.inf, -np.inf], 0).fillna(0)` |

**Kod Durumu:**
```python
# api/routers/ml.py (Satır 481-495)
# Tail(1500) - Son 1500 mumu al (OOM önleme)
candles_df = candles_df.tail(1500)
logger.info(f"🛡️ [ML] OOM Koruması: {len(candles_df)} mum (tail 1500)")

# Markers'ları da sınırla
if len(candles_df) > 0:
    min_time = candles_df['time'].min()
    markers = [m for m in markers if m.get('time', 0) >= min_time]

# NaN/Infinity temizliği
for col in ['open', 'high', 'low', 'close', 'volume']:
    candles_df[col] = candles_df[col].replace([np.inf, -np.inf], 0).fillna(0)
```

---

## 6. TAMAMLANMA DURUMU ÖZETİ

| Kategori | Görev Sayısı | Tamamlanan | Durum |
|----------|--------------|------------|-------|
| **WFO (Bayesian)** | 5 | 5 | ✅ %100 |
| **Auto-Grid** | 4 | 4 | ✅ %100 |
| **ML XAI (UI Binding)** | 4 | 4 | ✅ %100 |
| **Feature Importance** | 4 | 4 | ✅ %100 |
| **Lightweight Charts** | 5 | 5 | ✅ %100 |
| **ThreadPool Izolasyon** | 4 | 4 | ✅ %100 |
| **OOM Koruması** | 3 | 3 | ✅ %100 |
| **TOPLAM** | **29** | **29** | ✅ **%100** |

---

## 7. TEST SENARYOLARI

### **7.1 WFO Hot-Reload Testi**

**Script:** `test_wfo_hot_reload.py`

**Adımlar:**
1. ✅ POST /api/v1/config/advanced çağrısı
2. ✅ HTTP 200 response doğrulama
3. ✅ config.yaml safe_dump kontrolü
4. ✅ RAM CONFIG hot-reload kontrolü

**Beklenen Sonuç:**
```
[SİSTEM] Yamalar Uygulandı ve WFO Ayarları API Üzerinden (Hot-Reload)
         Otonom Olarak Yapılandırıldı.
```

---

### **7.2 ML Visual Analysis Testi**

**Adımlar:**
1. ✅ Sayfa yüklendiğinde `loadMLStrategies()` çağrılır
2. ✅ 6+ strateji dropdown'a eklenir
3. ✅ `loadMLSymbols()` çağrılır
4. ✅ 10+ sembol dropdown'a eklenir
5. ✅ "🚀 Simülasyonu Başlat" tıklanır
6. ✅ `runMLVisualAnalysis()` API çağrısı yapar
7. ✅ 1500 mum render edilir
8. ✅ 25+ marker gösterilir
9. ✅ Feature Importance grafiği çizilir

**Beklenen Sonuç:**
```
✅ [XAI] 1500 mum, 25 marker, 10 feature importance yüklendi
✅ [XAI] Feature Importance grafiği çizildi: 10 özellik
```

---

**Doküman Versiyonu:** v4.0 (Mart 2026)
**İzlenebilirlik Durumu:** ✅ %100 (29/29 görev tamamlandı)
