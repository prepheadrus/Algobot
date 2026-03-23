"""
API Schemas

Pydantic models for request/response validation.
"""

from api.schemas.bot import (
    BotStartRequest,
    BotStopRequest,
    BotResumeRequest,
    BotRemoveRequest,
    BotStatusResponse,
    BotListResponse,
)
from api.schemas.ml import (
    MLTrainRequest,
    MLStatusResponse,
    MLTrainingHistoryResponse,
    MLCheckModelResponse,
)
from api.schemas.strategy import (
    StrategySelectRequest,
    StrategyListResponse,
)
from api.schemas.data import (
    DataDownloadRequest,
    DataStopRequest,
    DataResumeRequest,
    DataDeleteRequest,
    DataPauseRequest,
    HistoryStatusResponse,
    ActiveDownloadsResponse,
)
from api.schemas.config import (
    RiskConfigUpdate,
    AdvancedConfigUpdate,
    ApiKeyUpdateRequest,
)

__all__ = [
    # Bot
    'BotStartRequest',
    'BotStopRequest',
    'BotResumeRequest',
    'BotRemoveRequest',
    'BotStatusResponse',
    'BotListResponse',

    # ML
    'MLTrainRequest',
    'MLStatusResponse',
    'MLTrainingHistoryResponse',
    'MLCheckModelResponse',

    # Strategy
    'StrategySelectRequest',
    'StrategyListResponse',

    # Data
    'DataDownloadRequest',
    'DataStopRequest',
    'DataResumeRequest',
    'DataDeleteRequest',
    'DataPauseRequest',
    'HistoryStatusResponse',
    'ActiveDownloadsResponse',

    # Config
    'RiskConfigUpdate',
    'AdvancedConfigUpdate',
    'ApiKeyUpdateRequest',
]
