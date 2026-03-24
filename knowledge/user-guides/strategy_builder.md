# 🎨 Strateji Oluşturucu (Strategy Builder)

**Versiyon:** v4.0
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-strategy-builder)

---

## 🎯 Genel Bakış

No-Code Strateji Oluşturucu, kullanıcıların kod bilgisi gerektirmeden görsel arayüz ile özel trading stratejileri oluşturmasını sağlar. Sürükle-bırak mantıksal operatörler ve indikatör kütüphanesi içerir.

---

## 📁 Konum

```
Sol Menü → 🎨 Strateji Oluşturucu
```

---

## 🏗️ Arayüz Düzeni

```
┌─────────────────────────────────────────────────────────┐
│  SOL PANEL           │  ORTA PANEL       │  SAĞ PANEL   │
│  📚 Gösterge         │  ⚙️ Koşul         │  🎯 Backtest │
│  Kütüphanesi         │  Oluşturucu       │  & Analiz    │
│                      │                   │              │
│  - TREND             │  - LONG Koşulları │  - Sembol    │
│  - MOMENTUM          │  - SHORT Koşulları│  - Timeframe │
│  - VOLATİLİTE        │  - VE/VEYA        │  - SL/TP     │
│  - VOLUME            │                   │  - Risk %    │
│                      │                   │              │
│  💾 Kaydedilmiş      │                   │  🧪 Test Et  │
│  Stratejiler         │                   │  💾 Kaydet   │
└─────────────────────────────────────────────────────────┘
```

---

## 🧩 Bileşenler

### **1. SOL PANEL: Gösterge Kütüphanesi**

#### **🔍 İndikatör Arama**
- **ID:** `#indicator-search`
- **Tip:** Text Input
- **Placeholder:** `🔍 İndikatör ara...`
- **Fonksiyon:** İndikatör listesinde anlık filtreleme

#### **📈 İndikatör Kategorileri**

**TREND İndikatörleri:**
| İndikatör | ID | Varsayılan Parametreler |
|-----------|----|-------------------------|
| **EMA (20)** | `.indicator-btn` | `{"period": 20}` |
| **SMA (20)** | `.indicator-btn` | `{"period": 20}` |
| **Supertrend** | `.indicator-btn` | `{"period": 10, "multiplier": 3}` |

**🚀 MOMENTUM İndikatörleri:**
| İndikatör | ID | Varsayılan Parametreler |
|-----------|----|-------------------------|
| **RSI (14)** | `.indicator-btn` | `{"period": 14}` |
| **MACD** | `.indicator-btn` | `{"fast": 12, "slow": 26, "signal": 9}` |

**📊 VOLATİLİTE İndikatörleri:**
| İndikatör | ID | Varsayılan Parametreler |
|-----------|----|-------------------------|
| **ATR (14)** | `.indicator-btn` | `{"period": 14}` |
| **Bollinger** | `.indicator-btn` | `{"period": 20, "std": 2}` |

#### **İndikatör Ekleme Butonu**
- **Class:** `.indicator-btn`
- **Data Attributes:**
  - `data-type`: İndikatör tipi (örn: "RSI")
  - `data-params`: JSON parametreler (örn: `{"period": 14}`)
- **Aksiyon:** Parametre modal'ını açar

**Event Handler:**
```javascript
// frontend/app.js
document.querySelectorAll('.indicator-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const type = e.currentTarget.dataset.type;
        const params = JSON.parse(e.currentTarget.dataset.params);
        
        openParamModal(type, params);
    });
});
```

---

### **2. ORTA PANEL: Koşul Oluşturucu**

#### **Strateji Meta Bilgileri**

**Strateji Adı:**
- **ID:** `#strategy-name`
- **Tip:** Text Input
- **Varsayılan:** `Yeni Strateji`
- **Max Uzunluk:** 50 karakter

**Açıklama:**
- **ID:** `#strategy-description`
- **Tip:** Textarea
- **Placeholder:** `Opsiyonel açıklama...`
- **Max Uzunluk:** 200 karakter

---

#### **🟢 LONG Koşulları**

**Container:**
- **ID:** `#long-conditions-container`
- **Class:** `.condition-builder`
- **Border:** `3px solid var(--neon-green)`

**Mantık Seçici (Logic Selector):**
- **ID:** `#long-logic-selector`
- **Butonlar:**
  - `VE (AND)` - Tüm koşullar sağlanmalı
  - `VEYA (OR)` - Koşullardan biri yeterli

**Koşul Ekleme Butonu:**
- **Class:** `.btn-add-rule`
- **Etiket:** `➕ LONG Koşulu Ekle`
- **Aksiyon:** Yeni koşul satırı ekler

**Koşul Satırı Yapısı:**
```html
<div class="condition-row" data-type="long">
    <select class="condition-select indicator">
        <option value="RSI">RSI</option>
        <option value="EMA">EMA</option>
        <option value="MACD">MACD</option>
    </select>
    
    <select class="condition-select operator">
        <option value=">">&gt;</option>
        <option value="<">&lt;</option>
        <option value=">=">&ge;</option>
        <option value="<=">&le;</option>
        <option value="==">=</option>
        <option value="crosses_over">Üstten Keser</option>
        <option value="crosses_under">Alt'tan Keser</option>
    </select>
    
    <input type="number" class="condition-input value" value="50">
    
    <button class="btn-remove-condition" onclick="removeCondition(this)">❌</button>
</div>
```

