import logging
import colorlog
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from core.config import CONFIG

class JSONFormatter(logging.Formatter):
    """
    Structured Logging Formatter (JSON Format).
    ELK Stack (Elasticsearch, Logstash, Kibana) ve benzeri sistemler için.
    
    Usage:
        logger.info("Bot started", extra={'bot_id': 'BTC_1', 'symbol': 'BTC/USDT'})
        # Output: {"timestamp": "...", "level": "INFO", "message": "Bot started", "bot_id": "BTC_1", ...}
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Exception traceback ekle
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Extra fields (kullanıcı tarafından eklenen)
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                          'message', 'asctime']:
                try:
                    json.dumps(value)  # JSON serialize edilebilir mi?
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredJSONFormatter(logging.Formatter):
    """
    Hybrid Formatter: Konsol için renkli, dosya için JSON.
    Development modunda renkli, production modunda JSON.
    """
    
    def __init__(self, use_json: bool = False):
        super().__init__()
        self.use_json = use_json
        
        self.colored_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt='%H:%M:%S',
            reset=True,
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        
        self.json_formatter = JSONFormatter()
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_json:
            return self.json_formatter.format(record)
        else:
            return self.colored_formatter.format(record)


def setup_logger(name='CryptoAlgoBot', use_json: Optional[bool] = None):
    """
    Merkezi loglama yapılandırması.
    
    Args:
        name: Logger adı
        use_json: True için JSON, False için renkli konsol.
                  None ise config.yaml'dan otomatik (production=True, development=False)
    """
    logger = logging.getLogger(name)

    # Log seviyesini config.yaml'dan belirle
    log_level_str = CONFIG.get('bot', {}).get('log_level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # JSON formatı kullanılsın mı? (default: False - renkli konsol)
    if use_json is None:
        environment = CONFIG.get('bot', {}).get('environment', 'development')
        use_json = (environment == 'production')  # Sadece production'da JSON

    # Eğer önceden eklenmiş bir handler varsa, tekrar ekleme
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Hybrid formatter (konsol renkli, production JSON)
        formatter = ColoredJSONFormatter(use_json=use_json)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Production modunda dosya logger da ekle
        if use_json:
            try:
                file_handler = logging.FileHandler('cryptobot.log', encoding='utf-8')
                file_handler.setLevel(log_level)
                file_handler.setFormatter(JSONFormatter())
                logger.addHandler(file_handler)
                logger.info("📄 Log dosyası: cryptobot.log (JSON format)")
            except Exception as e:
                logger.warning(f"⚠️ Dosya logger oluşturulamadı: {e}")

    return logger


# Silencing noisy third-party loggers
def silence_noisy_loggers():
    """Silence external libraries that generate too much noise."""
    noisy_loggers = [
        "uvicorn.access",
        "uvicorn.error",
        "httpcore",
        "httpx",
        "ccxt",
        "matplotlib",
        "PIL",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# Logger örneği kullanımı için hazır
silence_noisy_loggers()
logger = setup_logger()
