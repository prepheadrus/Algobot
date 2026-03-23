"""
Auto-Grid Generator - Zero-Touch Parametre Uzayı

Stratejilerdeki DEFAULT_PARAMS sözlüğünü dinamik olarak okuyup,
her parametreyi %30 esnetme payı (Flex Ratio) ile 3'lü arama
uzaylarına dönüştürür.

Manuel PARAM_GRID tanımlama zorunluluğunu ortadan kaldırır.

Usage:
    from core.auto_grid import AutoGridGenerator
    
    generator = AutoGridGenerator()
    
    # Strateji instance'ından otomatik param grid oluştur
    param_grid = generator.generate_from_strategy(strategy_instance)
    
    # Veya manuel DEFAULT_PARAMS'ten
    param_grid = generator.generate_from_dict({
        'rsi_period': 14,
        'ema_fast': 20,
        'ema_slow': 50
    })
"""

from typing import Dict, Any, List, Union
from core.logger import logger
import numpy as np


class AutoGridGenerator:
    """
    Zero-Touch Parametre Uzayı Oluşturucu.
    
    Her parametreyi otomatik olarak %30 esnetir ve
    3 noktalı arama uzayı oluşturur.
    """
    
    # Flex Ratio: Her parametreyi ne kadar esneteceğiz?
    FLEX_RATIO = 0.30  # %30
    
    # Minimum step size (çok küçük parametreler için)
    MIN_STEP = 1
    
    def __init__(self):
        logger.info("🔧 [AUTO-GRID] Generator initialized")
    
    def generate_from_strategy(self, strategy_instance) -> Dict[str, List[Any]]:
        """
        Strateji instance'ından otomatik param grid oluştur.
        
        Args:
            strategy_instance: Strateji sınıfı (DEFAULT_PARAMS attribute'ı olmalı)
        
        Returns:
            Param grid (Optuna study.suggest_* formatına uygun)
        """
        if not hasattr(strategy_instance, 'DEFAULT_PARAMS'):
            logger.warning(f"⚠️ [AUTO-GRID] {strategy_instance.__class__.__name__} DEFAULT_PARAMS yok")
            return {}
        
        return self.generate_from_dict(strategy_instance.DEFAULT_PARAMS)
    
    def generate_from_dict(self, params: Dict[str, Any]) -> Dict[str, List[Any]]:
        """
        Manuel DEFAULT_PARAMS sözlüğünden param grid oluştur.
        
        Args:
            params: Parametre sözlüğü (örn: {'rsi_period': 14, 'ema_fast': 20})
        
        Returns:
            Param grid (her parametre için 3 değer)
        """
        param_grid = {}
        
        for param_name, default_value in params.items():
            # Sadece numeric parametreleri işle
            if isinstance(default_value, (int, float)):
                param_grid[param_name] = self._generate_range(default_value)
                logger.debug(f"📊 [AUTO-GRID] {param_name}: {default_value} → {param_grid[param_name]}")
            else:
                # Non-numeric parametreleri sabit tut
                logger.debug(f"⏭️ [AUTO-GRID] {param_name} numeric değil, atlandı")
        
        logger.info(f"✅ [AUTO-GRID] {len(param_grid)} parametre için grid oluşturuldu")
        return param_grid
    
    def _generate_range(self, default_value: Union[int, float]) -> List[Union[int, float]]:
        """
        Tek bir parametre için 3 noktalı arama uzayı oluştur.
        
        Formula:
            low = default_value * (1 - FLEX_RATIO)
            mid = default_value
            high = default_value * (1 + FLEX_RATIO)
        
        Args:
            default_value: Varsayılan değer
        
        Returns:
            [low, mid, high] listesi
        """
        # Integer ise
        if isinstance(default_value, int):
            step = max(int(default_value * self.FLEX_RATIO), self.MIN_STEP)
            
            low = default_value - step
            mid = default_value
            high = default_value + step
            
            # Negatif olmasın
            low = max(low, 1)
            
            return [low, mid, high]
        
        # Float ise
        else:
            step = default_value * self.FLEX_RATIO
            
            low = default_value - step
            mid = default_value
            high = default_value + step
            
            # Negatif olmasın
            low = max(low, 0.01)
            
            return [round(low, 4), round(mid, 4), round(high, 4)]
    
    def get_optuna_suggestions(self, param_grid: Dict[str, List[Any]]) -> Dict[str, str]:
        """
        Param grid'i Optuna suggest_* formatına çevir.
        
        Args:
            param_grid: Param grid
        
        Returns:
            Optuna suggest formatı (örn: {'rsi_period': 'suggest_int'})
        """
        suggestions = {}
        
        for param_name, values in param_grid.items():
            if len(values) == 3:
                low, mid, high = values
                
                # Integer mi float mı?
                if isinstance(low, int):
                    suggestions[param_name] = {
                        'type': 'int',
                        'low': low,
                        'high': high
                    }
                else:
                    suggestions[param_name] = {
                        'type': 'float',
                        'low': low,
                        'high': high
                    }
        
        return suggestions


# Singleton instance
auto_grid = AutoGridGenerator()

# Export
__all__ = ['AutoGridGenerator', 'auto_grid']
