# 🚀 Deployment Guide

**Version:** v4.1.0  
**Status:** ✅ Production Ready  
**Category:** Deployment / Operations  
**Last Updated:** March 2026

---

## 📋 Overview

Deployment Guide, CryptoAlgoBot'u Windows ve Ubuntu sistemlerine kurma ve çalıştırma rehberidir.

**Supported Platforms:**
- ✅ Windows 10/11
- ✅ Ubuntu 20.04/22.04 LTS
- ✅ Oracle Cloud Free Tier
- ✅ AWS EC2
- ✅ DigitalOcean Droplet

---

## 🪟 Windows Deployment

### **System Requirements**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 10 GB | 50+ GB SSD |
| Python | 3.10+ | 3.12+ |

---

### **Step 1: Install Python**

```powershell
# Download Python 3.12
# https://www.python.org/downloads/

# Install with these options:
# ✅ Add Python to PATH
# ✅ Install pip
# ✅ Create shortcuts

# Verify installation
python --version  # Should show: Python 3.12.x
pip --version     # Should show: pip 24.x
```

---

### **Step 2: Clone Repository**

```powershell
# Create directory
mkdir C:\CryptoBot
cd C:\CryptoBot

# Clone repository
git clone https://github.com/prepheadrus/Crypto_Automat.git .
```

---

### **Step 3: Setup Virtual Environment**

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# You should see (venv) in prompt
```

---

### **Step 4: Install Dependencies**

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# This installs:
# - ccxt (Exchange connectivity)
# - pandas, numpy (Data processing)
# - xgboost, scikit-learn (ML)
# - fastapi, uvicorn (API)
# - aiosqlite (Database)
# - And more...
```

---

### **Step 5: Configure API Keys**

```powershell
# Copy example .env
copy .env.example .env

# Edit .env file
notepad .env
```

**Fill in your credentials:**
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
ENVIRONMENT=development
```

---

### **Step 6: Configure Bot**

```powershell
# Copy example config
copy config.example.yaml config.yaml

# Edit configuration
notepad config.yaml
```

**Recommended for Windows:**
```yaml
bot:
  environment: development
  log_level: DEBUG

risk_management:
  max_open_positions: 5
  kill_switch:
    enabled: true
```

---

### **Step 7: Download Data**

```powershell
# Start bot (auto-downloads data)
python main.py

# Or use dashboard:
# 1. Open http://localhost:3000
# 2. Go to "Veri Laboratuvarı"
# 3. Download BTC/USDT, ETH/USDT
```

---

### **Step 8: Start Bot**

```powershell
# Activate venv (if not already)
.\venv\Scripts\Activate.ps1

# Start bot
python main.py

# Expected output:
# ✅ BOT TAM OLARAK BAŞLATILDI!
# Dashboard: http://localhost:3000
```

---

### **Step 9: Access Dashboard**

```
Open browser: http://localhost:3000

Default credentials:
- No login required (local only)
```

---

### **Step 10: Create Startup Script**

**File:** `start_bot.bat`

```batch
@echo off
echo Starting CryptoAlgoBot...
cd /d %~dp0
call venv\Scripts\activate.bat
python main.py
pause
```

**Usage:**
```powershell
# Double-click to start
start_bot.bat
```

---

## 🐧 Ubuntu Deployment

### **System Requirements**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 20.04 | Ubuntu 22.04 LTS |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 10 GB | 50+ GB SSD |
| Python | 3.10+ | 3.12+ |

---

### **Step 1: Update System**

```bash
sudo apt update && sudo apt upgrade -y
```

---

### **Step 2: Install Python**

```bash
# Ubuntu 22.04+ (Python 3.10+ pre-installed)
python3 --version

# If needed, install Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev -y
```

---

### **Step 3: Clone Repository**

```bash
# Create directory
mkdir -p ~/CryptoBot
cd ~/CryptoBot

# Clone repository
git clone https://github.com/prepheadrus/Crypto_Automat.git .
```

---

### **Step 4: Setup Virtual Environment**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in prompt
```

---

### **Step 5: Install Dependencies**

```bash
# Upgrade pip
pip install --upgrade pip

# Install system dependencies
sudo apt install -y python3-dev build-essential libssl-dev libffi-dev

# Install Python requirements
pip install -r requirements.txt
```

---

### **Step 6: Configure API Keys**

```bash
# Copy example .env
cp .env.example .env

# Edit .env file
nano .env
```

**Fill in credentials:**
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
ENVIRONMENT=production
```

---

### **Step 7: Configure Bot**

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

**Recommended for Ubuntu (VPS):**
```yaml
bot:
  environment: production
  log_level: INFO

risk_management:
  max_open_positions: 10
  kill_switch:
    enabled: true
