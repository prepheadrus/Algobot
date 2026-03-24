# 💾 Veri Laboratuvarı (Data Laboratory)

**Versiyon:** v4.0
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-data)

---

## 🎯 Genel Bakış

Veri Laboratuvarı, Binance üzerinden OHLCV (Open-High-Low-Close-Volume) verisi indirme, Parquet Data Lake'e kaydetme ve indirme görevlerini yönetme panelidir.

---

## 📁 Konum

```
Sol Menü → 💾 Veri Laboratuvarı
```

---

## 🏗️ Mimari

```
┌──────────────┐
│   Binance    │
│    REST API  │
└──────┬───────┘
       │ OHLCV Data
       ▼
┌──────────────┐
│  Downloader  │
│  (Async)     │
└──────┬───────┘
       │ Parquet Format
       ▼
┌──────────────┐
│  Data Lake   │
│  (MTF-Daily) │
└──────────────┘
```

**Parquet Data Lake Yapısı:**
```
data/ohlcv/
└── binance/
    └── BTC/USDT/
        ├── 1m/
        │   └── 2026/
        │       └── 03/
        │           ├── 17/
        │           │   └── data.parquet
        │           └── 18/
        │               └── data.parquet
        └── 1h/
            └── market.parquet
```

---

## 🧩 Bileşenler

### **1. Piyasa Seçimi (Card 1)**

#### **🔍 Arama Filtresi**
- **ID:** `#market-search`
- **Tip:** Text Input
- **Placeholder:** `🔍 Coin Ara...`
- **Fonksiyon:** Sembol listesinde anlık filtreleme

#### **💹 Piyasa Tipi Filtresi**
- **ID:** `#market-type-filter`
- **Tip:** Select Dropdown
- **Seçenekler:**
  - `Tümü` (all)
  - `💰 Spot` (spot)
  - `💹 Futures` (swap)

#### **📊 Piyasa Listesi**
- **ID:** `#market-selection-list`
- **Tip:** Scrollable List
- **Her Satır:**
  - Sembol adı (örn: BTC/USDT)
  - Piyasa tipi (Spot/Futures)
  - Seçim checkbox'ı

**Seçim Mantığı:**
```javascript
// frontend/app.js
function selectSymbol(symbol, marketType) {
    document.getElementById('selected-symbol-val').textContent = symbol;
    document.getElementById('selected-symbol-val').dataset.market = marketType;
    
    // Highlight selected
    document.querySelectorAll('.market-item').forEach(item => {
        item.classList.remove('selected');
    });
    event.target.closest('.market-item').classList.add('selected');
}
```

---

### **2. İndirme Kontrolü (Card 2)**

#### **Seçili Sembol Kutusu**
- **ID:** `#selected-symbol-container`
- **Görünüm:** 
  ```
  Seçili Sembol: BTC/USDT (Futures)
  ```

#### **🏗️ Parquet Data Lake Detayları**

**Details/Summary Bileşeni:**
- **ID:** `#resampling-info-details`
- **Başlık:** `🏗️ Parquet Data Lake Mimarisi Detayları`

**İçerik:**
```
Sistem otomatik olarak SADECE 1 dakikalık mumları indirir ve 
Parquet formatında kaydeder.

Diğer zaman dilimleri (5m, 15m, 1h, 4h, vb.) otomatik olarak 
oluşturulur ve data/ohlcv/binance/ klasörüne kaydedilir.
```

#### **Zaman Dilimi Seçimi**
- **ID:** `#data-timeframe`
- **Tip:** Select Dropdown
- **Seçenekler:**
  - `1m` (1 dakika) - **Varsayılan**
  - `3m`, `5m`, `10m`, `15m`, `20m`, `30m`, `45m`
  - `1h`, `2h`, `3h`, `4h`, `6h`, `8h`, `12h`
  - `1d`, `1W`, `1M`

