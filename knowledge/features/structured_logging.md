# 📝 Structured Logging

**Version:** v4.1.0  
**Status:** ✅ Production Ready  
**Category:** Observability / Logging  
**Last Updated:** March 2026

---

## 📋 Overview

Structured Logging, hem renkli konsol hem de JSON formatında loglama sağlar. ELK Stack (Elasticsearch, Logstash, Kibana) ve benzeri sistemlerle uyumludur.

**Problem:**
- Konsol logları analiz edilemiyor
- Production'da hata ayıklama zor
- Log aggregation yok

**Çözüm:**
- Development: Renkli konsol log
- Production: JSON format + dosya logger
- Extra fields ile zenginleştirilmiş log

---

## 🏗️ Architecture

### **Dual-Mode Logging**

```
┌─────────────────────────────────────────┐
│ Development Mode                        │
│ ┌─────────────────────────────────────┐ │
│ │ 15:30:45 | INFO  | Bot started     │ │
│ │ 15:30:46 | ERROR | Connection lost │ │
│ └─────────────────────────────────────┘ │
│ Colored Console Output                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Production Mode                         │
│ ┌─────────────────────────────────────┐ │
│ │ {                                   │ │
│ │   "timestamp": "2026-03-22T...",    │ │
│ │   "level": "INFO",                  │ │
│ │   "message": "Bot started",         │ │
│ │   "bot_id": "BTC_1",                │ │
│ │   "symbol": "BTC/USDT"              │ │
│ │ }                                   │ │
│ └─────────────────────────────────────┘ │
│ JSON File Output (cryptobot.log)        │
└─────────────────────────────────────────┘
```

---

## 🔧 Implementation

### **Logger Configuration**

**File:** `core/logger.py`

```python
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
    ELK Stack compatible.
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
        
        # Exception traceback
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'pathname', 'process', 
                          'processName', 'relativeCreated', 'stack_info', 
                          'exc_info', 'exc_text', 'thread', 'threadName',
                          'message', 'asctime']:
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredJSONFormatter(logging.Formatter):
    """
    Hybrid Formatter: Console colored, Production JSON.
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
    Centralized logging configuration.
    
    Args:
        name: Logger name
        use_json: True for JSON, False for colored console.
                  None = auto from config.yaml
    """
    logger = logging.getLogger(name)

    # Log level from config
    log_level_str = CONFIG.get('bot', {}).get('log_level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Auto-detect mode
    if use_json is None:
        environment = CONFIG.get('bot', {}).get('environment', 'development')
        use_json = (environment == 'production')

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Hybrid formatter
        formatter = ColoredJSONFormatter(use_json=use_json)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Production: Add file logger
        if use_json:
            try:
                file_handler = logging.FileHandler('cryptobot.log', encoding='utf-8')
                file_handler.setLevel(log_level)
                file_handler.setFormatter(JSONFormatter())
                logger.addHandler(file_handler)
                logger.info(f"📄 Log dosyası: cryptobot.log (JSON format)")
            except Exception as e:
                logger.warning(f"⚠️ Dosya logger oluşturulamadı: {e}")

    return logger


# Silence noisy loggers
def silence_noisy_loggers():
    """Silence external libraries."""
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


# Initialize logger
silence_noisy_loggers()
logger = setup_logger()
```

---

## 📊 Usage Examples

### **Basic Logging**

```python
from core.logger import logger

# Standard logging
logger.info("Bot started")
logger.warning("High latency detected")
logger.error("Connection failed")
logger.critical("Database corrupted")
```

### **Extra Fields**

```python
# Add context to logs
logger.info(
    "Position opened",
    extra={
        'bot_id': 'BTC_1',
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 68500.00,
        'size': 0.1
    }
)

# Production output (JSON):
# {
#   "timestamp": "2026-03-22T15:30:45.123456",
#   "level": "INFO",
#   "message": "Position opened",
#   "bot_id": "BTC_1",
#   "symbol": "BTC/USDT",
#   "direction": "LONG",
#   "entry_price": 68500.00,
#   "size": 0.1
# }
```

### **Exception Logging**

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)

