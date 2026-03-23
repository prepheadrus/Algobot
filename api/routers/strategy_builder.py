"""
Strategy Builder API Endpoints

FastAPI router for No-Code Strategy Builder operations.
Frontend ile Backend arasındaki köprü.

Endpoints:
- POST /save: Strateji kaydetme
- GET /list: Strateji listeleme
- POST /test: Hızlı test (quick backtest)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import os

# Strategy Builder modüllerinden import
from strategy.builder.executor import StrategyExecutor
from strategy.builder.condition_parser import RuleGroup, parse_condition_json
from strategy.builder.json_validator import StrategyValidator

# Bot modüllerinden import
from data.indicators import StrategyIndicators
from core.logger import logger
from strategy.manager import StrategyManager

# Router oluştur
router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy Builder"])


# ============================================================================
# PYDANTIC MODELLERİ (Request/Response Şemaları)
# ============================================================================

class StrategySaveRequest(BaseModel):
    """Strateji kaydetme isteği"""
    name: str = Field(..., description="Strateji adı", min_length=1, max_length=100)
    description: str = Field(default="", description="Strateji açıklaması", max_length=500)
    indicators: List[Dict[str, Any]] = Field(..., description="İndikatör listesi")
    conditions: Dict[str, Any] = Field(..., description="LONG ve SHORT koşulları")
    risk: Optional[Dict[str, float]] = Field(default=None, description="Risk parametreleri")


class StrategySaveResponse(BaseModel):
    """Strateji kaydetme yanıtı"""
    status: str = Field(..., description="Durum (success/error)")
    message: str = Field(..., description="Mesaj")
    filename: str = Field(..., description="Kaydedilen dosya adı")
    filepath: str = Field(..., description="Tam dosya yolu")


class StrategyInfo(BaseModel):
    """Strateji bilgisi (listeleme için)"""
    filename: str = Field(..., description="Dosya adı")
    name: str = Field(..., description="Strateji adı")
    description: str = Field(default="", description="Strateji açıklaması")
    indicators_count: int = Field(..., description="İndikatör sayısı")
    created_at: str = Field(..., description="Oluşturulma zamanı")


class StrategyListResponse(BaseModel):
    """Strateji listeleme yanıtı"""
    status: str = Field(..., description="Durum")
    count: int = Field(..., description="Strateji sayısı")
    strategies: List[StrategyInfo] = Field(..., description="Strateji listesi")


class StrategyTestRequest(BaseModel):
    """Strateji test isteği"""
    strategy: Dict[str, Any] = Field(..., description="Strateji JSON")
    symbol: str = Field(..., description="Sembol (örn: BTC/USDT)")
    timeframe: str = Field(default="1h", description="Zaman dilimi")
    days: int = Field(default=30, description="Test edilecek gün sayısı")


class StrategyTestResponse(BaseModel):
    """Strateji test yanıtı"""
    status: str = Field(..., description="Durum")
    message: str = Field(..., description="Mesaj")
    metrics: Dict[str, Any] = Field(..., description="Test metrikleri")


# ============================================================================
# ENDPOINT'LER
# ============================================================================

@router.post("/save", response_model=StrategySaveResponse)
async def save_strategy(request: StrategySaveRequest):
    """
    Kullanıcıdan gelen JSON stratejiyi kaydet.
    
    Args:
        request: StrategySaveRequest (name, description, indicators, conditions, risk)
        
    Returns:
        StrategySaveResponse: Kayıt durumu ve dosya bilgisi
        
    Raises:
        HTTPException: JSON geçersizse veya kayıt başarısızsa
    """
    try:
        # 1. JSON validasyonu
        logger.info(f"📥 Strateji kaydetme isteği: {request.name}")
        
        # Strateji JSON'u oluştur
        strategy_json = {
            "name": request.name,
            "description": request.description,
            "indicators": request.indicators,
            "conditions": request.conditions,
            "risk": request.risk or {
                "stop_loss_atr_multiplier": 2.0,
                "take_profit_atr_multiplier": 4.0,
                "max_risk_percent": 2.0
            }
        }
        
        # Condition validation
        try:
            if "LONG" in strategy_json["conditions"]:
                long_data = strategy_json["conditions"]["LONG"]
                if isinstance(long_data, dict):
                    RuleGroup.from_dict(long_data)
            
            if "SHORT" in strategy_json["conditions"]:
                short_data = strategy_json["conditions"]["SHORT"]
                if isinstance(short_data, dict):
                    RuleGroup.from_dict(short_data)
                    
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Koşul validasyonu başarısız: {str(e)}"
            )
        
        # 2. Dosya yolunu oluştur
        strategies_dir = Path("artifacts/strategies")
        strategies_dir.mkdir(parents=True, exist_ok=True)
        
        # Dosya adı: name_YYYYMMDD_HHMMSS.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = request.name.lower().replace(" ", "_").replace("-", "_")
        filename = f"{safe_name}_{timestamp}.json"
        filepath = strategies_dir / filename
        
        # 3. Dosyayı kaydet
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(strategy_json, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Strateji kaydedildi: {filepath}")

        # Stratejileri yeniden yükle (Hot Reload)
        try:
            StrategyManager.reload_strategies()
            logger.info("🔄 Stratejiler yeniden yüklendi (Hot Reload).")
        except Exception as e:
            logger.error(f"🔥 Hot Reload hatası: {e}")
            # Bu bir hata olmamalı, sadece loglayalım. API response'u etkilemesin.

        return StrategySaveResponse(
            status="success",
            message=f"Strateji '{request.name}' başarıyla kaydedildi",
            filename=filename,
            filepath=str(filepath)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Strateji kaydetme hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strateji kaydedilemedi: {str(e)}"
        )


@router.get("/list", response_model=StrategyListResponse)
async def list_strategies():
    """
    Kaydedilmiş tüm stratejileri listele.
    
    Returns:
        StrategyListResponse: Strateji listesi
        
    Raises:
        HTTPException: Liste okunamazsa
    """
    try:
        logger.info("📋 Strateji listesi isteniyor")
        
        strategies_dir = Path("artifacts/strategies")
        
        # Klasör yoksa oluştur
        if not strategies_dir.exists():
            strategies_dir.mkdir(parents=True, exist_ok=True)
            return StrategyListResponse(
                status="success",
                message="Henüz strateji yok",
                count=0,
                strategies=[]
            )
        
        # JSON dosyalarını tara
        strategies = []
        for filepath in strategies_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    strategy_data = json.load(f)
                
                # Strateji bilgilerini çıkar
                strategy_info = StrategyInfo(
                    filename=filepath.name,
                    name=strategy_data.get("name", "Bilinmeyen"),
                    description=strategy_data.get("description", ""),
                    indicators_count=len(strategy_data.get("indicators", [])),
                    created_at=datetime.fromtimestamp(filepath.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                )
                strategies.append(strategy_info)
                
            except Exception as e:
                logger.warning(f"⚠️ Dosya okunamadı: {filepath.name} - {e}")
                continue
        
        # Zamana göre sırala (en yeni önce)
        strategies.sort(key=lambda x: x.created_at, reverse=True)
        
        logger.info(f"✅ {len(strategies)} strateji listelendi")
        
        return StrategyListResponse(
            status="success",
            count=len(strategies),
            strategies=strategies
        )
        
    except Exception as e:
        logger.error(f"❌ Strateji listeleme hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stratejiler listelenemedi: {str(e)}"
        )


@router.post("/test", response_model=StrategyTestResponse)
async def test_strategy(request: StrategyTestRequest):
    """
    Stratejiyi hızlı test et (Quick Backtest).
    
    Args:
        request: StrategyTestRequest (strategy, symbol, timeframe, days)
        
    Returns:
        StrategyTestResponse: Test metrikleri
        
    Raises:
        HTTPException: Test başarısızsa
    """
    try:
        logger.info(f"🧪 Strateji testi isteniyor: {request.symbol} ({request.timeframe})")
        
        # 1. Geçici JSON dosyası oluştur
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(request.strategy, f, indent=2, ensure_ascii=False)
            temp_json_path = f.name
        
        try:
            # 2. StrategyExecutor'ı başlat
            executor = StrategyExecutor(temp_json_path)
            
            # 3. Test DataFrame oluştur (simülasyon)
            # Gerçek implementasyonda: core/exchange.py'den veri çekilecek
            # Şimdilik simülasyon yapıyoruz
            import numpy as np
            
            # Son 30 gün için saatlik veri (30 * 24 = 720 satır)
            n_rows = request.days * 24 if request.timeframe == "1h" else request.days * 4  # 4h için
            
            import pandas as pd
            np.random.seed(42)
            
            # Random walk fiyat simülasyonu
            close_prices = 50000 + np.cumsum(np.random.randn(n_rows) * 100)
            high_prices = close_prices + np.abs(np.random.randn(n_rows)) * 50
            low_prices = close_prices - np.abs(np.random.randn(n_rows)) * 50
            open_prices = close_prices + np.random.randn(n_rows) * 50
            volumes = np.random.randint(100, 10000, n_rows)
            
            test_df = pd.DataFrame({
                'open': open_prices,
                'high': high_prices,
                'low': low_prices,
                'close': close_prices,
                'volume': volumes
            })
            
            # 4. Veriyi hazırla (indikatörleri hesapla)
            prepared_df = executor.prepare_data(test_df)
            
            # 5. Sinyalleri üret
            long_count = 0
            short_count = 0
            hold_count = 0
            
            for i in range(len(prepared_df)):
                signal = executor.generate_signal(prepared_df.iloc[:i+1])
                if signal == 2:
                    long_count += 1
                elif signal == 0:
                    short_count += 1
                else:
                    hold_count += 1
            
            # 6. Metrikleri oluştur
            total_signals = long_count + short_count
            metrics = {
                "total_candles": len(prepared_df),
                "total_signals": total_signals,
                "long_signals": long_count,
                "short_signals": short_count,
                "hold_signals": hold_count,
                "signal_ratio": f"{(total_signals / len(prepared_df) * 100):.2f}%" if len(prepared_df) > 0 else "0%",
                "indicators_calculated": list([col for col in prepared_df.columns if col not in test_df.columns]),
                "strategy_info": executor.get_strategy_info()
            }
            
            logger.info(f"✅ Test tamamlandı: {total_signals} sinyal üretildi")
            
            return StrategyTestResponse(
                status="success",
                message=f"Strateji testi başarılı: {request.symbol} ({request.timeframe})",
                metrics=metrics
            )
            
        finally:
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_json_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"❌ Strateji test hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strateji testi başarısız: {str(e)}"
        )


# ============================================================================
# YARDIMCI ENDPOINT (Opsiyonel)
# ============================================================================

@router.get("/info/{filename}")
async def get_strategy_info(filename: str):
    """
    Belirli bir stratejinin detaylı bilgilerini al.
    
    Args:
        filename: Dosya adı (örn: rsi_macd_20260306_143022.json)
        
    Returns:
        Dict: Strateji bilgileri
    """
    try:
        filepath = Path("artifacts/strategies") / filename
        
        if not filepath.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strateji dosyası bulunamadı: {filename}"
            )
        
        with open(filepath, 'r', encoding='utf-8') as f:
            strategy_data = json.load(f)
        
        return {
            "status": "success",
            "filename": filename,
            "data": strategy_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Strateji bilgisi okuma hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strateji bilgisi okunamadı: {str(e)}"
        )


@router.delete("/delete/{filename}")
async def delete_strategy(filename: str):
    """
    Strateji dosyasını sil.
    
    Args:
        filename: Dosya adı
        
    Returns:
        Dict: Silme durumu
    """
    try:
        filepath = Path("artifacts/strategies") / filename
        
        if not filepath.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strateji dosyası bulunamadı: {filename}"
            )
        
        filepath.unlink()
        logger.info(f"✅ Strateji silindi: {filename}")
        
        return {
            "status": "success",
            "message": f"Strateji '{filename}' silindi"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Strateji silme hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Strateji silinemedi: {str(e)}"
        )
