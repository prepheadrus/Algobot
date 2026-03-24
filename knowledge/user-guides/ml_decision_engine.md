# 🧠 ML Karar Motoru (ML Decision Engine)

**Versiyon:** v4.0
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-ml)

---

## 🎯 Genel Bakış

ML Karar Motoru, XGBoost + Random Forest ensemble modelini Triple Barrier Method ile eğitmek ve canlı tahmin yapmak için kullanılan arayüzdür. Model, strateji sinyallerini onaylamak ve dinamik kaldıraç için güven skoru üretmek için kullanılır.

---

## 📁 Konum

```
Sol Menü → 🧠 ML Karar Motoru
```

---

## 🏗️ Mimari

```
┌──────────────┐
│  Parquet     │
│  Data Lake   │
└──────┬───────┘
       │ OHLCV Data
       ▼
┌──────────────┐
│  Feature     │
│  Engineering │
│  (40+ feat.) │
└──────┬───────┘
       │ Features + Labels
       ▼
┌──────────────┐
│  XGBoost +   │
│  RF Ensemble │
└──────┬───────┘
       │ Model (.json)
       ▼
┌──────────────┐
│  Inference   │
│  (Live)      │
└──────┬───────┘
       │ Confidence Score
       ▼
┌──────────────┐
│  Confluence  │
│  (Signal)    │
└──────────────┘
```

---

## 🧩 Bileşenler

### **1. ML Model Eğitimi Paneli**

#### **🧠 Başlık ve Açıklama**

**Başlık:**
```
🧠 ML Model Eğitimi
```

**Açıklama:**
```
XGBoost modelinizi Triple Barrier Method ile eğitin. 
Model, strateji sinyallerini onaylamak ve dinamik kaldıraç 
için güven skoru üretmek için kullanılacaktır.
```

---

#### **Sembol Seçimi**

**Input:**
- **ID:** `#ml-train-symbol`
- **Class:** `strategy-select symbol-select`
- **Tip:** Select Dropdown
- **Event:** `onchange="validateMumCount()"`
- **Dinamik Yükleme:** `loadSymbolsForML()` fonksiyonu ile

**Event Handler:**
```javascript
// frontend/app.js
async function loadSymbolsForML() {
    const select = document.getElementById('ml-train-symbol');
    
    try {
        const symbols = await api.get('/api/v1/ml/symbols');
        
        select.innerHTML = symbols.map(s => 
            `<option value="${s.symbol}">${s.symbol}</option>`
        ).join('');
        
        validateMumCount(); // Validate after load
    } catch (error) {
        showToast('❌ Sembol yükleme hatası: ' + error.message, 'error');
    }
}
```

---

#### **Zaman Dilimi Seçimi**

**Input:**
- **ID:** `#ml-train-timeframe`
- **Class:** `timeframe-select`
- **Tip:** Select Dropdown
- **Varsayılan:** `1h`
- **Event:** `onchange="validateMumCount()"`

**Seçenekler:**
```
1m, 3m, 5m, 10m, 15m, 20m, 30m, 45m
1h (selected), 2h, 3h, 4h, 6h, 8h, 12h
1d
```

---

#### **Mum Sayısı**

**Input:**
- **ID:** `#ml-train-limit`
- **Tip:** Number Input
- **Varsayılan:** `5000`
- **Min:** `100`
- **Step:** `100`
- **Event:** `onchange="validateMumCount()" oninput="validateMumCount()"`

**DB Mum Sayısı Göstergesi:**
- **ID:** `#ml-db-count`
- **Format:** `(DB: 15000 mum)`
- **Renk:** `var(--neon-blue)`

**Uyarı Mesajı:**
- **ID:** `#ml-limit-warning`
- **Görünürlük:** `display: none` (varsayılan)
- **Mesaj:** `⚠️ DB'de bu sayıdan az mum var!`
- **Renk:** `var(--neon-red)`

