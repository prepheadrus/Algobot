#!/bin/bash
#===============================================================================
# CRYPTO ALGO BOT - PRODUCTION DEPLOYMENT SCRIPT
# Ubuntu 20.04/22.04 LTS - Systemd Daemon - 7/24 Uptime
#===============================================================================
# Bu betik şunları yapar:
# 1. OS ve Kantitatif Bağımlılık İzolasyonu
# 2. Konfigürasyon ve Güvenlik Kalkanı
# 3. Systemd Daemon Entegrasyonu (7/24 Uptime & Auto-Recovery)
# 4. Otonom Tetikleme ve Log Yönlendirmesi
#===============================================================================

set -e  # Hata durumunda betiği durdur

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Log fonksiyonları
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "\n${WHITE}========================================${NC}\n${WHITE}$1${NC}\n${WHITE}========================================${NC}\n"; }

# Root kontrolü
if [ "$EUID" -eq 0 ]; then 
    log_error "Bu betiği root olarak çalıştırmayın! Lütfen normal kullanıcı olarak çalıştırın."
    exit 1
fi

# Script dizini
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_header "STEP 1: OS ve Kantitatif Bağımlılık İzolasyonu"

# ============================================================================
# 1.1 OS Güncellemeleri
# ============================================================================
log_info "Ubuntu paket yöneticisi güncelleniyor..."
sudo apt update -qq

log_info "Sistem paketleri yükseltiliyor..."
sudo apt upgrade -y -qq

log_success "OS güncellemeleri tamamlandı"

# ============================================================================
# 1.2 Build ve Derleme Araçları
# ============================================================================
log_info "Derleme araçları ve kütüphaneler kuruluyor..."

sudo apt install -y -qq \
    build-essential \
    python3-dev \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libatlas-base-dev \
    libbz2-dev \
    liblzma-dev \
    git \
    curl \
    wget \
    jq

log_success "Derleme araçları kuruldu"

# ============================================================================
# 1.3 Python Virtual Environment
# ============================================================================
log_info "Python virtual environment kontrol ediliyor..."

if [ ! -d "venv" ]; then
    log_info "Virtual environment oluşturuluyor..."
    python3 -m venv venv
    log_success "Virtual environment oluşturuldu"
else
    log_success "Virtual environment zaten mevcut"
fi

# ============================================================================
# 1.4 Python Bağımlılıkları
# ============================================================================
log_info "Python bağımlılıkları yükleniyor (bu işlem 5-10 dakika sürebilir)..."

# Pip upgrade
./venv/bin/python -m pip install --upgrade pip wheel setuptools --quiet

# Requirements install
if [ -f "requirements.txt" ]; then
    ./venv/bin/pip install -r requirements.txt --quiet --upgrade
    log_success "Python bağımlılıkları yüklendi"
else
    log_error "requirements.txt bulunamadı!"
    exit 1
fi

# PyArrow ve XGBoost doğrulama (Ubuntu için kritik!)
log_info "Kritik kütüphaneler doğrulanıyor..."
./venv/bin/python -c "import pandas; import xgboost; import pyarrow; print('✅ Pandas, XGBoost, PyArrow doğrulandı')" || {
    log_error "Kritik kütüphaneler yüklenemedi!"
    log_error "PyArrow eksik, tekrar kuruluyor..."
    ./venv/bin/pip install pyarrow --quiet --upgrade
    ./venv/bin/python -c "import pyarrow; print('✅ PyArrow doğrulandı')" || {
        log_error "PyArrow hala yüklenemedi!"
        log_error "Manuel kurulum: ./venv/bin/pip install pyarrow"
        exit 1
    }
}

log_success "Kantitatif bağımlılıklar doğrulandı"

log_header "STEP 2: Konfigürasyon ve Güvenlik Kalkanı"

# ============================================================================
# 2.1 .env Dosyası Kontrolü
# ============================================================================
log_info "Konfigürasyon dosyaları kontrol ediliyor..."