---

#### **🔴 SHORT Koşulları**

**Container:**
- **ID:** `#short-conditions-container`
- **Class:** `.condition-builder`
- **Border:** `3px solid var(--neon-red)`

**Mantık Seçici:**
- **ID:** `#short-logic-selector`
- **Butonlar:** `VE (AND)`, `VEYA (OR)`

**Koşul Ekleme:**
- **Etiket:** `➕ SHORT Koşulu Ekle`

---

### **3. SAĞ PANEL: Backtest & Risk**

#### **Backtest Parametreleri**

| Parametre | ID | Tip | Varsayılan | Min/Max |
|-----------|----|-----|------------|---------|
| **Sembol** | `#backtest-symbol` | Text | `BTC/USDT` | - |
| **Timeframe** | `#backtest-timeframe` | Select | `1h` | 1m-1d |
| **Gün** | `#backtest-days` | Number | `30` | 1-365 |
| **Bakiye** | `#backtest-balance` | Number | `10000` | 100-1M |

#### **Risk Parametreleri**

| Parametre | ID | Tip | Varsayılan | Min/Max |
|-----------|----|-----|------------|---------|
| **SL (ATR)** | `#stop-loss-atr` | Number | `2.0` | 0.1-10 |
| **TP (ATR)** | `#take-profit-atr` | Number | `4.0` | 0.1-20 |
| **Max Risk (%)** | `#max-risk-percent` | Number | `2.0` | 0.1-10 |

---

#### **🧪 Backtest Butonları**

**Backtest Başlat:**
- **ID:** Backtest button (onclick: `testStrategy()`)
- **Class:** `btn btn-primary`
- **Etiket:** `🧪 Backtest Başlat`
- **Aksiyon:** Backtest simülasyonunu başlatır

**Event Handler:**
```javascript
// frontend/app.js
async function testStrategy() {
    const strategy = {
        name: document.getElementById('strategy-name').value,
        description: document.getElementById('strategy-description').value,
        long_conditions: collectConditions('long'),
        short_conditions: collectConditions('short'),
        long_logic: getLogic('long'),
        short_logic: getLogic('short')
    };
    
    const backtestParams = {
        symbol: document.getElementById('backtest-symbol').value,
        timeframe: document.getElementById('backtest-timeframe').value,
        days: parseInt(document.getElementById('backtest-days').value),
        initial_balance: parseFloat(document.getElementById('backtest-balance').value),
        stop_loss_atr: parseFloat(document.getElementById('stop-loss-atr').value),
        take_profit_atr: parseFloat(document.getElementById('take-profit-atr').value),
        max_risk_percent: parseFloat(document.getElementById('max-risk-percent').value)
    };
    
    try {
        const results = await api.post('/api/v1/backtest/test', {
            strategy: strategy,
            params: backtestParams
        });
        
        renderBacktestResults(results);
    } catch (error) {
        showToast('❌ Backtest hatası: ' + error.message, 'error');
    }
}
```

**Stratejiyi Kaydet:**
- **Onclick:** `saveStrategy()`
- **Class:** `btn btn-success`
- **Etiket:** `💾 Stratejiyi Kaydet`
- **Aksiyon:** Stratejiyi JSON formatında kaydeder

**Temizle:**
- **Onclick:** `clearForm()`
- **Class:** `btn`
- **Etiket:** `🗑️ Temizle`
- **Aksiyon:** Tüm form alanlarını sıfırlar

---

### **4. Backtest Sonuçları**

#### **📊 Metrik Kutuları**

| Metrik | ID | Format | Açıklama |
|--------|----|--------|----------|
| **Win Rate** | `#metric-winrate` | `0%` | Kazanan işlem oranı |
| **Net PnL** | `#metric-pnl` | `$0` | Toplam kar/zarar |
| **Profit Factor** | `#metric-profit-factor` | `0` | Brüt Kar / Brüt Zarar |
| **Max DD** | `#metric-drawdown` | `0%` | Maksimum drawdown |

#### **📈 Equity Curve Grafiği**
- **ID:** `#equity-curve-chart`
- **Yükseklik:** 150px
- **Tip:** Line Chart (Plotly)
- **Veri:** Her işlem sonrası bakiye

#### **📋 Son İşlemler Tablosu**
- **ID:** `#trades-table-body`
- **Kolonlar:**
  - Tarih
  - Yön (LONG/SHORT)
  - Giriş Fiyatı
  - Çıkış Fiyatı
  - PnL ($)
  - PnL (%)

---

## 🔘 Mantıksal Operatörler

### **Karşılaştırma Operatörleri**