**Önemli:** Sistem sadece 1m indirir, diğer TF'ler resample edilir.

#### **Gün Sayısı**
- **ID:** `#data-days`
- **Tip:** Number Input
- **Varsayılan:** `30`
- **Min/Max:** `1 - 365`
- **Açıklama:** Kaç günlük veri indirilecek

#### **🚀 Veri İndir Butonu**
- **ID:** `#start-download-btn`
- **Class:** `btn btn-primary`
- **Etiket:** `🚀 Veri İndir`
- **Aksiyon:** İndirme görevini başlatır

**Event Handler:**
```javascript
// frontend/app.js
async function startDataDownload() {
    const symbol = document.getElementById('selected-symbol-val').textContent;
    const timeframe = document.getElementById('data-timeframe').value;
    const days = document.getElementById('data-days').value;
    
    if (symbol === '-- SEÇİNİZ --') {
        showToast('⚠️ Lütfen bir sembol seçin!', 'warning');
        return;
    }
    
    try {
        const response = await api.post('/api/v1/data/download-history', {
            symbol: symbol,
            timeframe: timeframe,
            days: parseInt(days)
        });
        
        showToast('✅ İndirme başlatıldı: ' + symbol, 'success');
        loadActiveTasks(); // Refresh task list
    } catch (error) {
        showToast('❌ İndirme hatası: ' + error.message, 'error');
    }
}
```

---

### **3. Görev Geçmişi (Card 3)**

#### **📋 Aktif Görevler Tablosu**

| Kolon | ID | Açıklama |
|-------|----|----------|
| **Sembol** | `.task-symbol` | İndirilen sembol (örn: BTC/USDT) |
| **Timeframe** | `.task-timeframe` | Zaman dilimi (1m, 1h, vb.) |
| **Durum** | `.task-status` | `🟢 Çalışıyor`, `⏸️ Duraklatıldı`, `✅ Tamamlandı` |
| **İlerleme** | `.task-progress` | Progress bar (0-100%) |
| **Kontrol** | `.task-controls` | ⏸️ Duraklat, ▶️ Devam, ❌ İptal butonları |

#### **İlerleme Çubuğu (Progress Bar)**

**HTML Yapısı:**
```html
<div class="progress-container">
    <div class="progress-bar" 
         id="task-progress-123" 
         style="width: 45%;"
         data-task-id="123">
    </div>
    <span class="progress-text">45%</span>
</div>
```

**Güncelleme Mantığı:**
```javascript
// frontend/app.js
function updateTaskProgress(taskId, progress) {
    const progressBar = document.getElementById(`task-progress-${taskId}`);
    const progressText = progressBar.nextElementSibling;
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${Math.round(progress)}%`;
        
        // Renk kodu
        if (progress >= 100) {
            progressBar.style.background = 'var(--neon-green)';
        } else if (progress >= 50) {
            progressBar.style.background = 'var(--neon-blue)';
        } else {
            progressBar.style.background = 'var(--neon-purple)';
        }
    }
}
```

#### **Görev Kontrol Butonları**

| Buton | Icon | ID Prefix | Aksiyon |
|-------|------|-----------|---------|
| **Duraklat** | ⏸️ | `#pause-task-` | İndirmeyi geçici durdur |
| **Devam** | ▶️ | `#resume-task-` | İndirmeyi devam ettir |
| **İptal** | ❌ | `#cancel-task-` | İndirmeyi iptal et ve sil |

**Event Handlers:**
```javascript
// frontend/app.js
async function pauseTask(taskId) {
    await api.post(`/api/v1/data/toggle-pause`, { task_id: taskId });
    showToast('⏸️ Görev duraklatıldı', 'info');
    loadActiveTasks();
}

async function resumeTask(taskId) {
    await api.post(`/api/v1/data/toggle-pause`, { task_id: taskId });
    showToast('▶️ Görev devam ediyor', 'info');
    loadActiveTasks();
}

async function cancelTask(taskId) {
    if (confirm('❌ İndirme iptal edilecek ve silinecek. Emin misiniz?')) {
        await api.post(`/api/v1/data/delete-task`, { task_id: taskId });
        showToast('❌ Görev iptal edildi', 'error');
        loadActiveTasks();
    }
}
```

