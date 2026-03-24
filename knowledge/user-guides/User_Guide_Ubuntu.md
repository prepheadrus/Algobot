# 🐧 User Guide: Ubuntu Zero-Touch Kurulumu ve Dashboard

Bu döküman, AlgoBot'un Ubuntu tabanlı sunucularda tamamen otonom (Zero-Touch) kurulumunu ve web tabanlı Dashboard arayüzünün kullanımını açıklamaktadır. Geliştiriciler ve sistem yöneticileri için, sistemin hızla ayağa kaldırılmasını sağlayan standart prosedürleri içerir.

## 🚀 1. Zero-Touch Kurulum (Ubuntu Pro)

AlgoBot v4.1.0 ile birlikte sistemin tüm bağımlılıklarını (Numpy, Parquet, XGBoost) otomatik yöneten `start_ubuntu_pro.sh` betiği devreye alınmıştır.

### Adım Adım Kurulum

Sunucunuza (Örn: AWS EC2, DigitalOcean Droplet, Hetzner) SSH ile bağlandıktan sonra aşağıdaki adımları izleyin:

```bash
# 1. Repoyu klonlayın
git clone https://github.com/your-repo/crypto-algobot.git
cd crypto-algobot

# 2. Betiği çalıştırılabilir yapın
chmod +x start_ubuntu_pro.sh

# 3. Kurulumu başlatın
./start_ubuntu_pro.sh
```

**Bu script ne yapar?**
- Sistemi günceller (`apt-get update`)
- Gerekli sistem kütüphanelerini kurar (python3-venv vb.)
- Sanal ortamı (`.venv`) oluşturur.
- Bağımlılıkları yükler (pandas-ta veya dış ML kütüphaneleri olmadan, saf Pandas/Numpy ve XGBoost).
- `.env.example` dosyasını otomatik olarak `.env` olarak kopyalar.
- Uygulamayı `127.0.0.1:3000` üzerinden başlatır.

> ⚠️ **Not:** Güvenlik gereği API sunucusu varsayılan olarak **sadece Localhost (127.0.0.1)** üzerinden yayın yapar. Dışarıdan erişim için Nginx/Apache ile Reverse Proxy kurulması veya `.env` içerisindeki `API_HOST` değerinin `0.0.0.0` olarak değiştirilmesi gerekir. (Production ortamında Reverse Proxy + SSL şiddetle tavsiye edilir).

## 🎛️ 2. Dashboard Kullanımı

Sistem başarıyla başlatıldığında, tarayıcınızdan `http://<Sunucu-IP>:3000` (Eğer dışarıya açtıysanız) veya yerel bilgisayarınızda `http://localhost:3000` adresine giderek Dashboard'a ulaşabilirsiniz.

### 2.1. System Settings (Sistem Ayarları)
İlk girişte Exchange (Borsa) API ayarlarını yapmanız gerekir.
- **API Key & Secret:** Borsanızdan aldığınız bilgileri girin. (Test amaçlıysanız Testnet kullanın).
- Bu bilgiler doğrudan şifrelenerek güvenli bir şekilde backend tarafına iletilir.

### 2.2. Data Laboratory (Veri Laboratuvarı)
Sistemin kalbi olan Parquet verilerini yönettiğimiz alandır.
- İstediğiniz pariteleri (Örn: `BTC/USDT`, `ETH/USDT`) ve zaman dilimlerini (Örn: `1h`, `15m`) seçin.
- **"Fetch Data"** butonuna basarak geçmiş veriyi indirin.
- Sistem bu veriyi milisaniyeler içinde indirip, XGBoost modelinin okuyabilmesi için **Parquet formatına dönüştürüp kaydeder.** SQLite yalnızca anlık işlem tamponu (Hot Buffer) olarak kullanılır.

### 2.3. ML Engine & Model Eğitimi (AI)
Veriyi indirdikten sonra ML sekmesine geçin.
- Model eğitmek istediğiniz pariteyi seçip **"Train Model"** deyin.
- Sistem; Parquet Lake üzerinden veriyi okuyacak, saf Pandas/Numpy ile indikatör özelliklerini (Feature Engineering) çıkaracak ve modeli eğitecektir.
- Çıkan **Accuracy (Doğruluk)** skorlarını ve backtest sonuçlarını ekrandan takip edebilirsiniz.

### 2.4. Trade History & Live Monitoring
Botu başlattığınızda açılan ve kapanan tüm pozisyonlar **Trade History** sekmesinde listelenir.
Sistem arka planda Event-Driven bir mimari kullandığı için yeni bir sinyal (Al/Sat) veya Kar Al (Take Profit) / Zarar Durdur (Stop Loss) gerçekleştiğinde Dashboard **sayfa yenilemeye gerek kalmadan otomatik olarak anında (Real-Time)** güncellenir.
