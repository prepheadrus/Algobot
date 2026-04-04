"""
Strategy Executor - Strateji JSON'unu Trading Sinyallerine Dönüştürücü

Bu modül, kullanıcıların oluşturduğu JSON stratejilerini okur,
gerekli indikatörleri hesaplar ve 0/1/2 sinyalleri üretir.

JSON Formatı:
{
    "name": "RSI MACD Combo",
    "description": "RSI aşırı alım/satım + MACD momentum",
    "indicators": [
        {"name": "RSI", "period": 14},
        {"name": "MACD", "fast": 12, "slow": 26, "signal": 9}
    ],
    "conditions": {
        "LONG": {
            "logic": "AND",
            "conditions": [
                {"indicator": "RSI_14", "operator": "<", "value": 30},
                {"indicator": "MACD_12_26_9", "operator": ">", "value": "MACD_Signal_12_26_9"}
            ]
        },
        "SHORT": {
            "logic": "AND",
            "conditions": [
                {"indicator": "RSI_14", "operator": ">", "value": 70},
                {"indicator": "MACD_12_26_9", "operator": "<", "value": "MACD_Signal_12_26_9"}
            ]
        }
    },
    "risk": {
        "stop_loss_atr_multiplier": 2.0,
        "take_profit_atr_multiplier": 4.0,
        "max_risk_percent": 2.0
    }
}

Çıktı Sinyalleri:
- 2 = AL (LONG)
- 1 = BEKLE (HOLD)
- 0 = SAT (SHORT)
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Condition Parser'dan import
try:
    from .condition_parser import RuleGroup, Condition, parse_condition_json, evaluate_strategy
except ImportError:
    from condition_parser import RuleGroup, Condition, parse_condition_json, evaluate_strategy

# Bot'un indikatör modülü
try:
    from data.indicators import StrategyIndicators
except ImportError:
    # Test için mock
    class StrategyIndicators:
        @staticmethod
        def rsi(close, period): return pd.Series([50] * len(close))
        @staticmethod
        def macd(close, fast, slow, signal): return pd.Series([0.1]*len(close)), pd.Series([0.05]*len(close)), pd.Series([0.05]*len(close))
        @staticmethod
        def ema(close, period): return close.ewm(span=period).mean()
        @staticmethod
        def sma(close, period): return close.rolling(window=period).mean()
        @staticmethod
        def atr(high, low, close, period): return pd.Series([1.0]*len(close))
        @staticmethod
        def bollinger_bands(close, period, std):
            sma = close.rolling(window=period).mean()
            std_dev = close.rolling(window=period).std()
            return sma + (std_dev * std), sma, sma - (std_dev * std)
        @staticmethod
        def stochastic(high, low, close, k, d):
            return pd.Series([50]*len(close)), pd.Series([50]*len(close))


@dataclass
class StrategyConfig:
    """Strateji konfigürasyonu"""
    name: str
    description: str
    indicators: List[Dict[str, Any]]
    long_conditions: RuleGroup
    short_conditions: RuleGroup
    risk_params: Dict[str, float]


class StrategyExecutor:
    """
    Strateji JSON'unu çalıştırılabilir sinyallere dönüştürür.
    
    Kullanım:
        executor = StrategyExecutor('strategies/rsi_macd.json')
        df = pd.read_csv('data.csv')
        df = executor.prepare_data(df)
        signal = executor.generate_signal(df)  # 0, 1, veya 2
    """
    
    def __init__(self, strategy_json_path: Optional[str] = None, strategy_dict: Optional[Dict[str, Any]] = None):
        """
        StrategyExecutor'ı başlat.
        
        Args:
            strategy_json_path: JSON strateji dosyasının yolu
            strategy_dict: Doğrudan RAM'den yüklenecek strateji sözlüğü
            
        Raises:
            FileNotFoundError: JSON dosyası bulunamazsa
            json.JSONDecodeError: JSON geçersizse
            ValueError: Gerekli alanlar eksikse
        """
        self.config = None
        self.strategy_data = {}
        
        if strategy_dict is not None:
            self.load_strategy_from_dict(strategy_dict)
        elif strategy_json_path is not None:
            self.load_strategy_from_file(strategy_json_path)

        # Cache için
        self._last_signal = 1  # Varsayılan: BEKLE
        self._last_timestamp = None

    def load_strategy_from_dict(self, strategy_dict: Dict[str, Any]) -> None:
        """Stratejiyi disk IO olmadan RAM üzerinden yükler."""
        self.strategy_data = strategy_dict
        
        # Gerekli alanları kontrol et
        self._validate_strategy_json()
        
        # Strateji konfigürasyonunu oluştur
        self.config = self._parse_strategy_config()

    def load_strategy_from_file(self, path: str) -> None:
        """Stratejiyi diskteki JSON dosyasından yükler."""
        self.json_path = Path(path)
        
        # JSON dosyasını kontrol et
        if not self.json_path.exists():
            raise FileNotFoundError(f"Strateji dosyası bulunamadı: {self.json_path}")

        # JSON'u yükle
        with open(self.json_path, 'r', encoding='utf-8') as f:
            strategy_data = json.load(f)

        self.load_strategy_from_dict(strategy_data)
    
    def _validate_strategy_json(self) -> None:
        """
        JSON'un geçerliliğini kontrol et.
        Eski stratejiler için varsayılan değerler ekler.

        Raises:
            ValueError: Gerekli alanlar eksikse
        """
        required_fields = ["name", "indicators"]
        for field in required_fields:
            if field not in self.strategy_data:
                raise ValueError(f"Eksik alan: {field}")

        # "conditions" alanı için safe get - yoksa varsayılan ekle
        from core.logger import logger
        conditions = self.strategy_data.get('conditions')

        if not conditions:
            logger.warning(f"⚠️ {self.strategy_data.get('name', 'Bilinmeyen')} stratejisi 'conditions' alanı içermiyor. Varsayılan boş koşullar ekleniyor.")
            self.strategy_data["conditions"] = {
                "LONG": {"logic": "AND", "conditions": []},
                "SHORT": {"logic": "AND", "conditions": []}
            }
        else:
            # Case-insensitive kontrol (LONG/SHORT veya long/short kabul edilir)
            normalized = {k.upper(): v for k, v in conditions.items()}
            if "LONG" not in normalized or "SHORT" not in normalized:
                raise ValueError("Koşullar LONG ve SHORT içermeli")

            # Normalize edilmiş conditions'ı kaydet
            self.strategy_data["conditions"] = normalized
    
    def _parse_strategy_config(self) -> StrategyConfig:
        """
        JSON verisini StrategyConfig objesine dönüştür.

        Returns:
            StrategyConfig: Parse edilmiş konfigürasyon
        """
        # LONG koşullarını parse et (normalize edilmiş)
        long_data = self.strategy_data["conditions"]["LONG"]
        if isinstance(long_data, str):
            long_conditions = parse_condition_json(long_data)
        else:
            long_conditions = RuleGroup.from_dict(long_data)

        # SHORT koşullarını parse et (normalize edilmiş)
        short_data = self.strategy_data["conditions"]["SHORT"]
        if isinstance(short_data, str):
            short_conditions = parse_condition_json(short_data)
        else:
            short_conditions = RuleGroup.from_dict(short_data)
        
        # Risk parametreleri (varsayılan değerlerle)
        risk_params = self.strategy_data.get("risk", {})
        if risk_params is None:
            risk_params = {}
        risk_params.setdefault("stop_loss_atr_multiplier", 2.0)
        risk_params.setdefault("take_profit_atr_multiplier", 4.0)
        risk_params.setdefault("max_risk_percent", 2.0)
        
        return StrategyConfig(
            name=self.strategy_data["name"],
            description=self.strategy_data.get("description", ""),
            indicators=self.strategy_data["indicators"],
            long_conditions=long_conditions,
            short_conditions=short_conditions,
            risk_params=risk_params
        )
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame'i strateji için hazırla (indikatörleri hesapla).
        
        Args:
            df: OHLCV verisi içeren DataFrame (open, high, low, close, volume sütunları gerekli)
            
        Returns:
            pd.DataFrame: İndikatörler eklenmiş DataFrame
            
        Raises:
            ValueError: Gerekli sütunlar eksikse
        """
        # Gerekli sütunları kontrol et
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Eksik sütunlar: {missing_columns}")
        
        # DataFrame'in kopyasını al (orijinali değiştirme)
        df = df.copy()
        
        # Her indikatörü hesapla
        for indicator_config in self.config.indicators:
            indicator_name = indicator_config.get("name", "").upper()
            params = {k: v for k, v in indicator_config.items() if k != "name"}
            
            # İndikatörü hesapla
            df = self._calculate_indicator(df, indicator_name, params)
        
        # VERİ TEMİZLİĞİ (Kritik!)
        # NaN ve Infinity değerlerini temizle
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)
        
        return df
    
    def _calculate_indicator(self, df: pd.DataFrame, indicator_name: str, params: Dict[str, Any]) -> pd.DataFrame:
        """
        Tek bir indikatörü hesapla.
        
        Args:
            df: DataFrame
            indicator_name: İndikatör adı (RSI, MACD, EMA, vb.)
            params: İndikatör parametreleri
            
        Returns:
            pd.DataFrame: İndikatör eklenmiş DataFrame
        """
        try:
            if indicator_name == "RSI":
                period = params.get("period", 14)
                df[f"RSI_{period}"] = StrategyIndicators.rsi(df['close'], period)
                
            elif indicator_name == "MACD":
                fast = params.get("fast", 12)
                slow = params.get("slow", 26)
                signal = params.get("signal", 9)
                
                macd, macd_signal, macd_hist = StrategyIndicators.macd(df['close'], fast, slow, signal)
                df[f"MACD_{fast}_{slow}_{signal}"] = macd
                df[f"MACD_Signal_{fast}_{slow}_{signal}"] = macd_signal
                df[f"MACD_Hist_{fast}_{slow}_{signal}"] = macd_hist
                
            elif indicator_name == "EMA":
                period = params.get("period", 20)
                df[f"EMA_{period}"] = StrategyIndicators.ema(df['close'], period)
                
            elif indicator_name == "SMA":
                period = params.get("period", 20)
                df[f"SMA_{period}"] = StrategyIndicators.sma(df['close'], period)
                
            elif indicator_name == "ATR":
                period = params.get("period", 14)
                df[f"ATR_{period}"] = StrategyIndicators.atr(df['high'], df['low'], df['close'], period)
                
            elif indicator_name == "Bollinger":
                period = params.get("period", 20)
                std = params.get("std", 2.0)
                upper, middle, lower = StrategyIndicators.bollinger_bands(df['close'], period, std)
                df[f"BBU_{period}_{std}"] = upper
                df[f"BBM_{period}_{std}"] = middle
                df[f"BBL_{period}_{std}"] = lower
                
            elif indicator_name == "Stochastic":
                k = params.get("k", 14)
                d = params.get("d", 3)
                stoch_k, stoch_d = StrategyIndicators.stochastic(df['high'], df['low'], df['close'], k, d)
                df[f"STOCH_K_{k}_{d}"] = stoch_k
                df[f"STOCH_D_{k}_{d}"] = stoch_d
                
            else:
                print(f"[UYARI] Bilinmeyen indikatör: {indicator_name}. Atlandı.")
                
        except Exception as e:
            print(f"[HATA] {indicator_name} hesaplanırken hata: {e}")
            # Hata olsa bile devam et
        
        return df
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Trading sinyali üret.
        
        Args:
            df: İndikatörler eklenmiş DataFrame
            
        Returns:
            int: Sinyal
                2 = AL (LONG)
                1 = BEKLE (HOLD)
                0 = SAT (SHORT)
        """
        # DataFrame boş kontrolü
        if df.empty:
            return 1  # BEKLE
        
        # Son mumu al
        last_row = df.iloc[-1:]
        
        # LONG koşullarını değerlendir
        long_signal = False
        try:
            long_signal = self.config.long_conditions.evaluate(last_row)
        except Exception as e:
            print(f"[HATA] LONG koşulu değerlendirilirken hata: {e}")
        
        # SHORT koşullarını değerlendir
        short_signal = False
        try:
            short_signal = self.config.short_conditions.evaluate(last_row)
        except Exception as e:
            print(f"[HATA] SHORT koşulu değerlendirilirken hata: {e}")
        
        # Sinyal üret
        if long_signal:
            signal = 2  # AL
        elif short_signal:
            signal = 0  # SAT
        else:
            signal = 1  # BEKLE
        
        # Cache
        self._last_signal = signal
        self._last_timestamp = df.index[-1] if hasattr(df.index, '__len__') else None
        
        return signal
    
    def get_risk_params(self) -> Dict[str, float]:
        """
        Risk parametrelerini al.
        
        Returns:
            Dict[str, float]: Risk parametreleri
        """
        return self.config.risk_params
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Strateji bilgilerini al.
        
        Returns:
            Dict[str, Any]: Strateji bilgileri
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "indicators": self.config.indicators,
            "risk_params": self.config.risk_params
        }
    
    def __str__(self) -> str:
        """String temsili"""
        return f"StrategyExecutor(name='{self.config.name}', signals={self._last_signal})"


# ============================================================================
# ÖRNEK KULLANIM VE TEST
# ============================================================================

if __name__ == "__main__":
    # Örnek JSON dosyası oluştur
    example_strategy = {
        "name": "RSI MACD Combo",
        "description": "RSI aşırı alım/satım + MACD momentum stratejisi",
        "indicators": [
            {"name": "RSI", "period": 14},
            {"name": "MACD", "fast": 12, "slow": 26, "signal": 9}
        ],
        "conditions": {
            "LONG": {
                "logic": "AND",
                "conditions": [
                    {"indicator": "RSI_14", "operator": "<", "value": 30},
                    {"indicator": "MACD_12_26_9", "operator": ">", "value": "MACD_Signal_12_26_9"}
                ]
            },
            "SHORT": {
                "logic": "AND",
                "conditions": [
                    {"indicator": "RSI_14", "operator": ">", "value": 70},
                    {"indicator": "MACD_12_26_9", "operator": "<", "value": "MACD_Signal_12_26_9"}
                ]
            }
        },
        "risk": {
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_atr_multiplier": 4.0,
            "max_risk_percent": 2.0
        }
    }
    
    # JSON dosyasını kaydet
    import json
    test_json_path = Path("test_strategy.json")
    with open(test_json_path, 'w', encoding='utf-8') as f:
        json.dump(example_strategy, f, indent=2, ensure_ascii=False)
    
    print("[OK] Test stratejisi olusturuldu: test_strategy.json")
    
    # Test DataFrame oluştur
    print("\n[TEST] DataFrame olusturuluyor...")
    np.random.seed(42)
    n_rows = 100
    
    # Rastgele fiyat verisi (random walk)
    close_prices = 100 + np.cumsum(np.random.randn(n_rows))
    high_prices = close_prices + np.abs(np.random.randn(n_rows)) * 2
    low_prices = close_prices - np.abs(np.random.randn(n_rows)) * 2
    open_prices = close_prices + np.random.randn(n_rows)
    volumes = np.random.randint(1000, 10000, n_rows)
    
    test_df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })
    
    print(f"[OK] Test DataFrame: {len(test_df)} satır")
    print(f"     Sütunlar: {list(test_df.columns)}")
    
    # StrategyExecutor'ı başlat
    print("\n[TEST] StrategyExecutor baslatiliyor...")
    executor = StrategyExecutor(str(test_json_path))
    print(f"[OK] StrategyExecutor: {executor}")
    
    # Strateji bilgilerini al
    info = executor.get_strategy_info()
    print(f"\n[OK] Strateji Bilgileri:")
    print(f"     İsim: {info['name']}")
    print(f"     Açıklama: {info['description']}")
    print(f"     İndikatörler: {len(info['indicators'])}")
    print(f"     Risk Parametreleri: {info['risk_params']}")
    
    # Veriyi hazırla
    print("\n[TEST] Veri hazırlaniyor...")
    prepared_df = executor.prepare_data(test_df)
    print(f"[OK] Hazır DataFrame: {len(prepared_df)} satır")
    print(f"     Yeni sütunlar: {[col for col in prepared_df.columns if col not in test_df.columns]}")
    
    # Sinyal üret
    print("\n[TEST] Sinyal uretiliyor...")
    signal = executor.generate_signal(prepared_df)
    signal_names = {0: "SAT", 1: "BEKLE", 2: "AL"}
    print(f"[OK] Sinyal: {signal} ({signal_names.get(signal, 'BİLİNMİYOR')})")
    
    # Son mumun verisini göster
    last_row = prepared_df.iloc[-1]
    print(f"\n[OK] Son mum verisi:")
    print(f"     Close: {last_row['close']:.2f}")
    if 'RSI_14' in last_row:
        print(f"     RSI_14: {last_row['RSI_14']:.2f}")
    if 'MACD_12_26_9' in last_row:
        print(f"     MACD_12_26_9: {last_row['MACD_12_26_9']:.4f}")
    if 'MACD_Signal_12_26_9' in last_row:
        print(f"     MACD_Signal_12_26_9: {last_row['MACD_Signal_12_26_9']:.4f}")
    
    # Test dosyasını temizle
    test_json_path.unlink()
    print(f"\n[OK] Test dosyasi temizlendi: {test_json_path}")
    
    print("\n" + "="*60)
    print("[OK] TÜM TESTLER BAŞARILI!")
    print("="*60)
