#!/bin/bash
set -e

# ============================================================================
# CRYPTO ALGO BOT - UBUNTU ZERO-TOUCH STARTUP SCRIPT
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
WHITE='\033[1;37m'
NC='\033[0m'

# Script directory (Safe Resolution)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info() { echo -e "${BLUE}[BILGI]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[UYARI]${NC} $1"; }
log_error() { echo -e "${RED}[HATA]${NC} $1"; }
log_header() { echo -e "\n${WHITE}========================================${NC}\n${WHITE}$1${NC}\n${WHITE}========================================${NC}\n"; }

log_header "CryptoAlgoBot - Linux Baslatma"

# 1. Python Kontrolu
log_info "Python kurulumu kontrol ediliyor..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 sisteminizde kurulu degil!"
    echo -e "${YELLOW}Lutfen asagidaki komutu kopyalayip terminale yapistirarak gerekli kurulumlari yapin:${NC}"
    echo -e "\n  ${WHITE}sudo apt update && sudo apt install python3 python3-venv python3-pip${NC}\n"
    exit 1
fi
log_success "Python3 kurulumu dogrulandi."

# 2. Sanal Ortam (VENV) Kontrolu ve Olusturma
if [ ! -d "venv" ]; then
    log_info "Sanal ortam (venv) bulunamadi. Otomatik olusturuluyor..."
    python3 -m venv venv || {
        log_error "Sanal ortam olusturulamadi. Lutfen 'python3-venv' paketinin kurulu oldugundan emin olun."
        echo -e "Kurulum komutu: ${WHITE}sudo apt install python3-venv${NC}"
        exit 1
    }
    log_success "Sanal ortam basariyla olusturuldu."
else
    log_success "Sanal ortam bulundu."
fi

# 3. Aktivasyon ve Bagimliliklarin Yuklenmesi
log_info "Kutuphaneler ve bagimliliklar kontrol ediliyor..."
log_info "Ilk kurulum yapiliyorsa bagimliliklar indirilecektir."
log_info "Bu islem bilgisayar hiziniza ve internetinize gore birkac dakika surebilir, lutfen bekleyin..."

source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1 || {
        log_error "Bagimliliklar yuklenirken bir sorun olustu. Lutfen internet baglantinizi kontrol edin."
        exit 1
    }
    log_success "Tum bagimliliklar yuklendi ve guncel."
else
    log_warning "requirements.txt dosyasi bulunamadi!"
fi

# 4. Cevre Degiskenleri (.env) ve Config (config.yaml) Kontrolu
if [ ! -f ".env" ]; then
    log_info ".env dosyasi yok. Otomatik olusturuluyor..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_success ".env dosyasi olusturuldu. API anahtarlarini daha sonra duzenleyebilirsiniz."
    else
        log_warning ".env.example bulunamadi, .env olusturulamadi."
    fi
else
    log_success ".env dosyasi mevcut."
fi

if [ ! -f "config.yaml" ]; then
    log_info "config.yaml dosyasi yok. Otomatik olusturuluyor..."
    if [ -f "config.example.yaml" ]; then
        cp config.example.yaml config.yaml
        log_success "config.yaml dosyasi olusturuldu."
    else
        log_warning "config.example.yaml bulunamadi, config.yaml olusturulamadi."
    fi
else
    log_success "config.yaml dosyasi mevcut."
fi

# 5. Botu Baslatma
log_header "Bot Baslatiliyor"
log_info "Dashboard: http://localhost:3000"
log_info "Durdurmak icin: CTRL+C"
echo ""

# Headless server support
export DISPLAY=""

exec python3 main.py
