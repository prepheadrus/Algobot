@echo off
REM ==============================================================================
REM CryptoAlgoBot - Otomatik Kurulum Betiği (Windows 10/11)
REM ==============================================================================
REM Bu betik, Windows üzerinde CryptoAlgoBot'u otomatik kurar.
REM Kullanım: setup.bat dosyasına çift tıklayın
REM ==============================================================================

echo.
echo ==========================================
echo   CryptoAlgoBot Kurulum Betigi
echo   Windows 10/11
echo ==========================================
echo.

REM 1. Python versiyon kontrolü
echo [INFO] Python versiyonu kontrol ediliyor...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python bulunamadi! Lutfen Python 3.8+ yukleyin.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

REM 2. Sanal Ortam (Virtual Environment) Olusturma
echo [INFO] Python sanal ortami olusturuluyor...
if exist "venv\" (
    echo [WARN] venv klasoru zaten mevcut, atalaniyor...
) else (
    python -m venv venv
    echo [INFO] venv klasoru olusturuldu.
)
echo.

REM 3. Virtual Environment'i Aktif Et
echo [INFO] Virtual environment aktif ediliyor...
call venv\Scripts\activate.bat

REM 4. Pip'i Guncelle
echo [INFO] Pip guncelleniyor...
python -m pip install --upgrade pip

REM 5. Kutuphaneleri Yukle
echo [INFO] Python kutuphaneleri yukleniyor (requirements.txt)...
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo [INFO] Tum Python kutuphaneleri basariyla yuklendi!
) else (
    echo [ERROR] requirements.txt dosyasi bulunamadi!
    pause
    exit /b 1
)
echo.

REM 6. .env Dosyasi Kontrolu
echo [INFO] .env dosyasi kontrol ediliyor...
if not exist ".env" (
    echo [WARN] .env dosyasi bulunamadi!
    if exist ".env.example" (
        echo [INFO] .env.example dosyasindan .env olusturuluyor...
        copy .env.example .env
        echo [WARN] .env dosyasi olusturuldu. Lutfen BINANCE_API_KEY ve BINANCE_API_SECRET degerlerini duzenleyin!
    ) else (
        echo [WARN] .env.example de bulunamadi. API anahtarlari icin .env dosyasi olusturmaniz gerekiyor.
    )
) else (
    echo [INFO] .env dosyasi mevcut.
)
echo.

REM 7. Config.yaml Kontrolu
echo [INFO] config.yaml kontrol ediliyor...
if not exist "config.yaml" (
    echo [ERROR] config.yaml dosyasi bulunamadi!
    pause
    exit /b 1
)
echo.

REM 8. Gerekli Klasorleri Olustur
echo [INFO] Gerekli klasorler olusturuluyor...
if not exist "artifacts\trained_models" mkdir artifacts\trained_models
if not exist "data" mkdir data
echo [INFO] Klasorler hazir.
echo.

REM 9. Kurulum Tamamlandi
echo ==========================================
echo   Kurulum Basariyla Tamamlandi!
echo ==========================================
echo.
echo Sonraki Adimlar:
echo.
echo 1. .env dosyasini duzenleyin (API anahtarlari opsiyonel):
echo    notepad .env
echo.
echo 2. config.yaml dosyasini duzenleyin (istegi bagli):
echo    notepad config.yaml
echo.
echo 3. Botu baslatin:
echo    venv\Scripts\activate
echo    python main.py
echo.
echo 4. Tarayicidan dashboard'a erisin:
echo    http://localhost:3000
echo    Swagger Docs: http://localhost:3000/docs
echo    Health Check: http://localhost:3000/api/v1/health
echo.
echo ==========================================
echo.
pause