---

## 🔄 İndirme İş Akışı

### **Adım 1: Piyasa Seçimi**
```
1. Arama kutusuna sembol yaz (örn: "BTC")
2. Filtre ile Spot/Futures seç
3. Listeden sembol tıkla → Seçili kutuda görünür
```

### **Adım 2: Parametre Girişi**
```
1. Timeframe seç (örn: 1m)
2. Gün sayısını gir (örn: 30)
3. "🚀 Veri İndir" butonuna tıkla
```

### **Adım 3: İndirme Başlatma**
```javascript
// API Request
POST /api/v1/data/download-history
{
    "symbol": "BTC/USDT",
    "timeframe": "1m",
    "days": 30
}

// API Response
{
    "status": "success",
    "task_id": "task_123",
    "message": "İndirme başlatıldı: BTC/USDT (30 gün)"
}
```

### **Adım 4: İlerleme İzleme**
```
Görev listesi her 2 saniyede otomatik güncellenir:
- Progress bar 0% → 100%
- Durum: "🟢 Çalışıyor" → "✅ Tamamlandı"
```

### **Adım 5: Veri Kullanımı**
```
İndirme tamamlandıktan sonra:
1. Veri Parquet formatında kaydedilir
2. ML eğitimi için kullanılabilir
3. Backtest için hazır
```

---

## 📊 İndirme İlerleme Durumları

| Durum | Icon | Renk | Açıklama |
|-------|------|------|----------|
| **Bekliyor** | ⏳ | Gri | Sırada bekliyor |
| **Çalışıyor** | 🟢 | Yeşil | Aktif indirme |
| **Duraklatıldı** | ⏸️ | Turuncu | Kullanıcı duraklattı |
| **Tamamlandı** | ✅ | Yeşil | İndirme başarılı |
| **Hata** | ❌ | Kırmızı | İndirme başarısız |

---

## 🚨 Sorun Giderme

### **Sorun 1: İndirme Başlamıyor**

**Semptom:** Butona tıklanınca reaksiyon yok

**Çözüm:**
1. Sembol seçildi mi kontrol et (`#selected-symbol-val`)
2. Console'da hata var mı bak
3. API çalışıyor mu test et:
   ```bash
   curl -X POST http://localhost:8000/api/v1/data/download-history \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTC/USDT","timeframe":"1m","days":30}'
   ```

---

### **Sorun 2: Progress Bar Güncellenmiyor**

**Semptom:** İndirme çalışıyor ama %0'da sabit

**Çözüm:**
1. Event Bus çalışıyor mu kontrol et
2. WebSocket bağlantısı aktif mi
3. Manuel refresh yap:
   ```javascript
   loadActiveTasks();
   ```

---

### **Sorun 3: İndirme Yarıda Kesiliyor**

**Semptom:** %50'de duruyor, hata veriyor

**Çözüm:**
1. Binance API limitini kontrol et (1200 weight/minute)
2. Internet bağlantısını test et
3. Disk alanı yeterli mi kontrol et:
   ```bash
   df -h data/ohlcv/
   ```

---

## 📚 İlgili Dokümanlar

- **Parquet Data Lake:** `features/parquet_data_lake.md`
- **ML Model Eğitimi:** `ui_reference/ml_decision_engine.md`
- **Backtest:** `ui_reference/strategy_builder.md`

---

*Bu doküman Veri Laboratuvarı v4.0 versiyonunu açıklar.*
*Güncellemeler için `frontend/index.html` (tab-data) ve `frontend/app.js` dosyalarını kontrol edin.*
