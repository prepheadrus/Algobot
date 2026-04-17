from typing import Dict, Any, Optional
import pandas as pd
import json

from core.logger import logger
from strategy.builder.executor import StrategyExecutor
from strategy.builder.executor import StrategyConfig
from strategy.builder.condition_parser import parse_condition_json

class DynamicJSONStrategyAdapter:
    """
    WFOEngine'in beklediği BaseStrategy arayüzünü,
    JSON tabanlı StrategyExecutor ile sarmalayan Adapter sınıfı.
    Disk I/O yerine tamamen in-memory çalışır.
    """
    def __init__(self, strategy_dict: Dict[str, Any] = None):
        self.strategy_dict = strategy_dict if strategy_dict else {}
        self.executor = None
        self._initialize_executor()

    def _initialize_executor(self):
        """Mevcut sözlükten StrategyExecutor'ı disk kullanmadan (in-memory) başlatır."""
        if not self.strategy_dict:
            return

        try:
            self.executor = StrategyExecutor(strategy_dict=self.strategy_dict)
        except Exception as e:
            logger.error(f"❌ [WFO Adapter] In-memory executor oluşturma hatası: {e}")

    def update_params(self, params: Dict[str, Any]):
        """
        WFO'dan gelen grid parametrelerini strateji JSON dict'i içerisine enjekte eder.
        """
        if not self.strategy_dict or "indicators" not in self.strategy_dict:
            return

        import json
        import re

        # 1. Update numeric values in indicators list
        for param_name, param_value in params.items():
            parts = param_name.split("_")
            if len(parts) >= 2:
                ind_name = parts[0]
                param_key = "_".join(parts[1:])
                for ind in self.strategy_dict.get("indicators", []):
                    if ind.get("name") == ind_name:
                        ind[param_key] = param_value

            # Update risk params
            if param_name.startswith("risk_") and "risk" in self.strategy_dict:
                risk_key = param_name.replace("risk_", "")
                self.strategy_dict["risk"][risk_key] = param_value

        # 2. String replace condition variables
        dict_str = json.dumps(self.strategy_dict)

        for ind in self.strategy_dict.get("indicators", []):
            ind_name = ind.get("name")
            if ind_name == "RSI" and "period" in ind:
                dict_str = re.sub(r'RSI_\d+', f'RSI_{ind["period"]}', dict_str)
            elif ind_name == "EMA" and "period" in ind:
                dict_str = re.sub(r'EMA_\d+', f'EMA_{ind["period"]}', dict_str)
            elif ind_name == "SMA" and "period" in ind:
                dict_str = re.sub(r'SMA_\d+', f'SMA_{ind["period"]}', dict_str)
            elif ind_name == "MACD" and all(k in ind for k in ["fast", "slow", "signal"]):
                dict_str = re.sub(r'MACD_\d+_\d+_\d+', f'MACD_{ind["fast"]}_{ind["slow"]}_{ind["signal"]}', dict_str)
                dict_str = re.sub(r'MACD_Signal_\d+_\d+_\d+', f'MACD_Signal_{ind["fast"]}_{ind["slow"]}_{ind["signal"]}', dict_str)
            elif ind_name == "ATR" and "period" in ind:
                dict_str = re.sub(r'ATR_\d+', f'ATR_{ind["period"]}', dict_str)

        self.strategy_dict = json.loads(dict_str)

        # Re-initialize
        self._initialize_executor()
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Tüm DataFrame için sinyalleri üretir.
        """
        if not self.executor or df.empty:
            return pd.Series(0, index=df.index)

        try:
            # prepare_data automatically calculates indicators based on self.executor.config.indicators
            prepared_df = self.executor.prepare_data(df.copy())

            signals = []
            for i in range(len(prepared_df)):
                sig = self.executor.generate_signal(prepared_df.iloc[:i+1])
                signals.append(sig)

            # Convert 2 -> 1 (LONG), 0 -> -1 (SHORT), 1 -> 0 (HOLD) for WFO compatibility
            mapped_signals = pd.Series(signals, index=df.index).map({2: 1, 0: -1, 1: 0})

            return mapped_signals

        except Exception as e:
            logger.error(f"❌ [WFO Adapter] Sinyal hesaplama hatası: {e}")
            return pd.Series(0, index=df.index)
