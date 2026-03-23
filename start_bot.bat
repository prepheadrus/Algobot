@echo off
title CryptoAlgoBot
color 0A

echo.
echo ==========================================
echo   CryptoAlgoBot - Windows Baslatma
echo ==========================================
echo.

REM Script dizinine git
cd /d %~dp0

REM Virtual Environment kontrolu
if not exist "venv\Scripts\python.exe" (
    echo [HATA] Virtual environment bulunamadi!
    echo [HATA] Lutfen once setup.bat dosyasini calistirin.
    echo.
    pause
    exit /b 1
)

echo [OK] Virtual environment bulundu.
echo.

REM .env kontrolu
if not exist ".env" (
    echo [UYARI] .env dosyasi yok! Otomatik olusturuluyor...
    copy .env.example .env >nul
    echo [OK] .env olusturuldu. API anahtarlarini duzenleyin!
    echo.
)

REM config.yaml kontrolu
if not exist "config.yaml" (
    echo [HATA] config.yaml bulunamadi!
    echo [HATA] config.example.yaml'i config.yaml olarak kopyalayin.
    pause
    exit /b 1
)

echo [OK] Yapilandirma hazir.
echo.
echo ==========================================
echo   Bot baslatiliyor...
echo ==========================================
echo.
echo [BİLGİ] Dashboard: http://localhost:3000
echo [BİLGİ] Tarayici otomatik acilacak...
echo [BİLGİ] Durdurmak icin: Bu pencereyi kapat veya CTRL+C
echo.

REM Botu arka planda baslat
start /B call venv\Scripts\activate.bat ^&^& python main.py

REM 5 saniye bekle (bot baslasin)
timeout /t 5 /nobreak >nul

REM Tarayiciyi ac
echo [OK] Dashboard aciliyor...
start http://localhost:3000

echo.
echo ==========================================
echo   Bot calisiyor...
echo ==========================================
echo.
echo NOT: Bot penceresini acik tutun!
echo     Kapatmak icin pencereyi kapatin veya CTRL+C yapin.
echo.
pause
