"""
Condition Parser - Strateji Koşullarını Ayrıştırıcı

Bu modül, kullanıcıların UI üzerinden oluşturduğu JSON stratejilerini
Python'un çalıştırabileceği mantıksal ağaçlara (AST) dönüştürür.

Örnek JSON:
{
    "logic": "AND",
    "conditions": [
        {
            "indicator": "RSI_14",
            "operator": "<",
            "value": 30
        },
        {
            "indicator": "MACD_12_26_9",
            "operator": ">",
            "value": "MACD_Signal_12_26_9"
        }
    ]
}

Bu JSON, aşağıdaki Python ifadesine dönüştürülür:
    (df['RSI_14'].iloc[-1] < 30) AND (df['MACD_12_26_9'].iloc[-1] > df['MACD_Signal_12_26_9'].iloc[-1])
"""

from dataclasses import dataclass, field
from typing import Union, List, Literal, Optional, Any
from enum import Enum
import pandas as pd


# ============================================================================
# SABİTLER VE TİP TANIMLARI
# ============================================================================

class Operator(str, Enum):
    """Karşılaştırma operatörleri"""
    GT = ">"   # Greater Than (Büyük)
    LT = "<"   # Less Than (Küçük)
    GTE = ">=" # Greater Than or Equal (Büyük veya Eşit)
    LTE = "<=" # Less Than or Equal (Küçük veya Eşit)
    EQ = "=="  # Equal (Eşit)
    NE = "!="  # Not Equal (Eşit Değil)


class LogicOperator(str, Enum):
    """Mantıksal operatörler"""
    AND = "AND"
    OR = "OR"


# Value tipi: Ya bir sayı (int/float) ya da başka bir indikatör adı (string)
Value = Union[int, float, str]


# ============================================================================
# VERİ MODELLERİ (DATACLASSES)
# ============================================================================