# Production output includes full traceback:
# {
#   "timestamp": "...",
#   "level": "ERROR",
#   "message": "Operation failed: Connection timeout",
#   "exception": "Traceback (most recent call last):\n  ..."
# }
```

---

## 🎯 Configuration

### **Development Mode**

```yaml
# config.yaml
bot:
  environment: development
  log_level: DEBUG  # Verbose logging
```

**Output:**
```
15:30:45 | INFO     | Bot started
15:30:46 | DEBUG    | Loading config...
15:30:47 | WARNING  | High latency: 500ms
```

### **Production Mode**

```yaml
# config.yaml
bot:
  environment: production
  log_level: INFO  # Less verbose
```

**Output (cryptobot.log):**
```json
{"timestamp": "2026-03-22T15:30:45.123456", "level": "INFO", "message": "Bot started", "module": "main", "function": "start_background_tasks"}
{"timestamp": "2026-03-22T15:30:46.234567", "level": "INFO", "message": "Position opened", "bot_id": "BTC_1", "symbol": "BTC/USDT"}
```

---

## 📈 Log Aggregation

### **ELK Stack Integration**

**Logstash Config:**

```ruby
# logstash.conf
input {
  file {
    path => "/path/to/cryptobot.log"
    codec => json
  }
}

filter {
  date {
    match => ["timestamp", "ISO8601"]
  }
  
  if [level] == "ERROR" {
    mutate {
      add_tag => ["error"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "cryptobot-%{+YYYY.MM.dd}"
  }
}
```

### **Kibana Dashboard**

1. **Create Index Pattern:**
   ```
   cryptobot-*
   ```

2. **Visualizations:**
   - Error rate over time
   - Log level distribution
   - Top error messages
   - Bot activity heatmap

---

## 🔍 Troubleshooting

### **Logs Not Appearing**

**Symptoms:**
- No logs in console
- No log file created

**Solutions:**
1. **Check log level:**
   ```yaml
   bot:
     log_level: DEBUG  # More verbose
   ```

2. **Check file permissions:**
   ```bash
   ls -la cryptobot.log
   chmod 644 cryptobot.log
   ```

3. **Check handlers:**
   ```python
   logger.info(f"Handlers: {logger.handlers}")
   # Should show at least 1 handler
   ```

### **JSON Not Valid**

**Symptoms:**
- Logstash/Elasticsearch rejects logs
- Parse errors

**Solutions:**
1. **Check for non-serializable objects:**
   ```python
   # Bad
   logger.info("Data", extra={'data': some_object})
   
   # Good
   logger.info("Data", extra={'data': str(some_object)})
   ```

2. **Validate JSON:**
   ```bash
   python -m json.tool cryptobot.log > /dev/null
   ```

---

## 📚 Best Practices

### **1. Use Appropriate Log Levels**

```python
logger.debug("Detailed info")      # Development only
logger.info("Normal operation")     # Production
logger.warning("Unexpected event")  # Not critical
logger.error("Error occurred")      # Needs attention
logger.critical("System failure")   # Immediate action
```

### **2. Add Context**

```python
# Bad
logger.error("Failed to open position")

# Good
logger.error(
    "Failed to open position",
    extra={
        'bot_id': 'BTC_1',
        'symbol': 'BTC/USDT',
        'error_code': 'INSUFFICIENT_MARGIN'
    }
)
```

### **3. Avoid Sensitive Data**

```python
# Bad - exposes API key
logger.info(f"Using API key: {api_key}")

# Good - mask sensitive data
logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:]}")
```

---

## 📈 Performance Impact

| Mode | Overhead | File Size (1hr) |
|------|----------|-----------------|
| Development (Colored) | <1% | N/A |
| Production (JSON) | 2-5% | ~10MB |

---

## 🔄 Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.1.0 | Mar 2026 | Initial implementation |
| v4.1.1 | Mar 2026 | Added extra fields support |
| v4.1.2 | Mar 2026 | Added ELK integration guide |

---

**Author:** CryptoAlgoBot Team  
**Review Status:** ✅ Peer Reviewed  
**Next Review:** April 2026
