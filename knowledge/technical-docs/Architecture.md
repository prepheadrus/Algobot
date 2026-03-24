# 🏗️ Technical Docs: System Architecture

AlgoBot v4.1.0 ile birlikte sistem mimarisi devrim niteliğinde bir yeniliğe kavuşmuş olup, tamamen olay güdümlü (Event-Driven), modüler (API Modularization) ve Parquet (Hybrid Data Engine) tabanlı bir mimariye geçilmiştir.

Bu belgede sistemin temel yapı taşları açıklanmaktadır.

## 1. Genel Mimari Özeti (High-Level Architecture)

Sistem artık birbirine sıkı sıkıya bağlı (tightly-coupled) değil, olay veri yolu (Event Bus) üzerinden mesajlaşan (loosely-coupled) bir mikro-servis benzeri monolitik yapıda çalışır.

```mermaid
graph TD
    %% Bileşenler
    Binance[Binance / Crypto Exchange WS & REST]
    API_Layer[FastAPI Backend - 127.0.0.1:3000]
    WFO_Engine[Walk Forward Optimization Engine]
    ML_Pipeline[ML Pipeline - XGBoost]
    Parquet_Lake[(Parquet Data Lake)]
    SQLite[(SQLite Hot Buffer)]
    Event_Bus{Event Bus}
    Strategy_Engine[Strategy & Risk Engine]
    Position_Manager[Position Manager - O(1) Dictionary]

    %% Veri Akışı
    Binance -->|WS Ticker / REST Klines| API_Layer
    API_Layer -->|Data Service| WFO_Engine
    WFO_Engine -->|Save Batch Klines| Parquet_Lake
    WFO_Engine -->|Active Session Cache| SQLite

    %% ML & Strateji Akışı
    Parquet_Lake -->|Direct High-Speed Read| ML_Pipeline
    ML_Pipeline -->|Predictions & Features| Strategy_Engine
    Strategy_Engine -->|Generate Signal Event| Event_Bus

    %% Event Bus Akışı
    Event_Bus -->|Signal Received| Position_Manager
    Position_Manager -->|Execute Trade| Binance
    Position_Manager -->|Update State| SQLite
```

## 2. Hybrid Data Engine (Parquet & SQLite)

Sistemin "Kalbi" veri motorudur.

Eski versiyonlarda tüm geçmiş (historical) kline verileri ve indikatör verileri SQLite veritabanında tutuluyordu. Bu durum, veri büyüdükçe (`database is locked` hataları, I/O darboğazları) ve özellikle Makine Öğrenmesi (ML) tarafında DataFrame dönüşümlerinde (satır satır okuma) devasa performans kayıplarına yol açıyordu.

**Yeni Mimari:**
1.  **Parquet Data Lake (Cold & Warm Storage):** Binance vb. borsalardan çekilen geçmiş veriler (1m, 15m, 1h mumları) anında `pandas` kullanılarak `.parquet` dosyalarına dönüştürülüp sıkıştırılarak diske yazılır. Parquet, sütun tabanlı (columnar) format olduğu için ML pipeline'ı (özellik çıkarımı vb.) tüm veriyi RAM'e nanosaniyeler/milisaniyeler içinde yükler. Bu işlem SQLite'a göre yaklaşık **~300x - 500x daha hızlıdır**.
2.  **SQLite Hot Buffer:** SQLite artık sadece sistemin "Anlık Belleği" (State Machine) olarak görev yapar. Açık pozisyonlar, emir durumları, API Key ayarları ve sistemin genel konfigürasyonu (Configuration Manager) gibi küçük boyutlu, anlık olarak sorgulanan ve değişen durum bilgileri SQLite'da tutulur. Asla geriye dönük yüklü fiyat verileri barındırmaz.

## 3. Position Management (Performans Optimizasyonu)