**Validasyon Mantığı:**
```javascript
// frontend/app.js
function validateMumCount() {
    const symbol = document.getElementById('ml-train-symbol').value;
    const timeframe = document.getElementById('ml-train-timeframe').value;
    const limitInput = document.getElementById('ml-train-limit');
    const warningEl = document.getElementById('ml-limit-warning');
    const dbCountEl = document.getElementById('ml-db-count');
    
    // Get DB count
    const dbCount = getDbCount(symbol, timeframe); // From store
    
    dbCountEl.textContent = `(DB: ${dbCount} mum)`;
    
    if (parseInt(limitInput.value) > dbCount) {
        warningEl.style.display = 'block';
        limitInput.style.borderColor = 'var(--neon-red)';
    } else {
        warningEl.style.display = 'none';
        limitInput.style.borderColor = 'rgba(255,255,255,0.1)';
    }
}
```

---

#### **TP (Take Profit) Çarpan**

**Input:**
- **ID:** `#ml-train-tp`
- **Tip:** Number Input
- **Varsayılan:** `2.0`
- **Min:** `1.0`
- **Max:** `5.0`
- **Step:** `0.5`
- **Açıklama:** Triple Barrier Method kar-al çarpanı

---

#### **SL (Stop Loss) Çarpan**

**Input:**
- **ID:** `#ml-train-sl`
- **Tip:** Number Input
- **Varsayılan:** `2.0`
- **Min:** `1.0`
- **Max:** `5.0`
- **Step:** `0.5`
- **Açıklama:** Triple Barrier Method zarar-kes çarpanı

---

#### **🚀 Modeli Eğit Butonu**

**Buton:**
- **Onclick:** `startMLTraining()`
- **Class:** `btn btn-primary`
- **Stil:** `linear-gradient(135deg, var(--neon-blue), #6366f1)`
- **Etiket:** `🚀 Modeli Eğit`

**Event Handler:**
```javascript
// frontend/app.js
async function startMLTraining() {
    const symbol = document.getElementById('ml-train-symbol').value;
    const timeframe = document.getElementById('ml-train-timeframe').value;
    const limit = parseInt(document.getElementById('ml-train-limit').value);
    const tp_multiplier = parseFloat(document.getElementById('ml-train-tp').value);
    const sl_multiplier = parseFloat(document.getElementById('ml-train-sl').value);
    
    // Validation
    if (!symbol) {
        showToast('⚠️ Lütfen sembol seçin!', 'warning');
        return;
    }
    
    if (limit < 100 || limit > 50000) {
        showToast('⚠️ Mum sayısı 100-50000 arası olmalı!', 'warning');
        return;
    }
    
    // Start training
    try {
        const response = await api.post('/api/v1/ml/train', {
            symbol: symbol,
            timeframe: timeframe,
            limit: limit,
            tp_multiplier: tp_multiplier,
            sl_multiplier: sl_multiplier
        });
        
        showToast('✅ ML model eğitimi başlatıldı: ' + symbol, 'success');
        
        // Show progress
        document.getElementById('ml-training-progress').style.display = 'block';
        startMLProgressPolling(response.task_id);
    } catch (error) {
        showToast('❌ ML eğitim hatası: ' + error.message, 'error');
    }
}
```

---

### **2. İlerleme Çubuğu (Progress Bar)**

**Container:**
- **ID:** `#ml-training-progress`
- **Varsayılan:** `display: none`
- **Görünürlük:** Eğitim başladığında `block`

**Progress Bar:**
- **ID:** `#ml-progress-bar`
- **Tip:** Div (width animasyonu)
- **Varsayılan Width:** `0%`
- **Geçiş:** `transition: width 0.3s ease`
- **Renk:** `linear-gradient(90deg, var(--neon-blue), #6366f1)`

**HTML Yapısı:**
```html
<div id="ml-training-progress" style="display: none; margin-top: 15px;">
    <div style="background: rgba(255,255,255,0.1); border-radius: 10px; 
                height: 20px; overflow: hidden; margin-bottom: 10px;">
        <div id="ml-progress-bar" 
             style="background: linear-gradient(90deg, var(--neon-blue), #6366f1); 
                    height: 100%; width: 0%; transition: width 0.3s ease;">
        </div>
    </div>
    <div id="ml-progress-text" style="text-align: center; 
         color: var(--text-muted); font-size: 0.8rem;">
        Model eğitiliyor... %0
    </div>
</div>
```

