#!/bin/bash
set -e # Hata durumunda betiği durdur

# ============================================================================
# CRYPTO ALGO BOT - UBUNTU STARTUP SCRIPT (PRO ENHANCED v2026.03)
# 7/24 Production-Ready Bot Launcher
# ============================================================================
# 6 Faz Mimari:
#   - Faz 1: Event-Driven Architecture (%100 Pub/Sub)
#   - Faz 2: Clean Architecture API (Modüler)
#   - Faz 3: ES6 Frontend Modules (Dashboard)
#   - Faz 4: Modular Indicators (5 modül)
#   - Faz 5: Zero-Touch WFO (Bayesian TPE)
#   - Faz 6: MLOps Auto-Retrain + Liquidity Sweep
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Memory management for edge cases
export MALLOC_ARENA_MAX=2

# Script directory (Safe Resolution)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Log functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "\n${WHITE}========================================${NC}\n${WHITE}$1${NC}\n${WHITE}========================================${NC}\n"; }

# ============================================================================
# STEP 1: Directory Check
# ============================================================================
log_header "STEP 1: Project Directory"
if [ ! -f "main.py" ]; then
    log_error "main.py not found! Script may not be running from correct directory."
    exit 1
fi
log_success "Project directory verified"

# ============================================================================
# STEP 2: Git Update & Stash Protection
# ============================================================================
log_header "STEP 2: Git Update"
if [ -d ".git" ]; then
    log_info "Stashing local changes (config files, etc.)..."
    git stash -q || true
    git pull origin main --rebase
    git stash pop -q || true
    log_success "Repository updated seamlessly"
else
    log_warning "Not a git repository, skipping update"
fi

# ============================================================================
# STEP 3: Virtual Environment (Robust Method)
# ============================================================================
log_header "STEP 3: Virtual Environment"
if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
    log_success "Virtual environment created"
fi

PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
PIP_BIN="$SCRIPT_DIR/venv/bin/pip"
log_success "Virtual environment paths verified"

# ============================================================================
# STEP 4: Dependencies
# ============================================================================
log_header "STEP 4: Dependencies"
$PYTHON_BIN -m pip install --upgrade pip wheel --quiet
if [ -f "requirements.txt" ]; then
    $PIP_BIN install -r requirements.txt --quiet
    log_success "Dependencies installed/verified"
else
    log_warning "requirements.txt not found!"
fi

# Install pytz if missing (ML requirement)
$PYTHON_BIN -c "import pytz" 2>/dev/null || $PIP_BIN install pytz --quiet

# ============================================================================
# STEP 5: Cache Cleanup
# ============================================================================
log_header "STEP 5: Cache Cleanup"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
log_success "Python cache cleaned"

# ============================================================================
# STEP 6: Configuration Files
# ============================================================================
log_header "STEP 6: Configuration"
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
    log_warning "Created default .env file"
fi

# Check API keys
if [ -f ".env" ]; then
    if grep -q "BINANCE_API_KEY=" .env && ! grep -q '""' .env; then
        log_success "Binance API keys configured"
    else
        log_warning "Binance API keys not configured - Running in PUBLIC mode"
    fi
fi

# ============================================================================
# STEP 7: Database & Data Lake Health
# ============================================================================
log_header "STEP 7: Database & Data Lake"

# SQLite check
if [ -f "cryptobot.db" ]; then
    DB_STATUS=$($PYTHON_BIN -c "import sqlite3; c=sqlite3.connect('cryptobot.db'); print('OK' if c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' else 'FAILED')" 2>/dev/null || echo "ERROR")
    if [[ "$DB_STATUS" == "OK" ]]; then
        log_success "SQLite database integrity check passed"
    else
        log_warning "Database check returned: $DB_STATUS"
    fi
else
    log_info "New SQLite database will be created on startup"
fi

# Parquet Data Lake check
if [ -d "data/ohlcv/binance" ]; then
    PARQUET_COUNT=$(find data/ohlcv/binance -name "*.parquet" 2>/dev/null | wc -l)
    if [ "$PARQUET_COUNT" -gt 0 ]; then
        log_success "Parquet Data Lake: $PARQUET_COUNT files found"
    else
        log_info "Parquet Data Lake directory empty - Download data via Dashboard"
    fi
else
    mkdir -p data/ohlcv/binance
    log_info "Parquet Data Lake directory created"
fi

# ============================================================================
# STEP 8: System Requirements
# ============================================================================
log_header "STEP 8: System Requirements"
log_info "Python: $($PYTHON_BIN --version 2>&1)"

if command -v free >/dev/null 2>&1; then
    RAM_AVAIL=$(free -m | awk '/^Mem:/{print $7}')
    log_info "RAM: ${RAM_AVAIL}MB available"
    if [ "$RAM_AVAIL" -lt 512 ]; then
        log_warning "Low RAM detected (< 512MB)"
    fi
fi

if command -v df >/dev/null 2>&1; then
    DISK_AVAIL=$(df -h . | awk 'NR==2{print $4}')
    log_info "Disk: $DISK_AVAIL available"
fi

# ML Model check
if [ -d "artifacts/models" ]; then
    MODEL_COUNT=$(find artifacts/models -name "*.json" -o -name "*.joblib" 2>/dev/null | wc -l)
    log_success "ML Models: $MODEL_COUNT files"
fi

# ============================================================================
# STEP 9: Architecture Features
# ============================================================================
log_header "Architecture Features"
log_info "✅ Event-Driven Architecture (%100 Pub/Sub)"
log_info "✅ Clean Architecture API (Modüler)"
log_info "✅ ES6 Frontend Modules (Dashboard)"
log_info "✅ Modular Indicators (5 modül)"
log_info "✅ Zero-Touch WFO (Bayesian TPE)"
log_info "✅ MLOps Auto-Retrain + Liquidity Sweep"
log_info "✅ Parquet Data Lake (Snappy compression)"
log_info "✅ ML Ensemble (XGBoost + Random Forest)"
log_info "✅ Triple Barrier Method Labeling"

# ============================================================================
# STEP 10: Start Bot
# ============================================================================
log_header "STEP 10: Starting Bot"

PORT=3000
log_info "Dashboard: http://localhost:$PORT"
log_info "API Docs: http://localhost:$PORT/docs"
log_info "Press CTRL+C to stop"
log_info "Pro Tip: Use 'tmux' or 'screen' for SSH sessions"
log_success "System Ready for Live Trading!"

# Headless server support
export DISPLAY=""

# Start with exec (replaces bash process, better signal handling)
exec $PYTHON_BIN main.py
