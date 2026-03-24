@echo off
title CryptoAlgoBot
color 0A

echo.
echo ==========================================
echo   CryptoAlgoBot - Windows Baslatma
echo ==========================================
echo.

REM Script dizinine git
cd /d "%~dp0"

REM 1. Python Kontrolu
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [HATA] Python sisteminizde kurulu degil veya PATH'e eklenmemis!
    echo.
    echo Lutfen asagidaki adimlari izleyin:
    echo 1. https://www.python.org/downloads/ adresinden Python'i indirin.
    echo 2. Kurulum ekraninda "Add Python to PATH" (Python'i PATH'e ekle) secenegini MUTLAKA isaretleyin.
    echo 3. Kurulum bittikten sonra bu dosyayi tekrar calistirin.
    echo.
    pause
    exit /b 1
)
echo [OK] Python kurulumu dogrulandi.

REM 2. Sanal Ortam (VENV) Kontrolu ve Olusturma
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [BILGI] Sanal ortam (venv) bulunamadi. Sizin icin otomatik olusturuluyor...
    python -m venv venv
    if errorlevel 1 (
        color 0C
        echo [HATA] Sanal ortam olusturulamadi. Lutfen Python kurulumunuzu kontrol edin.
        pause
        exit /b 1
    )
    echo [OK] Sanal ortam basariyla olusturuldu.
) else (
    echo [OK] Sanal ortam bulundu.
)

REM 3. Aktivasyon ve Bagimliliklarin Yuklenmesi
echo.
echo [BILGI] Kutuphaneler ve bagimliliklar kontrol ediliyor...
echo [BILGI] Ilk kurulum yapiliyorsa bagimliliklar indirilecektir.
echo [BILGI] Bu islem bilgisayar hiziniza ve internetinize gore birkac dakika surebilir, lutfen bekleyin...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
if exist "requirements.txt" (
    pip install -r requirements.txt >nul 2>&1
    if errorlevel 1 (
        color 0C
        echo [HATA] Bagimliliklar yuklenirken bir sorun olustu. Lutfen internet baglantinizi kontrol edin.
        pause
        exit /b 1
    )
    echo [OK] Tum bagimliliklar yuklendi ve guncel.
) else (
    echo [UYARI] requirements.txt dosyasi bulunamadi!
)

REM 4. Cevre Degiskenleri (.env) ve Config (config.yaml) Kontrolu
echo.
if not exist ".env" (
    echo [BILGI] .env dosyasi yok. Otomatik olusturuluyor...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] .env dosyasi olusturuldu. API anahtarlarini daha sonra duzenleyebilirsiniz.
    ) else (
        echo [UYARI] .env.example bulunamadi, .env olusturulamadi.
    )
) else (
    echo [OK] .env dosyasi mevcut.
)

if not exist "config.yaml" (
    echo [BILGI] config.yaml dosyasi yok. Otomatik olusturuluyor...
    if exist "config.example.yaml" (
        copy config.example.yaml config.yaml >nul
        echo [OK] config.yaml dosyasi olusturuldu.
    ) else (
        echo [UYARI] config.example.yaml bulunamadi, config.yaml olusturulamadi.
    )
) else (
    echo [OK] config.yaml dosyasi mevcut.
)

REM 5. Botu Baslatma
echo.
echo ==========================================
echo   Bot baslatiliyor...
echo ==========================================
echo.
echo [BILGI] Dashboard: http://localhost:3000
echo [BILGI] Tarayici otomatik acilacak...
echo [BILGI] Durdurmak icin: Bu pencereyi kapat veya CTRL+C
echo.

REM Tarayiciyi birazdan acmasi icin arka planda bir timeout komutu calistiralim
start /B cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:3000"

REM Botu on planda baslat ki loglari ekranda gorebilsin ve hata alirsa pencere kapanmasin
python main.py

echo.
echo [HATA] Bot beklenmedik sekilde durdu!
echo.
pause