```

---

### **Step 8: Create Systemd Service**

**File:** `/etc/systemd/system/cryptobot.service`

```bash
sudo nano /etc/systemd/system/cryptobot.service
```

**Content:**
```ini
[Unit]
Description=CryptoAlgoBot Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/CryptoBot
Environment="PATH=/home/ubuntu/CryptoBot/venv/bin"
ExecStart=/home/ubuntu/CryptoBot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable cryptobot

# Start service
sudo systemctl start cryptobot

# Check status
sudo systemctl status cryptobot
```

---

### **Step 9: Configure Firewall**

```bash
# Allow port 3000 (Dashboard)
sudo ufw allow 3000/tcp

# Enable firewall (if not already)
sudo ufw enable

# Check status
sudo ufw status
```

---

### **Step 10: Access Dashboard**

```
Open browser: http://<your-server-ip>:3000

Example: http://123.45.67.89:3000
```

---

## ☁️ Cloud Deployment

### **Oracle Cloud Free Tier**

**Instance Specs:**
- 4 OCPU ARM64
- 24 GB RAM
- 200 GB Storage
- Free forever

**Setup Steps:**

1. **Create Instance:**
   ```
   - Image: Ubuntu 22.04
   - Shape: VM.Standard.A1.Flex
   - OCPUs: 4
   - Memory: 24 GB
   ```

2. **Add Security Rules:**
   ```
   Ingress Rules:
   - Port 22 (SSH)
   - Port 3000 (Dashboard)
   ```

3. **Deploy Bot:**
   ```bash
   # Follow Ubuntu deployment steps above
   ```

---

### **AWS EC2**

**Instance Type:** t3.medium (2 vCPU, 4 GB RAM)

**Setup:**
```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@<your-ec2-ip>

# Follow Ubuntu deployment steps
```

---

### **DigitalOcean Droplet**

**Droplet Type:** Basic ($6/month)
- 2 GB RAM
- 1 vCPU
- 50 GB SSD

**Setup:**
```bash
# Create droplet with Ubuntu 22.04
# Follow Ubuntu deployment steps
```

---

## 🔧 Maintenance

### **Update Bot**

```bash
# Stop bot
sudo systemctl stop cryptobot  # Ubuntu service
# OR CTRL+C  # Windows

# Pull latest changes
git pull

# Install new dependencies
pip install -r requirements.txt

# Restart bot
sudo systemctl start cryptobot  # Ubuntu service
# OR python main.py  # Windows
```

---

### **Backup Database**

```bash
# Create backup directory
mkdir -p backups

# Backup database
DATE=$(date +%Y%m%d_%H%M%S)
cp cryptobot.db backups/cryptobot_$DATE.db

# Keep last 7 days
find backups -name "cryptobot_*.db" -mtime +7 -delete
```

---

### **Monitor Bot**

```bash
# Check status (Ubuntu)
sudo systemctl status cryptobot

# View logs (Ubuntu)
sudo journalctl -u cryptobot -f

# View logs (Windows)
# Check terminal output or cryptobot.log file
```

---

### **Restart Bot**

```bash
# Ubuntu service
sudo systemctl restart cryptobot

# Windows
# CTRL+C then python main.py
```

---

## 🔍 Troubleshooting

### **Bot Won't Start**

**Symptoms:**
- Service fails to start
- Error messages in logs

**Solutions:**

1. **Check Python version:**
   ```bash
   python3 --version  # Should be 3.10+
   ```

2. **Check virtual environment:**
   ```bash
   source venv/bin/activate
   which python  # Should point to venv
   ```

3. **Check logs:**
   ```bash
   # Ubuntu
   sudo journalctl -u cryptobot -n 50
   
   # Windows
   # Check terminal output
   ```

---

### **Dashboard Not Accessible**

**Symptoms:**
- Can't open http://localhost:3000
- Connection refused

**Solutions:**

1. **Check if bot is running:**
   ```bash
   # Ubuntu
   sudo systemctl status cryptobot
   
   # Windows
   # Check if terminal is running
   ```

2. **Check firewall:**
   ```bash
   # Ubuntu
   sudo ufw status
   sudo ufw allow 3000/tcp
   
   # Windows
   # Allow port 3000 in Windows Defender Firewall
   ```

3. **Check port binding:**
   ```bash
   # Check if port 3000 is listening
   netstat -tulpn | grep 3000
   ```

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `start_bot.bat` | Windows startup script |
| `start_ubuntu_pro.sh` | Ubuntu startup script |
| `cryptobot.service` | Systemd service file |
| `.env.example` | Environment template |
| `config.example.yaml` | Config template |

---

## 🔄 Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.0.0 | Jan 2026 | Initial deployment guide |
| v4.1.0 | Mar 2026 | Added cloud deployment sections |

---

**Author:** CryptoAlgoBot Team  
**Review Status:** ✅ Peer Reviewed  
**Next Review:** April 2026
