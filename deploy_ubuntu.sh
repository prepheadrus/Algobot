#!/bin/bash
set -e # Herhangi bir komut hata verirse betiği güvenli bir şekilde durdur

# ==============================================================================
# CryptoAlgoBot - Otomatik Kurulum ve Başlatma Betiği (Ubuntu Linux)
# ==============================================================================
# 6 Faz Mimari:
#   - Faz 1: Event-Driven Architecture (%100 Pub/Sub)
#   - Faz 2: Clean Architecture API (194 satır)
#   - Faz 3: ES6 Frontend Modules (210 satır)
#   - Faz 4: Modular Indicators (5 modül)
#   - Faz 5: Zero-Touch WFO (Bayesian TPE)
#   - Faz 6: MLOps Auto-Retrain + Liquidity Sweep
# ==============================================================================

echo -e "\e[36m🚀 CryptoAlgoBot Kurulumu Başlıyor...\e[0m"

# Betiğin çalıştığı dizini uygulamanın ana dizini olarak ayarla (Cron vs için güvenli)
cd "$(dirname "$0")"

# 1. Sistem Paketlerini Güncelle
echo -e "\e[33m\n[1/6] Sistem güncellemeleri kontrol ediliyor...\e[0m"
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Python ve Gerekli Sistem Bağımlılıklarını Kur
echo -e "\e[33m\n[2/6] Python 3, pip ve sistem bağımlılıkları kuruluyor...\e[0m"
sudo apt-get install -y python3 python3-pip python3-venv build-essential python3-dev libhdf5-serial-dev

# 3. Sanal Ortam (Virtual Environment) Oluşturma
echo -e "\e[33m\n[3/6] Python sanal ortamı (venv) oluşturuluyor...\e[0m"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "\e[32m✅ venv klasörü oluşturuldu.\e[0m"
else
    echo -e "\e[32m✅ venv klasörü zaten mevcut.\e[0m"
fi

# 4. Kütüphaneleri (Bağımlılıkları) Yükle
echo -e "\e[33m\n[4/6] Gerekli Python kütüphaneleri yükleniyor...\e[0m"
# source komutu yerine doğrudan venv içindeki executable'ları kullanmak daha stabildir
venv/bin/pip install --upgrade pip wheel

if [ -f "requirements.txt" ]; then
    venv/bin/pip install -r requirements.txt
    echo -e "\e[32m✅ Bağımlılıklar başarıyla yüklendi.\e[0m"
else
    echo -e "\e[31m⚠️ requirements.txt dosyası bulunamadı!\e[0m"
fi

# 5. Ortam (.env) kontrolü
if [ ! -f ".env" ]; then
    echo -e "\e[31m\n⚠️ .env dosyası bulunamadı! Lütfen '.env.example' dosyasından kopyalayarak oluşturun ve API bilgilerinizi doldurun.\e[0m"
fi

# 6. Parquet Data Lake dizinlerini oluştur
echo -e "\e[33m\n[5/6] Parquet Data Lake dizinleri oluşturuluyor...\e[0m"
mkdir -p data/ohlcv/binance
echo -e "\e[32m✅ data/ohlcv/binance dizini hazır.\e[0m"

echo -e "\e[32m\n✅ [6/6] Kurulum Tamamlandı!\e[0m"
echo -e "=============================================================================="
echo -e "\e[36mBot ve Dashboard Başlatılıyor...\e[0m"
echo -e "\e[33m💡 İpucu: Sunucuyu kapattığınızda botun kapanmaması için bu betiği 'tmux' veya 'screen' içinde çalıştırmanız önerilir.\e[0m"
echo -e "=============================================================================="
echo -e "\e[33mÖZELLİKLER:\e[0m"
echo -e "  - Event-Driven Architecture (%100 Pub/Sub)"
echo -e "  - Clean Architecture API (194 satır)"
echo -e "  - ES6 Frontend Modules (210 satır)"
echo -e "  - Modular Indicators (5 modül)"
echo -e "  - Zero-Touch WFO (Bayesian TPE)"
echo -e "  - MLOps Auto-Retrain + Liquidity Sweep"
echo -e "  - Parquet Data Lake (Snappy compression)"
echo -e "  - Order Book Imbalance Filtresi"
echo -e "  - Commission + Slippage Gerçekçi Backtest"
echo -e "=============================================================================="

# Linux terminal ortamında GUI/Matplotlib hatasını (X11) engellemek için
export DISPLAY=""

# Doğrudan sanal ortamdaki Python'u kullanarak ana uygulamayı başlat
exec venv/bin/python main.py
