import pytest
import math
from typing import Optional

from core.risk.risk_engine import RiskEngine

class MockConfig:
    max_risk_per_trade = 0.01  # %1 risk
    max_leverage = 10.0
    default_leverage = 1.0
    max_open_positions = 5
    kill_switch_enabled = False
    max_consecutive_losses = 3
    max_daily_loss = 0.05
    max_drawdown = 0.10

@pytest.fixture
def risk_engine():
    engine = RiskEngine()
    engine.config = MockConfig()
    return engine

# =====================================================================
# calculate_dynamic_leverage TESTS
# =====================================================================

def test_dynamic_leverage_veto(risk_engine):
    """Confidence < 0.50 durumunda veto (0.0x) edilmeli."""
    lev = risk_engine.calculate_dynamic_leverage(confidence_score=0.49)
    assert lev == 0.0

def test_dynamic_leverage_low_confidence(risk_engine):
    """0.50 <= Confidence < 0.65 durumunda min(3.0, max_leverage) olmalı."""
    lev = risk_engine.calculate_dynamic_leverage(confidence_score=0.55)
    assert lev == 3.0

def test_dynamic_leverage_medium_confidence(risk_engine):
    """0.65 <= Confidence <= 0.80 durumunda min(5.0, max_leverage) olmalı."""
    lev = risk_engine.calculate_dynamic_leverage(confidence_score=0.70)
    assert lev == 5.0

def test_dynamic_leverage_high_confidence(risk_engine):
    """Confidence > 0.80 durumunda min(10.0, max_leverage) olmalı."""
    lev = risk_engine.calculate_dynamic_leverage(confidence_score=0.85)
    assert lev == 10.0

def test_dynamic_leverage_fallback(risk_engine):
    """Confidence None ise default_leverage (fallback) dönmeli."""
    lev = risk_engine.calculate_dynamic_leverage(confidence_score=None)
    assert lev == 1.0

def test_dynamic_leverage_respects_max_cap(risk_engine):
    """Dynamic leverage verilen max_leverage sınırını geçmemeli."""
    lev = risk_engine.calculate_dynamic_leverage(confidence_score=0.90, max_leverage=7.0)
    assert lev == 7.0

# =====================================================================
# calculate_position_size TESTS
# =====================================================================

def test_position_size_zero_distance_shield(risk_engine):
    """sl_distance == 0 olduğunda sistem crash olmamalı, 0.0 dönmeli."""
    size = risk_engine.calculate_position_size(
        account_balance=1000.0,
        entry_price=50000.0,
        stop_loss_price=50000.0, # Zero distance!
        risk_percentage=1.0,
        ml_confidence=0.85
    )
    assert size == 0.0

def test_position_size_normal_calculation(risk_engine):
    """
    Normal koşullar altında doğru coin miktarı hesaplanmalı.
    Balance: $1000, Risk: %1 ($10)
    Entry: $50,000, SL: $49,000 -> SL Distance: $1,000
    Raw Size (Coin) = $10 / $1000 = 0.01 BTC
    Max Notional = 1000 * 10x (confidence=0.85) = 10,000
    Raw Notional = 0.01 * 50,000 = 500
    500 < 10000, no clipping needed. Return 0.01
    """
    size = risk_engine.calculate_position_size(
        account_balance=1000.0,
        entry_price=50000.0,
        stop_loss_price=49000.0,
        risk_percentage=1.0,
        ml_confidence=0.85
    )
    assert math.isclose(size, 0.01, rel_tol=1e-5)

def test_position_size_clipping_due_to_veto(risk_engine):
    """Confidence veto eşiğindeyse (0.0x), pozisyon boyutu 0 dönmeli."""
    size = risk_engine.calculate_position_size(
        account_balance=1000.0,
        entry_price=50000.0,
        stop_loss_price=49000.0,
        risk_percentage=1.0,
        ml_confidence=0.45 # VETO
    )
    assert size == 0.0

def test_position_size_clipping_due_to_max_notional(risk_engine):
    """
    Büyük risk alındığında, dinamik kaldıraca bağlı notional limiti devreye girip boyutu kırpmalı.
    Balance: $1000
    Risk: %10 (Bilinçli zorlama fallback, test için config ezildi) -> Ama RiskEngine <=5.0 kalkanına takılıp 1.0 olacak.
    Yani Risk Amount = $10
    SL: Çok dar. Entry: 50,000, SL: 49,990 -> SL Distance = $10
    Raw Size = $10 / $10 = 1.0 BTC
    Raw Notional = 1.0 * 50,000 = 50,000 USD
    Confidence: 0.60 -> Max Lev = 3.0x -> Max Notional = 1000 * 3.0 = 3000 USD
    Clipping devrede: Size = 3000 / 50000 = 0.06 BTC
    """
    size = risk_engine.calculate_position_size(
        account_balance=1000.0,
        entry_price=50000.0,
        stop_loss_price=49990.0,
        risk_percentage=1.0,
        ml_confidence=0.60 # max 3x
    )

    expected_clipped_size = 3000 / 50000.0
    assert math.isclose(size, expected_clipped_size, rel_tol=1e-5)

def test_position_size_without_ml_confidence(risk_engine):
    """
    ml_confidence = None olduğunda default_leverage(1x) kullanılmalı.
    Balance: 1000, Risk: %1 ($10)
    Entry: 50000, SL: 49500 -> SL Distance = 500
    Raw Size: 10 / 500 = 0.02 BTC
    Raw Notional: 0.02 * 50000 = 1000
    Max Notional: 1000 * 1.0 (fallback) = 1000
    Sınırda, no clipping. Return 0.02
    """
    size = risk_engine.calculate_position_size(
        account_balance=1000.0,
        entry_price=50000.0,
        stop_loss_price=49500.0,
        risk_percentage=1.0,
        ml_confidence=None # None fallback -> default leverage 1x
    )
    assert math.isclose(size, 0.02, rel_tol=1e-5)