@dataclass
class Condition:
    """
    Tek bir koşulu temsil eder.
    
    Örnekler:
    - RSI < 30
    - MACD > Signal
    - Close >= EMA_50
    
    Attributes:
        indicator: İndikatör adı (örn: "RSI_14", "MACD_12_26_9")
        operator: Karşılaştırma operatörü (>, <, >=, <=, ==, !=)
        value: Karşılaştırma değeri (sayı veya başka indikatör adı)
    """
    indicator: str
    operator: Operator
    value: Value
    
    def __post_init__(self):
        """Veri doğrulama"""
        # Indicator boş olamaz
        if not self.indicator or not self.indicator.strip():
            raise ValueError("İndikatör adı boş olamaz")
        
        # Value boş olamaz
        if self.value is None:
            raise ValueError("Değer boş olamaz")
        
        # Value string ise (başka indikatör), boş olamaz
        if isinstance(self.value, str) and not self.value.strip():
            raise ValueError("İndikatör değeri boş olamaz")
    
    def evaluate(self, df: pd.DataFrame) -> bool:
        """
        Bu koşulu DataFrame üzerinde değerlendir.
        
        Args:
            df: OHLCV + indikatörler içeren DataFrame
            
        Returns:
            bool: Koşul sağlanıyorsa True, değilse False
            
        Raises:
            KeyError: İndikatör DataFrame'de yoksa
            IndexError: DataFrame boşsa
        """
        # Son mumun verisini al
        if df.empty:
            raise IndexError("DataFrame boş, koşul değerlendirilemiyor")
        
        last_idx = len(df) - 1
        
        # İndikatör değerini al
        if self.indicator not in df.columns:
            raise KeyError(f"İndikatör '{self.indicator}' DataFrame'de bulunamadı")
        
        left_value = df[self.indicator].iloc[last_idx]
        
        # Sağ taraf değeri al (sayı veya başka indikatör)
        if isinstance(self.value, (int, float)):
            right_value = self.value
        else:
            # Başka bir indikatör
            if self.value not in df.columns:
                raise KeyError(f"İndikatör '{self.value}' DataFrame'de bulunamadı")
            right_value = df[self.value].iloc[last_idx]
        
        # Karşılaştırmayı yap
        if self.operator == Operator.GT:
            return left_value > right_value
        elif self.operator == Operator.LT:
            return left_value < right_value
        elif self.operator == Operator.GTE:
            return left_value >= right_value
        elif self.operator == Operator.LTE:
            return left_value <= right_value
        elif self.operator == Operator.EQ:
            return left_value == right_value
        elif self.operator == Operator.NE:
            return left_value != right_value
        
        return False
    
    def to_dict(self) -> dict:
        """
        Condition'ı dictionary'e çevir (JSON serialization için).
        
        Returns:
            dict: Condition'ın dictionary temsili
        """
        return {
            "indicator": self.indicator,
            "operator": self.operator.value if isinstance(self.operator, Operator) else self.operator,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Condition':
        """
        Dictionary'den Condition oluştur.
        
        Args:
            data: Dictionary (JSON'dan parse edilmiş)
            
        Returns:
            Condition: Oluşturulan Condition objesi
            
        Raises:
            ValueError: Gerekli alanlar eksikse
        """
        # Gerekli alanları kontrol et
        required_fields = ["indicator", "operator", "value"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Eksik alan: {field_name}")
        
        # Operator'ü enum'a çevir
        operator = data["operator"]
        if isinstance(operator, str):
            try:
                operator = Operator(operator)
            except ValueError:
                raise ValueError(f"Geçersiz operatör: {operator}. Geçerli değerler: {[op.value for op in Operator]}")
        
        return cls(
            indicator=data["indicator"],
            operator=operator,
            value=data["value"]
        )


@dataclass
class RuleGroup:
    """
    Koşul grubunu temsil eder (AND/OR mantığı ile birleştirilmiş koşullar).
    
    Örnekler:
    - (RSI < 30) AND (MACD > Signal)
    - (Close > EMA_50) OR (Close > SMA_200)
    - ((RSI < 30) AND (MACD > Signal)) OR (Close > Upper_Band)
    
    Attributes:
        logic: Mantıksal operatör (AND veya OR)
        conditions: Koşullar veya alt gruplar listesi
    """
    logic: LogicOperator
    conditions: List[Union['Condition', 'RuleGroup']] = field(default_factory=list)
    
    def __post_init__(self):
        """Veri doğrulama"""
        # Logic geçerli olmalı
        if not isinstance(self.logic, LogicOperator):
            raise ValueError(f"Geçersiz logic operatörü: {self.logic}. Geçerli değerler: {[op.value for op in LogicOperator]}")
        
        # Boş conditions listesine izin ver
    
    def add_condition(self, condition: Union[Condition, 'RuleGroup']) -> None:
        """
        Gruba yeni koşul ekle.
        
        Args:
            condition: Eklenecek Condition veya RuleGroup
        """
        self.conditions.append(condition)
    
    def evaluate(self, df: pd.DataFrame) -> bool:
        """
        Bu kural grubunu DataFrame üzerinde değerlendir.
        
        Args:
            df: OHLCV + indikatörler içeren DataFrame
            
        Returns:
            bool: Tüm koşullar sağlanıyorsa True, değilse False
            
        Raises:
            IndexError: DataFrame boşsa
            KeyError: İndikatör DataFrame'de yoksa
        """
        if df.empty:
            raise IndexError("DataFrame boş, kural grubu değerlendirilemiyor")
        
        # Her koşulu değerlendir
        results = []
        for condition in self.conditions:
            if isinstance(condition, Condition):
                result = condition.evaluate(df)
            elif isinstance(condition, RuleGroup):
                result = condition.evaluate(df)
            else:
                raise TypeError(f"Geçersiz koşul tipi: {type(condition)}")
            
            results.append(result)
            
            # Kısa devre değerlendirmesi (short-circuit evaluation)
            if self.logic == LogicOperator.AND:
                # AND: İlk False gördüğümüzde dur (çünkü sonuç False olacak)
                if not result:
                    return False
            elif self.logic == LogicOperator.OR:
                # OR: İlk True gördüğümüzde dur (çünkü sonuç True olacak)
                if result:
                    return True
        
        # Tüm sonuçları döndür
        if self.logic == LogicOperator.AND:
            return all(results)
        elif self.logic == LogicOperator.OR:
            return any(results)
        
        return False
    
    def to_dict(self) -> dict:
        """
        RuleGroup'u dictionary'e çevir (JSON serialization için).
        
        Returns:
            dict: RuleGroup'un dictionary temsili
        """
        return {
            "logic": self.logic.value if isinstance(self.logic, LogicOperator) else self.logic,
            "conditions": [
                cond.to_dict() if isinstance(cond, Condition) else cond.to_dict()
                for cond in self.conditions
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RuleGroup':
        """
        Dictionary'den RuleGroup oluştur.
        
        Args:
            data: Dictionary (JSON'dan parse edilmiş)
            
        Returns:
            RuleGroup: Oluşturulan RuleGroup objesi
            
        Raises:
            ValueError: Gerekli alanlar eksikse
        """
        # Gerekli alanları kontrol et
        if "logic" not in data:
            raise ValueError("Eksik alan: logic")

        # "conditions" veya "rules" alanı olabilir (eski stratejiler için)
        # Empty list should be allowed
        rules_data = data.get('conditions')
        if rules_data is None:
            rules_data = data.get('rules')
        if rules_data is None:
            raise ValueError("Eksik alan: conditions veya rules")
        
        # Logic'i enum'a çevir
        logic = data["logic"]
        if isinstance(logic, str):
            try:
                logic = LogicOperator(logic)
            except ValueError:
                raise ValueError(f"Geçersiz logic operatörü: {logic}. Geçerli değerler: {[op.value for op in LogicOperator]}")
        
        # Koşulları oluştur
        conditions = []
        for cond_data in rules_data:
            # Nested RuleGroup mu yoksa Condition mu?
            if "logic" in cond_data:
                # Bu bir RuleGroup
                condition = cls.from_dict(cond_data)
            else:
                # Bu bir Condition
                condition = Condition.from_dict(cond_data)

            conditions.append(condition)
        
        return cls(logic=logic, conditions=conditions)


# ============================================================================
# YARDIMCI FONKSİYONLAR
# ============================================================================

def parse_condition_json(json_str: str) -> RuleGroup:
    """
    JSON string'den RuleGroup oluştur.
    
    Args:
        json_str: JSON string
        
    Returns:
        RuleGroup: Oluşturulan RuleGroup objesi
        
    Raises:
        json.JSONDecodeError: JSON geçersizse
        ValueError: Gerekli alanlar eksikse
    """
    import json
    data = json.loads(json_str)
    return RuleGroup.from_dict(data)


def evaluate_strategy(df: pd.DataFrame, rule_group: RuleGroup) -> bool:
    """
    Stratejiyi DataFrame üzerinde değerlendir.
    
    Args:
        df: OHLCV + indikatörler içeren DataFrame
        rule_group: Değerlendirilecek RuleGroup
        
    Returns:
        bool: Strateji koşulları sağlanıyorsa True, değilse False
    """
    return rule_group.evaluate(df)


# ============================================================================
# ÖRNEK KULLANIM
# ============================================================================

if __name__ == "__main__":
    # Örnek JSON
    example_json = """
    {
        "logic": "AND",
        "conditions": [
            {
                "indicator": "RSI_14",
                "operator": "<",
                "value": 30
            },
            {
                "indicator": "MACD_12_26_9",
                "operator": ">",
                "value": "MACD_Signal_12_26_9"
            }
        ]
    }
    """

    # JSON'dan RuleGroup oluştur
    rule_group = parse_condition_json(example_json)
    print("[OK] RuleGroup olusturuldu:")
    print(f"   Logic: {rule_group.logic}")
    print(f"   Conditions: {len(rule_group.conditions)}")

    # Dictionary'e çevir
    rule_dict = rule_group.to_dict()
    print(f"\n[OK] Dictionary'e çevrildi:")
    print(f"   {rule_dict}")

    # Test DataFrame oluştur
    test_df = pd.DataFrame({
        'RSI_14': [25, 28, 30, 35, 40],
        'MACD_12_26_9': [0.5, 0.6, 0.7, 0.8, 0.9],
        'MACD_Signal_12_26_9': [0.4, 0.5, 0.6, 0.7, 0.8]
    })

    # Stratejiyi değerlendir
    result = evaluate_strategy(test_df, rule_group)
    print(f"\n[OK] Strateji sonucu: {result}")
    print(f"   Son mum: RSI={test_df['RSI_14'].iloc[-1]}, MACD={test_df['MACD_12_26_9'].iloc[-1]}, Signal={test_df['MACD_Signal_12_26_9'].iloc[-1]}")
    print(f"   Kosul 1: RSI < 30 -> {test_df['RSI_14'].iloc[-1]} < 30 = {test_df['RSI_14'].iloc[-1] < 30}")
    print(f"   Kosul 2: MACD > Signal -> {test_df['MACD_12_26_9'].iloc[-1]} > {test_df['MACD_Signal_12_26_9'].iloc[-1]} = {test_df['MACD_12_26_9'].iloc[-1] > test_df['MACD_Signal_12_26_9'].iloc[-1]}")