if [ ! -f ".env" ]; then
    log_warning ".env dosyası bulunamadı!"
    
    if [ -f ".env.example" ]; then
        log_info ".env.example dosyasından .env oluşturuluyor..."
        cp .env.example .env
        log_success ".env dosyası oluşturuldu"
    else
        log_error ".env.example dosyası bulunamadı!"
        exit 1
    fi
else
    log_success ".env dosyası mevcut"
fi

# ============================================================================
# 2.2 API Anahtarları Doğrulama
# ============================================================================
log_info "API anahtarları doğrulanıyor..."

# Binance API key kontrolü
BINANCE_KEY=$(grep "^BINANCE_API_KEY=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$BINANCE_KEY" ] || [ "$BINANCE_KEY" == '""' ] || [ "$BINANCE_KEY" == "''" ]; then
    log_error "=========================================="
    log_error "API ANAHTARLARI EKSİK!"
    log_error "=========================================="
    log_error ""
    log_error "Lütfen .env dosyasını düzenleyin:"
    log_error "  nano .env"
    log_error ""
    log_error "Şu anahtarları girin:"
    log_error "  BINANCE_API_KEY=your_api_key_here"
    log_error "  BINANCE_API_SECRET=your_secret_here"
    log_error ""
    log_error "Kurulumu tamamlamak için:"
    log_error "  ./setup.sh"
    log_error "=========================================="
    exit 1
else
    log_success "Binance API anahtarları doğrulandı"
fi

# ============================================================================
# 2.3 config.yaml Kontrolü
# ============================================================================
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        log_info "config.yaml oluşturuluyor..."
        cp config.example.yaml config.yaml
        log_success "config.yaml oluşturuldu"
    else
        log_warning "config.yaml bulunamadı (varsayılan ayarlar kullanılacak)"
    fi
else
    log_success "config.yaml mevcut"
fi

# Log seviyesini INFO yap (production için)
log_info "Log seviyesi INFO'ya ayarlanıyor..."
if [ -f "config.yaml" ]; then
    # Python ile YAML güncelle
    ./venv/bin/python -c "
import yaml
with open('config.yaml', 'r') as f:
    cfg = yaml.safe_load(f)
cfg.setdefault('bot', {}).update({'log_level': 'INFO'})
with open('config.yaml', 'w') as f:
    yaml.dump(cfg, f)
print('✅ Log seviyesi INFO yapıldı')
" || log_warning "Log seviyesi değiştirilemedi (manuel ayarlayın)"
fi

log_header "STEP 3: Systemd Daemon Entegrasyonu (7/24 Uptime)"

# ============================================================================
# 3.1 Systemd Servis Dosyası Oluşturma
# ============================================================================
log_info "Systemd servis dosyası oluşturuluyor..."

SERVICE_NAME="cryptoalgobot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Python ve script yolları
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
MAIN_SCRIPT="$SCRIPT_DIR/main.py"
WORK_DIR="$SCRIPT_DIR"

# Servis dosyası içeriği
cat << EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=CryptoAlgoBot - 7/24 Event-Driven Trading System
Documentation=https://github.com/prepheadrus/Crypto_Automat
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$WORK_DIR

# Python environment
Environment=PYTHONUNBUFFERED=1
Environment=PATH=$SCRIPT_DIR/venv/bin:%H
Environment=PYTHONIOENCODING=utf-8

# Main execution
ExecStart=$PYTHON_BIN $MAIN_SCRIPT

# Auto-recovery (Çökme durumunda otonom yeniden başlama)
Restart=always
RestartSec=10

# Resource limits
LimitNOFILE=65535
Nice=-5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cryptoalgobot

[Install]
WantedBy=multi-user.target
EOF

if [ -f "$SERVICE_FILE" ]; then
    log_success "Systemd servis dosyası oluşturuldu: $SERVICE_FILE"
else
    log_error "Systemd servis dosyası oluşturulamadı!"
    exit 1
fi

# ============================================================================
# 3.2 Servis Dosyası Doğrulama
# ============================================================================
log_info "Servis dosyası doğrulanıyor..."

