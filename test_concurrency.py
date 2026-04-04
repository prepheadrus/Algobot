import asyncio
import time
from httpx import AsyncClient, ASGITransport
import sys
from pathlib import Path
import json
import logging

# Ensure api and main are accessible
sys.path.append(str(Path(__file__).resolve().parent))

# Configure logging to show basic info
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_benchmark():
    try:
        from api.server import app
    except ImportError as e:
        logger.error(f"Could not import main app: {e}")
        return

    # Prepare dummy strategy
    strategy_payload = {
        "name": "Dummy Strategy",
        "indicators": {},
        "conditions": [],
        "risk": {}
    }

    # Save the dummy strategy to the expected folder
    strategy_dir = Path("artifacts/strategies")
    strategy_dir.mkdir(parents=True, exist_ok=True)
    strategy_file = strategy_dir / "dummy_strategy.json"
    with open(strategy_file, "w", encoding="utf-8") as f:
        json.dump(strategy_payload, f)

    request_payload = {
        "strategy": {},  # Required but overriden by filename
        "strategy_filename": "dummy_strategy.json",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "days": 10,
        "initial_balance": 10000.0,
        "risk_per_trade": 0.01
    }

    url = "/api/v1/backtest/run"
    num_requests = 50

    logger.info(f"Starting {num_requests} concurrent requests to {url}...")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start_time = time.perf_counter()

        # Create all request tasks
        tasks = [
            client.post(url, json=request_payload)
            for _ in range(num_requests)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()

    # Analyze results
    success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status_code in (200, 400, 404, 500))
    error_count = len(results) - success_count

    elapsed = end_time - start_time
    throughput = num_requests / elapsed

    logger.info("=== Benchmark Results ===")
    logger.info(f"Total time elapsed: {elapsed:.2f} seconds")
    logger.info(f"Total requests: {num_requests}")
    logger.info(f"Successful processing (No crash): {success_count}")
    logger.info(f"Throughput: {throughput:.2f} req/sec")

    if success_count == num_requests:
        logger.info("SUCCESS: The application successfully handled concurrent requests without the event loop crashing.")
    else:
        logger.warning(f"Some requests failed or crashed: {error_count} errors.")
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Exception: {r}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