**Polling Mantığı:**
```javascript
// frontend/app.js
function startMLProgressPolling(taskId) {
    const pollInterval = setInterval(async () => {
        const status = await api.get(`/api/v1/ml/status?task_id=${taskId}`);
        
        const progressBar = document.getElementById('ml-progress-bar');
        const progressText = document.getElementById('ml-progress-text');
        
        if (progressBar && progressText) {
            progressBar.style.width = `${status.progress}%`;
            progressText.textContent = `Model eğitiliyor... %${status.progress}`;
            
            if (status.status === 'completed') {
                clearInterval(pollInterval);
                progressText.textContent = '✅ Eğitim tamamlandı!';
                progressText.style.color = 'var(--neon-green)';
                
                // Update model info
                updateModelInfo(status.model_path, status.metrics);
            } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                progressText.textContent = '❌ Eğitim başarısız!';
                progressText.style.color = 'var(--neon-red)';
            }
        }
    }, 2000); // Poll every 2 seconds
}
```

---

### **3. Model Bilgisi (Eğitim Sonrası)**

#### **Model Yolu**
- **ID:** `#ml-model-path`
- **Format:** `artifacts/models/xgb_model_btcusdtusdt_1h.json`
- **Görünürlük:** Eğitim tamamlandığında görünür

#### **Eğitim Metrikleri**

| Metrik | ID | Format | Açıklama |
|--------|----|--------|----------|
| **Accuracy** | `#ml-metric-accuracy` | `0.00` | Doğruluk oranı |
| **Precision** | `#ml-metric-precision` | `0.00` | Kesinlik |
| **Recall** | `#ml-metric-recall` | `0.00` | Duyarlılık |
| **F1-Score** | `#ml-metric-f1` | `0.00` | Harmonik ortalama |

---

### **4. Eğitim Geçmişi**

#### **📋 Geçmiş Tablosu**

| Kolon | ID | Açıklama |
|-------|----|----------|
| **Sembol** | `.history-symbol` | Eğitilen sembol |
| **Timeframe** | `.history-timeframe` | Zaman dilimi |
| **Tarih** | `.history-date` | Eğitim tarihi |
| **Accuracy** | `.history-accuracy` | Model doğruluğu |
| **Durum** | `.history-status` | `✅ Aktif`, `⏸️ Eski` |
| **Aksiyon** | `.history-actions` | `🔄 Yükle`, `🗑️ Sil` |

