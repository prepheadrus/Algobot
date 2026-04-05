import timeit
import gc
from datetime import datetime

def setup_code():
    now = datetime.utcnow()
    # Dummy creation parameters
    return """
from datetime import datetime
from core.trading.entities.order import Order, OrderType, OrderSide, OrderStatus

now = datetime.utcnow()
"""

def create_order_benchmark():
    setup = setup_code()
    code = """
Order(
    id="test_id",
    bot_id="bot_123",
    symbol="BTC/USDT",
    type=OrderType.LIMIT,
    side=OrderSide.BUY,
    status=OrderStatus.PENDING,
    size=1.0,
    leverage=1.0,
    created_at=now,
    price=50000.0,
    stop_price=49000.0
)
"""
    # Force garbage collection to minimize noise
    gc.collect()
    time_taken = timeit.timeit(code, setup=setup, number=100000)
    print(f"Time to create 100,000 LIMIT orders: {time_taken:.4f} seconds")
    return time_taken


def test_properties_benchmark():
    setup = setup_code() + """
order = Order(
    id="test_id",
    bot_id="bot_123",
    symbol="BTC/USDT",
    type=OrderType.LIMIT,
    side=OrderSide.BUY,
    status=OrderStatus.PENDING,
    size=1.0,
    leverage=1.0,
    created_at=now,
    price=50000.0,
    stop_price=49000.0
)
"""
    code = """
order.is_active
order.is_terminal
order.is_stop
"""
    gc.collect()
    time_taken = timeit.timeit(code, setup=setup, number=1000000)
    print(f"Time to access properties 1,000,000 times: {time_taken:.4f} seconds")
    return time_taken

if __name__ == "__main__":
    print("Baseline Benchmarks:")
    create_order_benchmark()
    test_properties_benchmark()
