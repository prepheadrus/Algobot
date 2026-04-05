"""
Strategy Manager - Strateji Yönetim Sistemi (OTO-KEŞİF)

Yeni mimari: Plug-and-Play oto-keşif sistemi.
- strategy/ klasöründeki .py dosyalarını otomatik tarar
- strategy/custom/ klasöründeki kullanıcı stratejilerini bulur
- BaseStrategy'den türetilen tüm sınıfları otomatik yükler
- Hatalı dosyaları atlar (sistem çökmez)
"""

from strategy.base import BaseStrategy
from strategy.builder.executor import StrategyExecutor
from core.logger import logger
from pathlib import Path
import json
import importlib
import inspect


class StrategyManager:
    """
    Sistemdeki tüm bot (strateji) setlerini bu yönetici üzerinden çağırırız.
    Oto-keşif ile sabit stratejiler + kullanıcı stratejileri.
    """

    # Sabit stratejiler (manuel import - backward compatibility)
    FIXED_STRATEGIES = {
        # Not: Bunlar hala manuel import, oto-keşif bunların ÜSTÜNE ekler
    }

    # Dinamik JSON stratejiler (runtime yüklenir)
    DYNAMIC_STRATEGIES = {}

    # StrategyExecutor instances (canlı sinyal üretimi için)
    STRATEGY_EXECUTORS = {}

    # Strateji klasörleri
    STRATEGY_DIR = Path("strategy")
    CUSTOM_STRATEGY_DIR = Path("strategy/custom")
    JSON_STRATEGIES_DIR = Path("artifacts/strategies")

    # Manuel import edilen stratejiler (backward compatibility)
    MANUALLY_IMPORTED = {}

    @classmethod
    def _import_manual_strategies(cls):
        """
        Manuel import edilen stratejileri yükle (backward compatibility).
        Bu fonksiyon sadece ilk başlatmada çalışır.
        """
        if cls.MANUALLY_IMPORTED:
            return  # Zaten yüklendi
        
        try:
            # Manuel import edilen stratejiler (eski sistem)
            from strategy.trend_master import TrendMasterPro
            from strategy.scalper_ninja import ScalperNinja
            from strategy.adaptive_koncorde import AdaptiveKoncordeX
            from strategy.golden_combo import GoldenCombo
            from strategy.divergence_hunter import DivergenceHunter
            from strategy.knn_quant import KNNQuantATRShield
            
            cls.MANUALLY_IMPORTED = {
                "trend_master": TrendMasterPro(),
                "scalper_ninja": ScalperNinja(),
                "adaptive_koncorde": AdaptiveKoncordeX(),
                "golden_combo": GoldenCombo(),
                "divergence_hunter": DivergenceHunter(),
                "knn_quant_atr": KNNQuantATRShield()
            }
            
            logger.info(f"✅ {len(cls.MANUALLY_IMPORTED)} manuel strateji yüklendi (backward compatibility)")
            
        except Exception as e:
            logger.error(f"❌ Manuel strateji yükleme hatası: {e}")
            cls.MANUALLY_IMPORTED = {}

    @classmethod
    def _discover_strategies_in_folder(cls, folder: Path, prefix: str = "") -> dict:
        """
        Bir klasördeki tüm .py dosyalarını tara ve BaseStrategy'den türetilen sınıfları bul.
        
        Args:
            folder: Tara nacak klasör
            prefix: Modül ön eki (örn: "strategy.custom.")
            
        Returns:
            dict: {strategy_id: strategy_instance}
        """
        discovered = {}
        
        if not folder.exists():
            logger.debug(f"📁 Klasör bulunamadı: {folder}")
            return discovered
        
        logger.info(f"🔍 {folder} klasöründe strateji aranıyor...")
        
        # .py dosyalarını bul
        py_files = list(folder.glob("*.py"))
        
        for py_file in py_files:
            # base.py ve manager.py'yi atla
            if py_file.stem in ["base", "manager", "__init__"]:
                continue
            
            try:
                # Modül adını oluştur
                if prefix:
                    module_name = f"{prefix}{py_file.stem}"
                else:
                    module_name = py_file.stem
                
                # Modülü import et
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    logger.warning(f"⚠️ Modül yüklenemedi: {py_file.name}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Modüldeki tüm sınıfları kontrol et
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # BaseStrategy'den türetilmiş mi?
                    if issubclass(obj, BaseStrategy) and obj != BaseStrategy:
                        # MANUEL STRATEJİLERİ ATLA (duplicate önleme)
                        # Eğer bu sınıf MANUALLY_IMPORTED'da varsa atla
                        manual_ids = [cls.MANUALLY_IMPORTED[sid].__class__.__name__ for sid in cls.MANUALLY_IMPORTED]
                        if name in manual_ids:
                            logger.debug(f"⏭️ Manuel strateji atlandı: {name} (zaten yüklü)")
                            continue
                        
                        # Sınıf adını strategy_id olarak kullan (küçük harf, alt çizgi)
                        strategy_id = name.lower().replace("strategy", "").strip("_")
                        
                        # Eğer custom klasöründeyse prefix ekle
                        if str(folder) == str(cls.CUSTOM_STRATEGY_DIR):
                            strategy_id = f"custom_{strategy_id}"
                        
                        # Instance oluştur
                        try:
                            instance = obj()
                            discovered[strategy_id] = instance
                            logger.info(f"✅ Strateji bulundu: {strategy_id} ({name})")
                        except Exception as e:
                            logger.warning(f"⚠️ Strateji instance oluşturulamadı: {name} - {e}")
                
            except Exception as e:
                # Hatalı dosyayı atla, sistemi çökertme
                logger.warning(f"⚠️ Strateji dosyası hatası: {py_file.name} - {e}")
                logger.debug(f"Traceback: {e}", exc_info=True)
                continue
        
        return discovered

    @classmethod
    def load_dynamic_strategies(cls):
        """
        artifacts/strategies/ klasöründen JSON stratejileri yükle.
        Her JSON dosyası için StrategyExecutor instance oluşturur.
        """
        cls.DYNAMIC_STRATEGIES.clear()
        cls.STRATEGY_EXECUTORS.clear()

        # Klasör yoksa oluştur
        if not cls.JSON_STRATEGIES_DIR.exists():
            cls.JSON_STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("📁 Strateji klasörü oluşturuldu: artifacts/strategies/")
            return

        # JSON dosyalarını tara
        json_files = list(cls.JSON_STRATEGIES_DIR.glob("*.json"))

        if not json_files:
            logger.info("📭 Kaydedilmiş strateji bulunamadı")
            return

        logger.info(f"📚 {len(json_files)} JSON strateji yükleniyor...")

        for filepath in json_files:
            try:
                # JSON'u yükle
                with open(filepath, 'r', encoding='utf-8') as f:
                    strategy_data = json.load(f)

                strategy_name = strategy_data.get('name', 'Bilinmeyen')
                strategy_id = f"dynamic_{filepath.stem}"  # Örn: dynamic_rsi_macd_20260306_143022

                # StrategyExecutor oluştur
                executor = StrategyExecutor(str(filepath))

                # Listeye ekle
                cls.DYNAMIC_STRATEGIES[strategy_id] = {
                    'name': strategy_name,
                    'description': strategy_data.get('description', ''),
                    'filename': filepath.name,
                    'executor': executor,
                    'data': strategy_data
                }

                cls.STRATEGY_EXECUTORS[strategy_id] = executor

                logger.info(f"✅ JSON strateji yüklendi: {strategy_name} ({filepath.name})")

            except Exception as e:
                logger.error(f"❌ JSON strateji yüklenemedi: {filepath.name} - {e}")

        logger.info(f"✅ {len(cls.DYNAMIC_STRATEGIES)} JSON strateji yüklendi")

    @classmethod
    def get_all_strategies(cls) -> dict:
        """
        TÜM stratejileri döndür (manuel + oto-keşif + JSON).
        
        Returns:
            dict: {strategy_id: strategy_dict}
        """
        # 1. Manuel import edilen stratejileri yükle (backward compatibility)
        cls._import_manual_strategies()
        
        # 2. Oto-keşif ile strategy/ klasöründeki stratejileri bul
        auto_discovered = cls._discover_strategies_in_folder(cls.STRATEGY_DIR)
        
        # 3. Oto-keşif ile strategy/custom/ klasöründeki stratejileri bul
        custom_discovered = cls._discover_strategies_in_folder(cls.CUSTOM_STRATEGY_DIR, prefix="custom.")
        
        # 4. Tüm stratejileri birleştir
        all_strategies = {}
        
        # Manuel stratejiler
        for strategy_id, instance in cls.MANUALLY_IMPORTED.items():
            # timeframe'i al (method veya attribute olabilir)
            timeframe = instance.timeframe() if callable(getattr(instance, 'timeframe', None)) else getattr(instance, 'timeframe', '1m')
            # name'i al (method veya attribute olabilir)
            name = instance.name() if callable(getattr(instance, 'name', None)) else getattr(instance, 'name', strategy_id)
            # description'ı al (method veya attribute olabilir)
            description = instance.description() if callable(getattr(instance, 'description', None)) else getattr(instance, 'description', '')
            
            all_strategies[strategy_id] = {
                'id': strategy_id,
                'name': name,
                'description': description,
                'timeframe': timeframe,
                'type': 'builtin',
                'instance': instance
            }
        
        # Oto-keşif edilen stratejiler
        for strategy_id, instance in auto_discovered.items():
            # Manuel stratejilerin üzerine yazma (backward compatibility)
            if strategy_id not in all_strategies:
                # timeframe'i al (method veya attribute olabilir)
                timeframe = instance.timeframe() if callable(getattr(instance, 'timeframe', None)) else getattr(instance, 'timeframe', '1m')
                # name'i al (method veya attribute olabilir)
                name = instance.name() if callable(getattr(instance, 'name', None)) else getattr(instance, 'name', strategy_id)
                # description'ı al (method veya attribute olabilir)
                description = instance.description() if callable(getattr(instance, 'description', None)) else getattr(instance, 'description', '')
                
                all_strategies[strategy_id] = {
                    'id': strategy_id,
                    'name': name,
                    'description': description,
                    'timeframe': timeframe,
                    'type': 'auto_discovered',
                    'instance': instance
                }
                logger.info(f"🆕 Oto-keşif strateji eklendi: {strategy_id}")
        
        # Custom stratejiler
        for strategy_id, instance in custom_discovered.items():
            # timeframe'i al (method veya attribute olabilir)
            timeframe = instance.timeframe() if callable(getattr(instance, 'timeframe', None)) else getattr(instance, 'timeframe', '1m')
            # name'i al (method veya attribute olabilir)
            name = instance.name() if callable(getattr(instance, 'name', None)) else getattr(instance, 'name', strategy_id)
            # description'ı al (method veya attribute olabilir)
            description = instance.description() if callable(getattr(instance, 'description', None)) else getattr(instance, 'description', '')
            
            all_strategies[strategy_id] = {
                'id': strategy_id,
                'name': name,
                'description': description,
                'timeframe': timeframe,
                'type': 'custom',
                'instance': instance
            }
            logger.info(f"🎨 Custom strateji eklendi: {strategy_id}")
        
        # JSON stratejiler
        for strategy_id, data in cls.DYNAMIC_STRATEGIES.items():
            all_strategies[strategy_id] = {
                'id': strategy_id,
                'name': data['name'],
                'description': data['description'],
                'timeframe': data['data'].get('timeframe', '1m'),
                'type': 'json',
                'executor': data['executor']
            }
        
        logger.info(f"📊 Toplam {len(all_strategies)} strateji bulundu")
        
        return all_strategies

    @classmethod
    def get_strategy(cls, strategy_id: str):
        """
        Belirli bir stratejiyi al.
        
        Args:
            strategy_id: Strateji ID
            
        Returns:
            Strategy instance veya None
        """
        # Manuel stratejilerde ara
        if strategy_id in cls.MANUALLY_IMPORTED:
            return cls.MANUALLY_IMPORTED[strategy_id]
        
        # Oto-keşif edilen stratejilerde ara
        all_strategies = cls.get_all_strategies()
        if strategy_id in all_strategies:
            return all_strategies[strategy_id].get('instance')
        
        # JSON stratejilerde ara
        if strategy_id in cls.DYNAMIC_STRATEGIES:
            return cls.DYNAMIC_STRATEGIES[strategy_id].get('executor')
        
        return None

    @classmethod
    def reload(cls):
        """
        Tüm stratejileri yeniden yükle (hot-reload).
        """
        logger.info("🔄 Stratejiler yeniden yükleniyor...")
        cls.DYNAMIC_STRATEGIES.clear()
        cls.STRATEGY_EXECUTORS.clear()
        cls.load_dynamic_strategies()
        logger.info("✅ Stratejiler yeniden yüklendi")
