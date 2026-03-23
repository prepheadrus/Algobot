"""
Events Module

Event-Driven Architecture (EDA) için event bus ve event definitions.

Usage:
    from shared.events import event_bus, Event
    from shared.events.events import BotStartedEvent, PositionOpenedEvent
    
    # Subscribe
    event_bus.subscribe("bot.started", my_handler)
    
    # Publish
    event = BotStartedEvent(
        bot_id="bot_123",
        symbol="BTC/USDT",
        strategy_id="trend_master",
        timeframe="1m"
    ).to_event()
    
    await event_bus.publish(event)
"""

from shared.events.event_bus import EventBus, Event, event_bus, on_event, publish_event
from shared.events import events

__all__ = [
    # Event Bus
    'EventBus',
    'Event',
    'event_bus',
    'on_event',
    'publish_event',
    
    # Events module
    'events',
]
