"""
JSON Validator - Strateji JSON validasyonu
"""

import json
from typing import Dict, Any, List, Tuple


class StrategyValidator:
    """
    Strateji JSON'ını validate eder.
    """
    
    VALID_OPERATORS = ['<', '>', '=', '<=', '>=']
    VALID_LOGIC = ['AND', 'OR']
    VALID_SIDES = ['long', 'short']
    
    # İndikatör tipleri ve gerekli parametreler
    INDICATOR_REQUIREMENTS = {
        'EMA': ['length'],
        'SMA': ['length'],
        'RSI': ['length'],
        'MACD': ['fast', 'slow', 'signal'],
        'Stochastic': ['k', 'd'],
        'ATR': ['period'],
        'Bollinger': ['length', 'std'],
        'Supertrend': ['multiplier', 'period'],
        'MFI': ['period'],
        'OBV': [],
        'VWAP': []
    }
    
    @classmethod
    def validate(cls, strategy: Dict) -> Tuple[bool, List[str]]:
        """
        Strateji JSON'ını validate eder

        Args:
            strategy: Strateji dictionary

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 1. Temel alanlar kontrolü (conditions opsiyonel - executor default ekler)
        required_fields = ['name', 'indicators']
        for field in required_fields:
            if field not in strategy:
                errors.append(f"Eksik alan: {field}")

        if errors:
            return False, errors

        # 2. İndikatörler boş olamaz
        if not strategy.get('indicators'):
            errors.append("En az bir indikatör eklenmeli")

        # 3. İndikatörleri validate et
        indicator_errors = cls._validate_indicators(strategy['indicators'])
        errors.extend(indicator_errors)

        # 4. Koşulları validate et (varsa - yoksa executor default ekler)
        if 'conditions' in strategy:
            condition_errors = cls._validate_conditions(strategy['conditions'], strategy['indicators'])
            errors.extend(condition_errors)

        # 5. Risk parametrelerini validate et
        if 'risk' in strategy:
            risk_errors = cls._validate_risk(strategy['risk'])
            errors.extend(risk_errors)

        return len(errors) == 0, errors
    
    @classmethod
    def _validate_indicators(cls, indicators: List[Dict]) -> List[str]:
        """İndikatörleri validate eder"""
        errors = []
        seen_ids = set()
        
        for ind in indicators:
            # ID kontrolü
            if 'id' not in ind:
                errors.append("İndikatör ID'si eksik")
            elif ind['id'] in seen_ids:
                errors.append(f"Tekrar eden ID: {ind['id']}")
            else:
                seen_ids.add(ind['id'])
            
            # Tip kontrolü
            if 'type' not in ind:
                errors.append("İndikatör tipi eksik")
            elif ind['type'] not in cls.INDICATOR_REQUIREMENTS:
                errors.append(f"Bilinmeyen indikatör: {ind['type']}")
            else:
                # Parametre kontrolü
                required_params = cls.INDICATOR_REQUIREMENTS[ind['type']]
                params = ind.get('parameters', {})
                
                for param in required_params:
                    if param not in params:
                        errors.append(f"{ind['type']} için eksik parametre: {param}")
        
        return errors
    
    @classmethod
    def _validate_conditions(cls, conditions: Dict, indicators: List[Dict]) -> List[str]:
        """Koşulları validate eder (case-insensitive, safe get)"""
        errors = []
        indicator_ids = {ind['id'] for ind in indicators}

        # Safe get - eğer conditions None veya boş ise hata ver
        if not conditions:
            return ["conditions alanı boş veya eksik"]

        # Case-insensitive kontrol için anahtarları normalize et
        normalized_conditions = {}
        for key, value in conditions.items():
            normalized_conditions[key.lower()] = value

        for side in cls.VALID_SIDES:  # 'long', 'short'
            if side not in normalized_conditions:
                errors.append(f"{side} koşulu eksik")
                continue

            side_cond = normalized_conditions[side]

            # None kontrolü
            if not side_cond:
                errors.append(f"{side} koşulu boş")
                continue

            # Logic kontrolü
            logic_val = side_cond.get('logic', '')
            if logic_val and logic_val.upper() not in cls.VALID_LOGIC:
                errors.append(f"Geçersiz logic: {side_cond.get('logic')}")

            # Rules kontrolü
            if 'rules' not in side_cond:
                errors.append(f"{side} için rules eksik")
                continue

            for rule in side_cond['rules']:
                # Gerekli alanlar
                for field in ['indicator', 'operator', 'value']:
                    if field not in rule:
                        errors.append(f"Kuralda eksik alan: {field}")

                # Operatör kontrolü
                if 'operator' in rule and rule['operator'] not in cls.VALID_OPERATORS:
                    errors.append(f"Geçersiz operatör: {rule['operator']}")

                # İndikatör kontrolü
                if 'indicator' in rule and rule['indicator'] not in indicator_ids:
                    errors.append(f"Bilinmeyen indikatör: {rule['indicator']}")

        return errors
    
    @classmethod
    def _validate_risk(cls, risk: Dict) -> List[str]:
        """Risk parametrelerini validate eder"""
        errors = []
        
        if 'stop_loss' in risk:
            sl = risk['stop_loss']
            if isinstance(sl, dict):
                if 'multiplier' in sl:
                    if not (0 < sl['multiplier'] <= 10):
                        errors.append("Stop loss çarpanı 0-10 arasında olmalı")
        
        if 'take_profit' in risk:
            tp = risk['take_profit']
            if isinstance(tp, dict):
                if 'multiplier' in tp:
                    if not (0 < tp['multiplier'] <= 20):
                        errors.append("Take profit çarpanı 0-20 arasında olmalı")
        
        if 'max_risk_percent' in risk:
            if not (0 < risk['max_risk_percent'] <= 10):
                errors.append("Max risk %0-10 arasında olmalı")
        
        return errors
    
    @classmethod
    def validate_file(cls, filepath: str) -> Tuple[bool, List[str]]:
        """
        Dosyadan strateji validate eder
        
        Args:
            filepath: JSON dosya yolu
            
        Returns:
            (is_valid, error_messages)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                strategy = json.load(f)
            return cls.validate(strategy)
        except FileNotFoundError:
            return False, [f"Dosya bulunamadı: {filepath}"]
        except json.JSONDecodeError as e:
            return False, [f"JSON hatası: {str(e)}"]
