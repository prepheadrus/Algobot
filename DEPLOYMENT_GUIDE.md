# 🚀 CryptoAlgoBot - Production Deployment Guide

**⚠️ IMPORTANT:** This file has been moved and updated.

## 📍 New Location

For the most up-to-date deployment documentation, please visit:

**[knowledge/workflows/deployment_guide.md](knowledge/workflows/deployment_guide.md)**

---

## 📋 Quick Links

- **[Windows Deployment](knowledge/workflows/deployment_guide.md#windows-deployment)**
- **[Ubuntu Deployment](knowledge/workflows/deployment_guide.md#ubuntu-deployment)**
- **[Cloud Deployment](knowledge/workflows/deployment_guide.md#cloud-deployment)**
- **[Configuration Guide](knowledge/developer_reference/configuration_guide.md)**
- **[API Reference](knowledge/developer_reference/api_reference.md)**
- **[Health Check](knowledge/features/health_check_endpoint.md)**

---

## 🆕 What's New in v4.1.0?

### **New Deployment Features**
- ✅ Systemd service configuration (Ubuntu)
- ✅ Windows startup script (start_bot.bat)
- ✅ Oracle Cloud Free Tier optimization
- ✅ AWS EC2 deployment guide
- ✅ DigitalOcean Droplet setup
- ✅ Firewall configuration
- ✅ Health check endpoint integration

### **New Documentation**
- ✅ Step-by-step troubleshooting
- ✅ Performance benchmarks
- ✅ Security best practices
- ✅ Backup strategies
- ✅ Monitoring setup (Prometheus/Grafana)

---

## 🚀 Quick Start (Legacy)

If you still want to use this legacy guide:

### **Ubuntu:**
```bash
./setup.sh
sudo systemctl start cryptoalgobot
sudo systemctl status cryptoalgobot
```

### **Windows:**
```cmd
setup.bat
python main.py
```

---

## 📊 Systemd Service (Ubuntu)

The new deployment guide includes a complete systemd service configuration:

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

---

## 🔍 Troubleshooting

### **Bot Won't Start**

```bash
# Check logs
sudo journalctl -u cryptoalgobot -n 50

# Check status
sudo systemctl status cryptoalgobot

# Restart service
sudo systemctl restart cryptoalgobot
```

### **Dashboard Not Accessible**

```bash
# Check firewall
sudo ufw status
sudo ufw allow 3000/tcp

# Check port
netstat -tulpn | grep 3000
```

---

## 📞 Support

For complete deployment documentation and troubleshooting:

**[knowledge/workflows/deployment_guide.md](knowledge/workflows/deployment_guide.md)**

---

**Last Updated:** March 2026  
**Version:** v4.1.0  
**Status:** Production Ready ✅