Position (Pozisyon) yönetimi modülünde büyük bir algoritma optimizasyonu yapılmıştır. O(n) karmaşıklığına sahip döngüler $O(1)$ sözlük (dictionary) tabanlı erişim hızına çekilmiştir.

**Eski Durum $O(n)$:**
Sistem her bir tick/fiyat geldiğinde açık pozisyonu bulmak için tüm pozisyonları (örneğin listede dolaşarak: `for pos in positions: if pos.symbol == current_symbol`) arıyordu. 100 farklı parite izlenirken bu gereksiz işlemci yükü oluşturuyordu.

**Yeni Durum $O(1)$:**
Pozisyonlar sembol bazlı (`symbol -> Position`) bir hash map (Dictionary) yapısında tutulur. Fiyat güncellemeleri veya sinyal geldiğinde, ilgili pozisyon doğrudan bellekteki adresten `positions[symbol]` şeklinde çekilir.

```python
# Eski Yavaş Yöntem:
def get_position(symbol):
    for pos in self.active_positions: # O(n)
        if pos.symbol == symbol:
            return pos

# Yeni Hızlı Yöntem (Production-Ready):
def get_position(symbol):
    return self.active_positions.get(symbol) # O(1)
```

## 4. Güvenlik ve Ağ (Security & Networking)

- **Varsayılan Güvenlik (127.0.0.1):** Güvenlik açıklarını kapatmak ve veri sızıntılarını önlemek için FastAPI sunucusu artık `0.0.0.0` yerine varsayılan olarak **`127.0.0.1` (Localhost)** üzerinde `3000` portundan hizmet vermektedir.
- **Konfigürasyon (core/config.py):** Dış dünyaya (örneğin internete açık bir IP'den) veya bir Nginx reverse proxy arkasından hizmet vermek isterseniz, `.env` dosyasındaki `API_HOST` değerini manuel olarak `0.0.0.0` olarak değiştirmelisiniz.
- Bu yapı, dashboard'a yetkisiz erişimi engeller. Şifreleme anahtarları (`.secret.key`) ve hassas veriler (API keyler) backend belleğinde şifreli tutulur.

## 5. Bağımlılık (Dependency-Free) ve Native Python Uyumluluğu

AlgoBot v4.1.0 itibariyle projenin dış kütüphane bağımlılığı asgari düzeye indirilmiştir. En büyük değişiklik, kronik olarak uyumluluk (özellikle Python 3.10+ ve Ubuntu ortamlarında C-derleme hataları) sorunları yaratan `pandas-ta` kütüphanesinin **tamamen projeden çıkarılmasıdır**.

Sistem tüm RSI, MACD, EMA, SMA, ATR vb. teknik göstergeleri doğrudan **Saf Pandas Vektörel Operasyonları ve Numpy** kullanarak hesaplamaktadır (`data/indicators/` modülleri). Bu sayede:
1. Kurulum sırasında C derleyici (build-essential, ta-lib vs.) bağımlılığı kalmaz.
2. Hesaplamalar tam kontrollüdür ve ML Pipeline'ı için %100 uyumludur.
3. Python sürüm güncellemelerinde kod kırılmaz.

## 6. Event-Driven Architecture (Olay Güdümlü Mimari)

Sistemin iç iletişim ağı `Event Bus` üzerinden akar.
Örneğin bir `StopLoss` olayı gerçekleştiğinde, Pozisyon Yöneticisi doğrudan veritabanı sınıfını çağırmaz. Bunun yerine:

1. `PositionManager` -> `StopLossHitEvent` yayınlar.
2. `EventBus` -> Bu mesajı dinleyen tüm sistemlere (Telegram Botu, SQLite Kaydedici, Risk Motoru, Dashboard WebSocket'i) aynı anda asenkron (Non-blocking) olarak dağıtır.

Bu, kodun modülerliğini (API Modularization) artırırken, sistem bileşenlerinin birbirinden bağımsız (decoupled) olarak test edilmesini ve geliştirilmesini sağlar.
