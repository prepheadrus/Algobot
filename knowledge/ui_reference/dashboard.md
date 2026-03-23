# 📊 Dashboard (Ana Sayfa)

**Versiyon:** v4.0
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-portfolio)

---

## 🎯 Genel Bakış

Dashboard, CryptoAlgoBot'un ana kontrol panelidir. Gerçek zamanlı portföy metrikleri, açık pozisyonlar ve performans grafiklerini gösterir.

---

## 📁 Konum

```
Sol Menü → 📊 Portföy Analizi
```

---

## 🧩 Bileşenler

### **1. Metrik Kartları (Üst Sıra)**

#### **💰 Bakiye (Balance)**
- **ID:** `#balance-val`
- **Format:** `$0.00`
- **Açıklama:** Toplam hesap bakiyesi (USDT)
- **Güncellenme:** Her 3 saniyede otomatik
- **API:** `GET /api/v1/dashboard/metrics`

#### **🛡️ Serbest Marjin**
- **ID:** `#free-margin-val`
- **Format:** `$0.00`
- **Açıklama:** Yeni pozisyon açmak için kullanılabilir nakit
- **Formül:** `Bakiye - Kullanılan Marjin`

#### **📊 Kullanılan Marjin**
- **ID:** `#used-margin-val`
- **Format:** `$0.00`
- **Açıklama:** Açık pozisyonlarda kilitli marjin
- **Güncellenme:** Pozisyon açılış/kapanışında anlık

#### **🚀 Toplam P&L (Live)**
- **ID:** `#total-pnl-val`
- **Format:** `+$0.00` veya `-$0.00`
- **Renk:** 
  - Kar: `var(--neon-green)` (yeşil)
  - Zarar: `var(--neon-red)` (kırmızı)
- **Açıklama:** Tüm açık pozisyonların anlık kar/zarar toplamı

---

### **2. Envanter Özeti (Mini Stats Grid)**

| Metrik | ID | Format | Açıklama |
|--------|----|--------|----------|
| **Kâr Faktörü** | `#stat-profit-factor` | `1.0` | Brüt Kar / Brüt Zarar |
| **Max Drawdown** | `#stat-drawdown` | `0.0%` | Tepe'den çukura maksimum düşüş |
| **Sharpe Ratio** | `#stat-sharpe` | `0.0` | Risk-ajuste getiri (yıllık) |

---

### **3. 📈 Bakiye Gelişim Grafiği (Equity Curve)**

- **ID:** `#plotly-chart`
- **Kütüphane:** Plotly.js
- **Yükseklik:** 250px
- **Veri:** Her işlem sonrası bakiye geçmişi
- **Eksenler:**
  - X: Tarih (zaman)
  - Y: Bakiye (USDT)

**Render Fonksiyonu:**
```javascript
// frontend/app.js
function updatePerformanceMetrics(portfolio) {
    const equityCurve = portfolio.equity_curve || [];
    
    Plotly.newPlot('plotly-chart', [{
        x: equityCurve.map(p => p.timestamp),
        y: equityCurve.map(p => p.balance),
        type: 'scatter',
        mode: 'lines',
        line: { color: '#00ff88', width: 2 }
    }], {
        margin: { t: 20, r: 20, l: 40, b: 40 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    });
}
```

---

### **4. 🍕 Varlık Dağılımı**

- **ID:** `#allocation-chart`
- **Tip:** Pie Chart (Plotly)
- **Yükseklik:** 180px
- **Veri:** 
  - Nakit (Free Margin)
  - Pozisyonlar (Used Margin)
  - Kripto varlıklar (BTC, ETH, vb.)

---

### **5. 🔥 Piyasa İzleme Listesi**

- **ID:** `#market-heatmap`
- **Tip:** Heatmap (Renk kodlu tablo)
- **Veri:** 
  - Sembol adı
  - 24s değişim (%)
  - Hacim (USDT)
- **Renk Kodları:**
  - Yeşil: `> +2%` (Yükseliş)
  - Kırmızı: `< -2%` (Düşüş)
  - Gri: `-2% ~ +2%` (Yatay)

---

## 🔘 Butonlar ve Aksiyonlar

### **Kill Switch (Acil Durdurma)**

- **Konum:** Sol menü alt kısmı
- **ID:** `#kill-switch`
- **Class:** `btn btn-danger`
- **Etiket:** `ACİL DURDURMA`
- **Aksiyon:** Tüm botları anında durdur

**Event Handler:**
```javascript
// frontend/app.js
document.getElementById('kill-switch').addEventListener('click', async () => {
    if (confirm('⚠️ TÜM BOTLAR DURDURULACAK! Emin misiniz?')) {
        await api.post('/api/v1/bot/emergency-stop');
        showToast('🚨 Acil durdurma aktif edildi', 'error');
    }
});
```

---

## 🔄 Otomatik Güncelleme

| Bileşen | Interval | Kaynak |
|---------|----------|--------|
| **Metrik Kartları** | 3 saniye | WebSocket Push |
| **P&L (Live)** | 1 saniye | WebSocket Push |
| **Equity Curve** | İşlem başına | Event: `trade.closed` |
| **Heatmap** | 30 saniye | REST API Polling |

---

## 📊 Dashboard Veri Akışı

```
┌──────────────┐
│  Binance     │
│  WebSocket   │
└──────┬───────┘
       │ Ticker Updates
       ▼
┌──────────────┐
│  Exchange    │
│  Manager     │
└──────┬───────┘
       │ price.updated Event
       ▼
┌──────────────┐
│  Event Bus   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Dashboard   │
│  (UI)        │
└──────────────┘
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Bakiye Gösterilmiyor**

**Semptom:** `#balance-val` gösterge "--"

**Çözüm:**
1. API bağlantısını kontrol et
2. Console'da hata var mı bak:
   ```javascript
   console.log(store.get('system').metrics);
   ```
3. Bot çalışıyor mu kontrol et

---

### **Sorun 2: Equity Curve Çizilmiyor**

**Semptom:** Grafik boş

**Çözüm:**
1. En az 1 işlem geçmişini kontrol et
2. Plotly.js yüklü mü:
   ```html
   <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
   ```
3. Console'da hata var mı:
   ```javascript
   console.log('Equity curve data:', portfolio.equity_curve);
   ```

---

### **Sorun 3: Kill Switch Çalışmıyor**

**Semptom:** Buton tıklanınca reaksiyon yok

**Çözüm:**
1. Browser console'da hata kontrolü
2. API endpoint çalışıyor mu:
   ```bash
   curl -X POST http://localhost:8000/api/v1/bot/emergency-stop
   ```
3. Event Bus çalışıyor mu kontrol et

---

## 📚 İlgili Dokümanlar

- **Aktif Botlar Tablosu:** `ui_reference/active_bots_table.md`
- **İşlem Geçmişi:** `ui_reference/trade_history.md`
- **Risk Ayarları:** `ui_reference/risk_settings.md`

---

*Bu doküman Dashboard (Ana Sayfa) v4.0 versiyonunu açıklar.*
*Güncellemeler için `frontend/index.html` ve `frontend/app.js` dosyalarını kontrol edin.*
