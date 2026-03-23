
import pytest
import asyncio
from datetime import datetime
from core.diagnostics.event_tracer import EventTracer, EventCategory
from shared.events.events import Event

def test_event_tracer_counting():
    tracer = EventTracer()
    tracer._running = True

    # Simulate events
    events = [
        Event(type="bot.started", payload={}),
        Event(type="bot.stopped", payload={}),
        Event(type="signal.new", payload={}),
        Event(type="data.update", payload={}),
    ]

    for event in events:
        tracer._on_event(event)

    stats = tracer.get_stats()

    assert stats['total_events'] == 4
    assert stats['by_category']['bot'] == 2
    assert stats['by_category']['signal'] == 1
    assert stats['by_category']['data'] == 1
    assert 'position' not in stats['by_category']

def test_event_tracer_get_stats_type():
    tracer = EventTracer()
    stats = tracer.get_stats()
    assert isinstance(stats['by_category'], dict)

def test_event_tracer_statistics_no_error(capsys):
    # This just ensures no crash during print
    tracer = EventTracer()
    tracer.start_time = datetime.utcnow()
    tracer.event_count = {'bot': 10, 'signal': 5}
    tracer.total_events = 15
    tracer._print_statistics()
    captured = capsys.readouterr()
    # stats are logged, not printed to stdout directly by print()
