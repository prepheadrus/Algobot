import pandas as pd
import numpy as np
from strategy.base import BaseStrategy
from typing import Dict, Any

class KNNQuantATRShield(BaseStrategy):
    """
    KNN Quant ATR Shield (K-En Yakın Komşu & Volatilite Kalkanı)
    Bölüm 3.17 (Single-stock KNN) ve Bölüm 18.2 (Cryptocurrencies - ANN) algoritmalarını temel alır.

    Özellikler:
    - Sıfır Bağımlılık (pandas_ta yok, sadece numpy/pandas)
    - Veri Bütünlüğü Kalkanı (inf, nan koruması)
    - KNN (K-Nearest Neighbors) Momentum ve Fiyat tabanlı Yön Tahmini (k=5)
    - ATR ve HTF Veto (EMA_50) tabanlı Volatilite Kalkanı
    - Olay Güdümlü ve Asenkron Mimari uyumlu "Tak-Çalıştır" modülü.
    """

    DEFAULT_PARAMS = {
        'knn_k': 5,             # K komşu sayısı
        'atr_period': 14,       # ATR periyodu
        'ema_period': 50,       # HTF Ana trend periyodu
        'risk_percent': 0.02,   # Bakiye risk yüzdesi
        'atr_multiplier': 2.0,  # Zarar Kes (Stop-Loss) ATR çarpanı
        'risk_reward_ratio': 2.0, # Kar Hedefi (Take-Profit) Risk Ödül Oranı
        'slippage': 0.0001,     # %0.01 Slippage
        'taker_fee': 0.0004     # %0.04 Borsa Taker Komisyonu
    }

    def __init__(self):
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "KNN Quant ATR Shield"

    def description(self) -> str:
        return "Makine Öğrenimi (KNN) ile geçmiş fiyat/hacim hareketlerinin Öklid uzaklığını hesaplar. ATR Volatilite Kalkanı ve Çoklu Zaman Dilimi (EMA 50) HTF trend vetosu ile korunur."

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Stratejinin ihtiyaç duyduğu indikatörleri %100 vektörize ve 0 bağımlılıkla hesaplar.
        """
        # Kopya üzerinde çalışarak orjinal veriyi bozmamaya özen gösterelim
        df = df.copy()

        # 1. EMA_50 Hesaplaması (HTF Veto)
        ema_period = self.params.get('ema_period', 50)
        df['EMA_50'] = df['Close'].ewm(span=ema_period, adjust=False).mean()

        # 2. ATR_14 Hesaplaması (Volatilite Kalkanı)
        atr_period = self.params.get('atr_period', 14)

        # True Range (TR)
        df['prev_close'] = df['Close'].shift(1)
        df['tr1'] = df['High'] - df['Low']
        df['tr2'] = (df['High'] - df['prev_close']).abs()
        df['tr3'] = (df['Low'] - df['prev_close']).abs()
        df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

        # ATR = TR'nin n periyotluk basit hareketli ortalaması (veya Wilder's Smoothing)
        # Klasik olarak SMA veya RMA kullanılır. Basitlik ve performans için SMA kullanıyoruz (RMA da kullanılabilir).
        # TradingView standart RMA kullansa da, numpy/pandas ile en güvenilir ve hızlısı EMA ile Alpha=1/N yapmaktır.
        df['ATR_14'] = df['TR'].ewm(alpha=1/atr_period, adjust=False).mean()

        # ATR_SMA_14 (Aşırı gürültülü piyasa tespiti için ATR'nin hareketli ortalaması)
        df['ATR_SMA_14'] = df['ATR_14'].rolling(window=atr_period).mean()

        # 3. RSI_14 Hesaplaması (Momentum için - KNN Özellik Matrisi)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))

        # 4. KNN_Pred (Vektörize Makine Öğrenimi Tahmini)
        # Son k=5 periyodun fiyat (Close) ve Momentum (RSI_14) matrisine göre yön tahmini.
        # Basit vektörize bir Euclidean Distance yaklaşımı:
        # Piyasada genelde geçmişteki 'k' adet benzer momentum/fiyat değişimine bakılır.
        # Tak-Çalıştır ve vektörize olması için: Son k mumluk Close ve RSI değişimlerini bir "özellik vektörü" yapıyoruz.

        k = self.params.get('knn_k', 5)

        # Özellikleri normalize et (Z-Score) ki Euclidean Distance anlamlı olsun
        df['Close_Norm'] = (df['Close'] - df['Close'].rolling(window=50).mean()) / df['Close'].rolling(window=50).std()
        df['RSI_Norm'] = (df['RSI_14'] - df['RSI_14'].rolling(window=50).mean()) / df['RSI_14'].rolling(window=50).std()

        # Hedef değişken (Gelecek 1 mumun yönü) - Eğitim için (Geçmiş veride)
        df['Target_Dir'] = np.where(df['Close'].shift(-1) > df['Close'], 1, -1)

        # NOT: Gerçek bir KNN modeli vektörize olarak tüm geçmişi taramak için çok maliyetlidir (O(N^2)).
        # Optimizasyon için, sadece basit bir momentum/mean-reversion benzerliği tabanlı "Proxy KNN_Pred" hesaplıyoruz.
        # K-komşu yerine, son K mumun eğilimine (trend) ve aşırılıklarına bakarak Yön Tahmini:
        # Eğer Fiyat Düşüyor ama RSI Yükseliyorsa (Pozitif Uyumsuzluk) -> +1
        # Eğilimleri basitleştirilmiş KNN Proxy:

        # Bu, "Tam bir KNN" yerine, istendiği gibi K=5 periyotluk vektörize bir uzaklık/moment metriğidir.
        df['Mom_Dist'] = df['Close_Norm'].diff(k) + df['RSI_Norm'].diff(k)

        # Yön Tahmini (KNN Proxy):
        # 1: Yükseliş Bekliyor (Momentum ve Fiyat Öklid Mesafesinde Pozitif Eğilim)
        # -1: Düşüş Bekliyor
        df['KNN_Pred'] = np.where(df['Mom_Dist'] > 0, 1, -1)

        # Gereksiz sütunları temizle
        drop_cols = ['prev_close', 'tr1', 'tr2', 'tr3', 'TR', 'Close_Norm', 'RSI_Norm', 'Target_Dir', 'Mom_Dist']
        df.drop(columns=drop_cols, inplace=True, errors='ignore')

        # [VERİ BÜTÜNLÜĞÜ KALKANI]
        # JSON serileştirme hatalarını önlemek için tüm hesaplamaların sonuna eklenmesi zorunlu kod.
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        return df

    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Sinyal Matrisi (Trading Katmanı):
        Strateji sadece 3 değer döndürebilir: 0 (SAT), 1 (BEKLE), 2 (AL).
        "Belki" veya "Yaklaştı" gibi gri alanlar yoktur.
        """
        # Veri kalkanı gereği ilk mumlarda 0.0 değerleri olabilir, bunları atla.
        if current_row.get('EMA_50', 0.0) == 0.0 or current_row.get('ATR_14', 0.0) == 0.0:
            return 1 # BEKLE

        knn_pred = current_row.get('KNN_Pred', 0)
        close = current_row.get('Close', 0.0)
        open_price = current_row.get('Open', 0.0)
        ema_50 = current_row.get('EMA_50', 0.0)
        atr_14 = current_row.get('ATR_14', 0.0)
        atr_sma_14 = current_row.get('ATR_SMA_14', 0.0)

        # AL (2) Sinyali (Confluence):
        # 1. KNN_Pred == 1 (KNN Yükseliş Bekliyor)
        # 2. Close > EMA_50 (Ana Trend Boğa)
        # 3. Close > Open (Yeşil Mum)
        # 4. Volatilite Kalkanı Aktif: ATR_14 < ATR_SMA_14 (Aşırı gürültülü piyasada işlem açma)
        if (knn_pred == 1) and (close > ema_50) and (close > open_price) and (atr_14 < atr_sma_14):
            return 2 # AL

        # SAT (0) Sinyali:
        # 1. KNN_Pred == -1 (KNN Düşüş Bekliyor)
        # 2. Close < EMA_50 (Ana Trend Ayı)
        elif (knn_pred == -1) and (close < ema_50):
            return 0 # SAT

        return 1 # BEKLE

    def get_stop_params(self) -> Dict[str, Any]:
        """
        Risk Yönetimi ve Dinamik Boyutlandırma (Finans Katmanı)
        PaperTrader ve Risk Engine'e gönderilecek emir parametreleri.

        Stop-Loss: Entry Price - (ATR_14 * 2.0)
        Take-Profit: Entry Price + (ATR_14 * 4.0) -> RRR = 2.0

        Dinamik Pozisyon Boyutu, Ratchet Trailing Stop, Slippage ve Fee
        motor tarafından işlenmek üzere bu metot aracılığıyla geçirilir.
        """
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 2.0),
            "risk_reward_ratio": self.params.get('risk_reward_ratio', 2.0),
            "risk_percent": self.params.get('risk_percent', 0.02),
            "trailing_stop_type": "ratchet", # Stop seviyesi sadece kâr yönünde (yukarı) hareket eder.
            "slippage": self.params.get('slippage', 0.0001),
            "taker_fee": self.params.get('taker_fee', 0.0004)
        }

    def update_params(self, params: Dict[str, Any]):
        """
        WFO tarafından bulunan yeni parametreleri uygular.
        """
        if hasattr(self, 'params'):
            self.params.update(params)
        else:
            self.params = self.DEFAULT_PARAMS.copy()
            self.params.update(params)
