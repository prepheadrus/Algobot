import pytest
import asyncio
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock

from core.risk.risk_engine import RiskEngine, RiskConfig
from shared.events.event_bus import event_bus, Event

@pytest.fixture
def risk_engine():
    # Geçici test dosyası oluştur
    test_state_file = "tests/test_risk_state.json"
    if os.path.exists(test_state_file):
        os.remove(test_state_file)

    config = RiskConfig(
        max_consecutive_losses=5,
        kill_switch_enabled=True,
        max_daily_loss=0.05
    )

    # Init sırasında _load_state_sync çağrıldığı için doğru path'in patchlenmesi gerekir
    with patch('core.risk.risk_engine.RiskEngine._state_file', test_state_file, create=True):
        engine = RiskEngine(config)
        # Patch init sonrası kalkar diye garanti olması için instance a da yazarız
        engine._state_file = test_state_file
        yield engine

    # Temizlik
    if os.path.exists(test_state_file):
        os.remove(test_state_file)

@pytest.mark.asyncio
async def test_microscopic_loss_filter(risk_engine):
    """Epsilon (Mikroskobik kayıp / Break-Even) filtresinin test edilmesi"""
    bot_id = "BOT_EPSILON_1"

    # Başlangıçta sayaç 0
    assert risk_engine.consecutive_losses.get(bot_id, 0) == 0

    # 1. Net Zarar (-1.0 > -0.5)
    event1 = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": -1.0})
    await risk_engine.on_position_closed(event1)
    assert risk_engine.consecutive_losses.get(bot_id) == 1

    # 2. Mikroskobik Zarar (-0.05) -> Sayacı ARTIRMAMALI
    event2 = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": -0.05})
    await risk_engine.on_position_closed(event2)
    assert risk_engine.consecutive_losses.get(bot_id) == 1

    # 3. Mikroskobik Kâr (+0.1) -> Sayacı SIFIRLAMAMALI (Break-Even)
    event3 = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": 0.1})
    await risk_engine.on_position_closed(event3)
    assert risk_engine.consecutive_losses.get(bot_id) == 1

    # 4. Net Kâr (+1.0) -> Sayacı SIFIRLAMALI
    event4 = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": 1.0})
    await risk_engine.on_position_closed(event4)
    assert risk_engine.consecutive_losses.get(bot_id) == 0

@pytest.mark.asyncio
async def test_kill_switch_activation_and_veto(risk_engine):
    """5 ardışık kayıp sonrası Kill Switch VETO'sunun test edilmesi ve event fırlatılması"""
    bot_id = "BOT_KILL_1"

    # Mock Event Bus publish
    with patch('shared.events.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_publish:
        # 4 kez zarar
        for _ in range(4):
            event = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": -10.0})
            await risk_engine.on_position_closed(event)

        assert risk_engine.consecutive_losses.get(bot_id) == 4
        assert not risk_engine.check_kill_switch(bot_id)
        assert mock_publish.call_count == 0

        # 5. Zarar
        event5 = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": -10.0})
        await risk_engine.on_position_closed(event5)

        assert risk_engine.consecutive_losses.get(bot_id) == 5
        assert risk_engine.check_kill_switch(bot_id) is True
        assert risk_engine.can_open_position(current_positions=0, bot_id=bot_id) is False

        # Event fırlatıldığını doğrula
        assert mock_publish.call_count == 1
        published_event = mock_publish.call_args[0][0]
        assert published_event.type == "bot.stopped"
        assert published_event.payload["bot_id"] == bot_id
        assert published_event.payload["reason"] == "kill_switch_activated"
        assert published_event.payload["consecutive_losses"] == 5

@pytest.mark.asyncio
async def test_async_state_persistence(risk_engine):
    """Async dosya kilidi ve kalıcılık testi"""
    bot_id = "BOT_STATE_1"

    event = Event(type="position.closed", payload={"bot_id": bot_id, "pnl": -5.0})
    await risk_engine.on_position_closed(event)

    # Dosya oluşmuş ve içeriği doğru mu?
    assert os.path.exists(risk_engine._state_file)

    with open(risk_engine._state_file, 'r') as f:
        data = json.load(f)

    assert data["consecutive_losses"][bot_id] == 1