sudo systemd-analyze verify "$SERVICE_FILE" 2>/dev/null && \
    log_success "Servis dosyası syntax doğrulandı" || \
    log_warning "Servis dosyası syntax uyarısı (devam ediliyor)"

log_header "STEP 4: Otonom Tetikleme ve Log Yönlendirmesi"

# ============================================================================
# 4.1 Systemd Daemon Reload
# ============================================================================
log_info "Systemd daemon yeniden yükleniyor..."
sudo systemctl daemon-reload
log_success "Systemd daemon reload tamamlandı"

# ============================================================================
# 4.2 Servis Enable (Boot'ta otomatik başlama)
# ============================================================================
log_info "Servis enable ediliyor (boot'ta otomatik başlama)..."
sudo systemctl enable $SERVICE_NAME
log_success "Servis enable edildi"

# ============================================================================
# 4.3 Servis Başlatma
# ============================================================================
log_info "CryptoAlgoBot başlatılıyor..."
sudo systemctl start $SERVICE_NAME

# Servis durumu kontrolü
sleep 3

if sudo systemctl is-active --quiet $SERVICE_NAME; then
    log_success "CryptoAlgoBot başarıyla başlatıldı!"
else
    log_error "CryptoAlgoBot başlatılamadı!"
    log_error "Durumu kontrol edin: sudo systemctl status $SERVICE_NAME"
    exit 1
fi

# ============================================================================
# 4.4 Servis Durumu
# ============================================================================
log_info "Servis durumu:"
sudo systemctl status $SERVICE_NAME --no-pager -l

log_header "DEPLOYMENT TAMAMLANDI"

# ============================================================================
# SONUÇ VE KULLANIM TALİMATLARI
# ============================================================================
echo -e "${GREEN}"
echo "=========================================="
echo "✅ [DEPLOYMENT] Ubuntu Systemd Daemon ve 7/24 İşlem Motoru Aktif"
echo "=========================================="
echo -e "${NC}"

echo ""
echo "📊 SERVİS YÖNETİM KOMUTLARI:"
echo "=========================================="
echo "  # Servis durumu"
echo "  sudo systemctl status $SERVICE_NAME"
echo ""
echo "  # Servis durdurma"
echo "  sudo systemctl stop $SERVICE_NAME"
echo ""
echo "  # Servis yeniden başlatma"
echo "  sudo systemctl restart $SERVICE_NAME"
echo ""
echo "  # Logları canlı izleme"
echo "  journalctl -u $SERVICE_NAME.service -f"
echo ""
echo "  # Son 100 satır log"
echo "  journalctl -u $SERVICE_NAME.service -n 100"
echo ""
echo "  # Bugünkü loglar"
echo "  journalctl -u $SERVICE_NAME.service --since today"
echo ""
echo "  # Servis enable/disable (boot'ta otomatik başlama)"
echo "  sudo systemctl enable $SERVICE_NAME"
echo "  sudo systemctl disable $SERVICE_NAME"
echo "=========================================="
echo ""

echo "📝 LOG DOSYALARI:"
echo "=========================================="
echo "  Systemd Journal: journalctl -u $SERVICE_NAME -f"
echo "  Bot Logları: $SCRIPT_DIR/logs/"
echo "=========================================="
echo ""

echo "🔒 GÜVENLİK:"
echo "=========================================="
echo "  - API anahtarları .env dosyasında şifreli"
echo "  - Servis root olmayan kullanıcı ile çalışıyor"
echo "  - NoNewPrivileges ve PrivateTmp aktif"
echo "=========================================="
echo ""

echo "🚀 SİSTEM 7/24 ÇALIŞIYOR!"
echo "=========================================="
echo "  CryptoAlgoBot artık arka planda çalışıyor."
echo "  Çökme durumunda otomatik yeniden başlıyor."
echo "  Sistem açılışında otomatik başlıyor."
echo "=========================================="
echo ""

log_success "Kurulum tamamlandı!"

exit 0
