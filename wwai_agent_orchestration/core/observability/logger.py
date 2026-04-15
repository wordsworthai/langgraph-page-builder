# core/observability/logger.py

"""
Structured logging for orchestration system.
All logs are JSON-formatted with context propagation.

Logging can be controlled via environment variables:
- WWAI_AGENT_ORCHESTRATION_LOG_LEVEL: Set minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  Examples: WWAI_AGENT_ORCHESTRATION_LOG_LEVEL=WARNING (only WARNING and above)
            WWAI_AGENT_ORCHESTRATION_LOG_LEVEL=ERROR (only ERROR and above)
- WWAI_AGENT_ORCHESTRATION_SUPPRESS_INFO_LOGS: Set to "true" to suppress INFO logs (keeps ERROR/WARNING)
  Example: WWAI_AGENT_ORCHESTRATION_SUPPRESS_INFO_LOGS=true
- WWAI_AGENT_ORCHESTRATION_PERF_LOGS_ENABLED: Set to "true" to emit perf_llm/perf_mongo/perf_redis timing logs
  Example: WWAI_AGENT_ORCHESTRATION_PERF_LOGS_ENABLED=true
"""

import os
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variables for request tracking
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})

# Global logging configuration from environment
_LOG_LEVEL = os.getenv("WWAI_AGENT_ORCHESTRATION_LOG_LEVEL", "INFO").upper()
_SUPPRESS_INFO = os.getenv("WWAI_AGENT_ORCHESTRATION_SUPPRESS_INFO_LOGS", "true").lower() == "true"

# Map string levels to logging constants
_LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Get minimum log level
_MIN_LOG_LEVEL = _LOG_LEVEL_MAP.get(_LOG_LEVEL, logging.INFO)

# Performance timing logs (perf_llm, perf_mongo, perf_redis) only when enabled
_PERF_LOGS_ENABLED = os.getenv("WWAI_AGENT_ORCHESTRATION_PERF_LOGS_ENABLED", "false").lower() == "true"


class StructuredLogger:
    """
    Structured logger that outputs JSON logs with context.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handler()
    
    def _setup_handler(self):
        """Set up JSON handler if not already configured"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            # Use configured log level from environment
            self.logger.setLevel(_MIN_LOG_LEVEL)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method with context"""
        # Check if this log level should be suppressed
        level_num = _LOG_LEVEL_MAP.get(level, logging.INFO)
        
        # Skip if below minimum log level
        if level_num < _MIN_LOG_LEVEL:
            return
        
        # Skip INFO logs if WWAI_AGENT_ORCHESTRATION_SUPPRESS_INFO_LOGS is enabled
        if _SUPPRESS_INFO and level == "INFO":
            return
        
        context = request_context.get({})
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **context,
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)


class StructuredFormatter(logging.Formatter):
    """Formatter that passes through JSON strings unchanged"""
    
    def format(self, record):
        return record.getMessage()


def set_request_context(
    request_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    **kwargs
):
    """
    Set context for current request.
    This propagates automatically through async calls.
    """
    context = request_context.get({}).copy()
    
    if request_id:
        context["request_id"] = request_id
    if workflow_id:
        context["workflow_id"] = workflow_id
    
    context.update(kwargs)
    request_context.set(context)


def get_request_context() -> Dict[str, Any]:
    """Get current request context"""
    return request_context.get({})


def is_perf_logging_enabled() -> bool:
    """Return True if perf timing logs (perf_llm, perf_mongo, perf_redis) should be emitted."""
    return _PERF_LOGS_ENABLED


# Global logger instance
def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)