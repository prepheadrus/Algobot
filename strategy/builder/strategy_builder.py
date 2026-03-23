"""
Strategy Builder - Ana Strateji Oluşturucu Sınıfı
Kullanıcı inputlarını alıp JSON strateji tanımı oluşturur.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class StrategyBuilder:
    """
    No-Code Strateji Oluşturucu
    
    Kullanıcı:
    1. Göstergeleri seçer
    2. Koşulları belirler
    3. Parametreleri ayarlar
    4. JSON formatında kaydeder
    """
    
    # Mevcut indikatörler ve parametreleri
    AVAILABLE_INDICATORS = {
        # Trend
        'EMA': {
            'category': 'trend',
            'parameters': {
                'length': {'type': 'int', 'default': 20, 'min': 1, 'max': 200}
            }
        },
        'SMA': {
            'category': 'trend',
            'parameters': {
                'length': {'type': 'int', 'default': 20, 'min': 1, 'max': 200}
            }
        },
        'Supertrend': {
            'category': 'trend',
            'parameters': {
                'multiplier': {'type': 'float', 'default': 3.0, 'min': 1.0, 'max': 10.0},
                'period': {'type': 'int', 'default': 10, 'min': 1, 'max': 50}
            }
        },
        
        # Momentum
        'RSI': {
            'category': 'momentum',
            'parameters': {
                'length': {'type': 'int', 'default': 14, 'min': 1, 'max': 50}
            }
        },
        'MACD': {
            'category': 'momentum',
            'parameters': {
                'fast': {'type': 'int', 'default': 12, 'min': 1, 'max': 50},
                'slow': {'type': 'int', 'default': 26, 'min': 1, 'max': 100},
                'signal': {'type': 'int', 'default': 9, 'min': 1, 'max': 50}
            }
        },
        'Stochastic': {
            'category': 'momentum',
            'parameters': {
                'k': {'type': 'int', 'default': 14, 'min': 1, 'max': 50},
                'd': {'type': 'int', 'default': 3, 'min': 1, 'max': 50}
            }
        },
        
        # Volatilite
        'ATR': {
            'category': 'volatility',
            'parameters': {
                'period': {'type': 'int', 'default': 14, 'min': 1, 'max': 50}
            }
        },
        'Bollinger': {
            'category': 'volatility',
            'parameters': {
                'length': {'type': 'int', 'default': 20, 'min': 1, 'max': 100},
                'std': {'type': 'float', 'default': 2.0, 'min': 0.5, 'max': 5.0}
            }
        },
        
        # Hacim
        'OBV': {
            'category': 'volume',
            'parameters': {}
        },
        'VWAP': {
            'category': 'volume',
            'parameters': {}
        },
        'MFI': {
            'category': 'volume',
            'parameters': {
                'period': {'type': 'int', 'default': 14, 'min': 1, 'max': 50}
            }
        }
    }
    
    def __init__(self):
        self.strategy = {
            'name': '',
            'description': '',
            'version': '1.0',
            'author': 'User',
            'created_at': datetime.now().isoformat(),
            'timeframe': '15m',
            'indicators': [],
            'conditions': {
                'long': {'logic': 'AND', 'rules': []},
                'short': {'logic': 'AND', 'rules': []}
            },
            'risk': {
                'stop_loss': {'type': 'ATR', 'multiplier': 2.0},
                'take_profit': {'type': 'ATR', 'multiplier': 3.0},
                'max_risk_percent': 2.0
            }
        }
        self.indicator_counter = 0
    
    def add_indicator(self, indicator_type: str, parameters: Optional[Dict] = None) -> str:
        """
        Stratejiye indikatör ekler
        
        Args:
            indicator_type: İndikatör tipi (RSI, MACD, EMA, vb.)
            parameters: İndikatör parametreleri
            
        Returns:
            indicator_id: Eklenen indikatörün ID'si
        """
        if indicator_type not in self.AVAILABLE_INDICATORS:
            raise ValueError(f"Bilinmeyen indikatör: {indicator_type}")
        
        # Parametre validasyonu
        indicator_config = self.AVAILABLE_INDICATORS[indicator_type]
        if parameters is None:
            parameters = {}
        
        # Varsayılan parametreleri kullan
        for param_name, param_config in indicator_config['parameters'].items():
            if param_name not in parameters:
                parameters[param_name] = param_config['default']
        
        # ID oluştur
        self.indicator_counter += 1
        indicator_id = f"{indicator_type.lower()}_{self.indicator_counter}"
        
        # İndikatörü ekle
        indicator = {
            'id': indicator_id,
            'type': indicator_type,
            'parameters': parameters
        }
        
        self.strategy['indicators'].append(indicator)
        return indicator_id
    
    def add_condition(self, side: str, indicator_id: str, operator: str, 
                     value: Any, logic: str = 'AND') -> None:
        """
        Koşul ekler
        
        Args:
            side: 'long' veya 'short'
            indicator_id: İndikatör ID'si
            operator: Karşılaştırma operatörü (<, >, =, <=, >=)
            value: Karşılaştırma değeri
            logic: Mantıksal operatör (AND, OR)
        """
        if side not in ['long', 'short']:
            raise ValueError("side 'long' veya 'short' olmalı")
        
        if operator not in ['<', '>', '=', '<=', '>=']:
            raise ValueError("Geçersiz operatör")
        
        # İndikatör var mı kontrol et
        indicator_exists = any(
            ind['id'] == indicator_id for ind in self.strategy['indicators']
        )
        if not indicator_exists:
            raise ValueError(f"İndikatör bulunamadı: {indicator_id}")
        
        # Koşulu ekle
        rule = {
            'indicator': indicator_id,
            'operator': operator,
            'value': value
        }
        
        self.strategy['conditions'][side]['rules'].append(rule)
        self.strategy['conditions'][side]['logic'] = logic
    
    def set_risk_params(self, stop_loss: float = 2.0, take_profit: float = 3.0, 
                       max_risk: float = 2.0) -> None:
        """
        Risk parametrelerini ayarla
        
        Args:
            stop_loss: ATR çarpanı
            take_profit: ATR çarpanı
            max_risk: Maksimum risk yüzdesi
        """
        self.strategy['risk'] = {
            'stop_loss': {'type': 'ATR', 'multiplier': stop_loss},
            'take_profit': {'type': 'ATR', 'multiplier': take_profit},
            'max_risk_percent': max_risk
        }
    
    def set_timeframe(self, timeframe: str) -> None:
        """Zaman dilimini ayarla"""
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d']
        if timeframe not in valid_timeframes:
            raise ValueError(f"Geçersiz zaman dilimi: {timeframe}")
        self.strategy['timeframe'] = timeframe
    
    def get_strategy_json(self, indent: int = 2) -> str:
        """
        Stratejiyi JSON string olarak döndür
        
        Args:
            indent: JSON indentasyonu
            
        Returns:
            JSON string
        """
        return json.dumps(self.strategy, indent=indent)
    
    def save_strategy(self, filepath: str) -> None:
        """
        Stratejiyi dosyaya kaydet
        
        Args:
            filepath: Dosya yolu
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.strategy, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_strategy(cls, filepath: str) -> 'StrategyBuilder':
        """
        Dosyadan strateji yükle
        
        Args:
            filepath: Dosya yolu
            
        Returns:
            StrategyBuilder instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            strategy_data = json.load(f)
        
        builder = cls()
        builder.strategy = strategy_data
        
        # Indicator counter'ı ayarla
        if strategy_data['indicators']:
            builder.indicator_counter = len(strategy_data['indicators'])
        
        return builder
    
    def reset(self) -> None:
        """Stratejiyi sıfırla"""
        self.__init__()
    
    def __str__(self) -> str:
        """Strateji özeti"""
        return f"Strategy: {self.strategy['name']} | Indicators: {len(self.strategy['indicators'])} | Timeframe: {self.strategy['timeframe']}"