#### **Geçmiş Yükleme**
```javascript
// frontend/app.js
async function loadMLTrainingHistory() {
    const tbody = document.getElementById('ml-history-body');
    
    try {
        const history = await api.get('/api/v1/ml/training-history');
        
        tbody.innerHTML = history.map(item => `
            <tr>
                <td>${item.symbol}</td>
                <td>${item.timeframe}</td>
                <td>${item.date}</td>
                <td>${(item.accuracy * 100).toFixed(2)}%</td>
                <td>${item.status === 'active' ? '✅ Aktif' : '⏸️ Eski'}</td>
                <td>
                    <button onclick="loadMLModel('${item.model_path}')" 
                            class="btn-icon" title="Yükle">🔄</button>
                    <button onclick="deleteMLModel('${item.model_path}')" 
                            class="btn-icon" title="Sil">🗑️</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('❌ ML geçmişi yükleme hatası:', error);
    }
}
```

---

## 🔄 ML Eğitim İş Akışı

### **Adım 1: Sembol ve Timeframe Seçimi**
```
1. "Sembol" dropdown'dan sembol seç (örn: BTC/USDT:USDT)
2. "Zaman Dilimi" dropdown'dan timeframe seç (örn: 1h)
3. Mum sayısı otomatik doğrulanır
```

### **Adım 2: Parametre Girişi**
```
1. Mum Sayısı: 5000 (DB'de yeterli mum olmalı)
2. TP Çarpan: 2.0 (Triple Barrier kar-al)
3. SL Çarpan: 2.0 (Triple Barrier zarar-kes)
```

### **Adım 3: Eğitimi Başlat**
```
1. "🚀 Modeli Eğit" butonuna tıkla
2. API request gönderilir:
   POST /api/v1/ml/train
3. Progress bar görünür hale gelir
```

### **Adım 4: İlerleme İzleme**
```
- Her 2 saniyede polling
- Progress bar 0% → 100%
- Durum: "Model eğitiliyor..." → "✅ Eğitim tamamlandı!"
```

### **Adım 5: Model Yükleme**
```
Eğitim tamamlandıktan sonra:
1. Model otomatik yüklenir
2. Strateji sinyallerini onaylamak için kullanılır
3. Güven skoru (confidence) üretilir
```

---

## 📊 Triple Barrier Method

### **Teorik Açıklama**

Triple Barrier Method, Marcos Lopez de Prado tarafından geliştirilen etiketleme yöntemidir. Her veri noktası için üç bariyer tanımlanır:

**1. Kar-Al Bariyeri (Profit-Take):**
```
pt_barrier = entry_price + (tp_multiplier × volatility)
```

**2. Zarar-Kes Bariyeri (Stop-Loss):**
```
sl_barrier = entry_price - (sl_multiplier × volatility)
```

**3. Zaman Limiti Bariyeri:**
```
time_limit = t + T (örn: T = 5 mum)
```

### **Etiket Atama Mantığı**

| Durum | Etiket | Anlam |
|-------|--------|-------|
| **pt_barrier önce dokunuldu** | `2` | LONG (Kar) |
| **sl_barrier önce dokunuldu** | `0` | SHORT (Zarar) |
| **time_limit doldu** | `1` | NEUTRAL (Yatay) |

---

## 🎯 Güven Skoru (Confidence Score)

### **Hesaplama**

```python
# ml/inference.py
ensemble_proba = (xgb_proba + rf_proba) / 2
confidence = max(ensemble_proba[0])  # En yüksek olasılık
```

### **Dinamik Kaldıraç Eşleme**

| Confidence | Kaldıraç | Aksiyon |
|------------|----------|---------|
| **< 50%** | 1x (base) | İşlem açma |
| **50-65%** | 2-3x | Düşük risk |
| **65-80%** | 3-5x | Orta risk |
| **> 80%** | 5-10x | Yüksek risk |

### **Timeframe-Aware Limit**

```python
# core/risk/risk_engine.py
if timeframe in ["1m", "3m"]:
    max_leverage = 10  # Yüksek gürültü
elif timeframe in ["5m", "15m"]:
    max_leverage = 20  # Orta gürültü
else:
    max_leverage = config.max_leverage  # Normal
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Model Eğitilmiyor**

**Semptom:** Butona tıklanınca reaksiyon yok

**Çözüm:**
1. Console'da hata kontrolü
2. Sembol seçildi mi
3. Mum sayısı yeterli mi:
   ```javascript
   console.log(document.getElementById('ml-db-count').textContent);
   ```

---

### **Sorun 2: Progress Bar Sabit**

**Semptom:** %0'da ilerlemiyor

**Çözüm:**
1. API endpoint çalışıyor mu:
   ```bash
   curl http://localhost:8000/api/v1/ml/status?task_id=123
   ```
2. Event Bus çalışıyor mu
3. Manuel polling başlat:
   ```javascript
   startMLProgressPolling(task_id);
   ```

---

### **Sorun 3: Model Yüklenmiyor**

**Semptom:** Eğitim tamamlandı ama model kullanılmıyor

**Çözüm:**
1. Model dosyası var mı:
   ```bash
   ls artifacts/models/xgb_model_*.json
   ```
2. ML inference yüklendi mi:
   ```python
   from ml.inference import MLInference
   inference = MLInference(symbol, timeframe)
   inference.load_model()
   ```
3. Confidence threshold yeterli mi (≥65%)

---

## 📚 İlgili Dokümanlar

- **ML Integration:** `features/ml_integration.md`
- **Triple Barrier Method:** `concepts/triple_barrier_method.md`
- **Dinamik Kaldıraç:** `concepts/dynamic_leverage.md`

---

*Bu doküman ML Karar Motoru v4.0 versiyonunu açıklar.*
*Güncellemeler için `frontend/index.html` (tab-ml) ve `frontend/app.js` dosyalarını kontrol edin.*