| Operatör | Sembol | Açıklama | Örnek |
|----------|--------|----------|-------|
| **Büyüktür** | `>` | Sol > Sağ | `RSI > 50` |
| **Küçüktür** | `<` | Sol < Sağ | `RSI < 30` |
| **Eşit veya Büyük** | `>=` | Sol ≥ Sağ | `EMA >= SMA` |
| **Eşit veya Küçük** | `<=` | Sol ≤ Sağ | `EMA <= SMA` |
| **Eşittir** | `==` | Sol = Sağ | `MACD == 0` |

---

### **Kesişim Operatörleri**

| Operatör | Sembol | Açıklama | Örnek |
|----------|--------|----------|-------|
| **Üstten Keser** | `crosses_over` | Sol çizgi sağ çizgiyi yukarı keser | `EMA crosses_over SMA` |
| **Alt'tan Keser** | `crosses_under` | Sol çizgi sağ çizgiyi aşağı keser | `EMA crosses_under SMA` |

**Kesişim Mantığı:**
```javascript
// frontend/app.js
function checkCrossOver(current, previous, target, targetPrevious) {
    // Önceki mum: current < target
    // Şu anki mum: current > target
    return previous <= targetPrevious && current > target;
}

function checkCrossUnder(current, previous, target, targetPrevious) {
    // Önceki mum: current > target
    // Şu anki mum: current < target
    return previous >= targetPrevious && current < target;
}
```

---

## 🔄 Strateji Oluşturma İş Akışı

### **Adım 1: İndikatör Seçimi**
```
1. Sol panelde indikatör kategorisini genişlet
2. İndikatör butonuna tıkla (örn: RSI)
3. Parametre modal'ı açılır
```

### **Adım 2: Parametre Girişi**
```
Modal'da:
- Period: 14
- Threshold: 70 (overbought)
- Threshold: 30 (oversold)
"Ekle" butonuna tıkla
```

### **Adım 3: Koşul Oluşturma**
```
1. "➕ LONG Koşulu Ekle" tıkla
2. İndikatör seç: RSI
3. Operatör seç: <
4. Değer gir: 30
```

### **Adım 4: Mantık Ayarı**
```
LONG Koşulları için:
- VE (AND): Tüm koşullar sağlanmalı
- VEYA (OR): Bir koşul yeterli
```

### **Adım 5: Backtest**
```
1. Sembol seç: BTC/USDT
2. Timeframe seç: 1h
3. Gün: 30
4. "🧪 Backtest Başlat" tıkla
```

### **Adım 6: Kaydetme**
```
1. Strateji adı gir: "RSI Oversold Strategy"
2. "💾 Stratejiyi Kaydet" tıkla
3. JSON formatında strategies/ klasörüne kaydedilir
```

---

## 📊 Strateji JSON Formatı

```json
{
    "name": "RSI Oversold Strategy",
    "description": "RSI 30'un altına inince LONG, 70'in üstüne çıkınca SHORT",
    "version": "1.0",
    "timeframe": "1h",
    "long_conditions": [
        {
            "indicator": "RSI",
            "params": {"period": 14},
            "operator": "<",
            "value": 30
        }
    ],
    "short_conditions": [
        {
            "indicator": "RSI",
            "params": {"period": 14},
            "operator": ">",
            "value": 70
        }
    ],
    "long_logic": "AND",
    "short_logic": "AND",
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0,
    "max_risk_percent": 2.0
}
```

---

## 🚨 Sorun Giderme

### **Sorun 1: İndikatör Eklenmiyor**

**Semptom:** Butona tıklanınca modal açılmıyor

**Çözüm:**
1. Console'da hata kontrolü
2. Modal element var mı:
   ```javascript
   console.log(document.getElementById('param-modal'));
   ```
3. Event listener bağlı mı:
   ```javascript
   console.log(document.querySelectorAll('.indicator-btn').length);
   ```

---

### **Sorun 2: Backtest Sonuçları Gösterilmiyor**

**Semptom:** Butona tıklanınca sonuç paneli açılmıyor

**Çözüm:**
1. API response kontrol et
2. `renderBacktestResults()` fonksiyonu çalışıyor mu
3. Sonuç paneli `display: none` değil mi:
   ```javascript
   document.getElementById('test-results').style.display = 'block';
   ```

---

### **Sorun 3: Strateji Kaydedilmiyor**

**Semptom:** "Kaydet" tıklanınca reaksiyon yok

**Çözüm:**
1. Strateji adı boş mu kontrol et
2. En az 1 koşul var mı
3. API endpoint çalışıyor mu:
   ```bash
   curl -X POST http://localhost:8000/api/v1/strategy/save \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Strategy",...}'
   ```

---

## 📚 İlgili Dokümanlar

- **No-Code Strategy Builder:** `features/no_code_strategy_builder.md`
- **Backtest Engine:** `core/backtester.py`
- **İndikatör Kütüphanesi:** `data/indicators/`

---

*Bu doküman Strateji Oluşturucu v4.0 versiyonunu açıklar.*
*Güncellemeler için `frontend/index.html` (tab-strategy-builder) ve `frontend/app.js` dosyalarını kontrol edin.*
