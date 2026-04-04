import logging
import pytest
from unittest.mock import patch, MagicMock
from core.logger import setup_logger, ColoredJSONFormatter

@pytest.fixture
def temp_logger():
    """Provides a temporary logger name to ensure test isolation, and cleans up after test."""
    logger_name = "TestLogger"
    yield logger_name

    # Cleanup handlers to ensure isolation between tests
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()

def test_setup_logger_default(temp_logger):
    """Test setup_logger with default parameters."""
    with patch("core.logger.CONFIG", {"bot": {"log_level": "DEBUG", "environment": "development"}}):
        logger = setup_logger(name=temp_logger)

        assert logger.name == temp_logger
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1

        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, ColoredJSONFormatter)
        # Development environment means use_json=False
        assert handler.formatter.use_json is False

def test_setup_logger_use_json_true(temp_logger):
    """Test setup_logger when use_json is explicitly True."""
    # We patch FileHandler properly to avoid the 'level' attribute error when logging inside setup_logger
    mock_file_handler = MagicMock(spec=logging.FileHandler)
    mock_file_handler.level = logging.INFO
    with patch("core.logger.logging.FileHandler", return_value=mock_file_handler):
        logger = setup_logger(name=temp_logger, use_json=True)

        # In use_json=True, it adds both StreamHandler and FileHandler
        assert len(logger.handlers) == 2

        stream_handler = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)][0]
        assert isinstance(stream_handler.formatter, ColoredJSONFormatter)
        assert stream_handler.formatter.use_json is True

def test_setup_logger_use_json_false(temp_logger):
    """Test setup_logger when use_json is explicitly False."""
    logger = setup_logger(name=temp_logger, use_json=False)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].formatter.use_json is False

def test_setup_logger_idempotency(temp_logger):
    """Test that calling setup_logger multiple times does not add duplicate handlers."""
    logger1 = setup_logger(name=temp_logger, use_json=False)
    assert len(logger1.handlers) == 1

    logger2 = setup_logger(name=temp_logger, use_json=False)
    assert logger1 is logger2
    assert len(logger2.handlers) == 1 # Still 1 handler

def test_setup_logger_production_environment(temp_logger):
    """Test setup_logger uses JSON in production environment by default."""
    mock_file_handler = MagicMock(spec=logging.FileHandler)
    mock_file_handler.level = logging.INFO
    with patch("core.logger.CONFIG", {"bot": {"log_level": "INFO", "environment": "production"}}):
        with patch("core.logger.logging.FileHandler", return_value=mock_file_handler):
            logger = setup_logger(name=temp_logger)

            # Should have both StreamHandler and FileHandler
            assert len(logger.handlers) == 2

            stream_handler = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)][0]
            assert isinstance(stream_handler.formatter, ColoredJSONFormatter)
            assert stream_handler.formatter.use_json is True
