import uuid
from typing import Dict, Any, Optional
from cachetools import TTLCache
from core.logger import logger

class BacktestService:
    """
    Service for managing backtest results and caching them.
    Implemented as a Singleton to share the cache across requests.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BacktestService, cls).__new__(cls)
            # Initialize cache: max 100 items, 1 hour (3600 seconds) TTL
            cls._instance._cache = TTLCache(maxsize=100, ttl=3600)
            logger.info("🔧 BacktestService initialized with TTLCache (maxsize=100, ttl=3600)")
        return cls._instance

    def save_result(self, result: Any, backtest_id: Optional[str] = None) -> str:
        """
        Saves a backtest result to the cache and returns its unique ID.
        If backtest_id is provided, it uses it, otherwise generates a new one.
        """
        if not backtest_id:
            backtest_id = str(uuid.uuid4())

        self._cache[backtest_id] = result
        logger.debug(f"💾 Backtest result saved to cache with ID: {backtest_id}")
        return backtest_id

    def get_result(self, backtest_id: str) -> Optional[Any]:
        """
        Retrieves a backtest result from the cache by ID.
        """
        result = self._cache.get(backtest_id)
        if result:
            logger.debug(f"🔍 Backtest result retrieved from cache for ID: {backtest_id}")
        else:
            logger.debug(f"⚠️ Backtest result not found in cache for ID: {backtest_id}")
        return result
