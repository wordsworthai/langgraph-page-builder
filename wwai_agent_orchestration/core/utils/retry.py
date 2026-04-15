# core/utils/retry.py

"""
Retry utilities with exponential backoff.
"""

import time
import random
from typing import Callable, TypeVar, Optional, Type, Tuple
from functools import wraps

from core.observability.logger import get_logger
logger = get_logger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        exceptions: Tuple of exception types to retry on
        
    Usage:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def flaky_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts",
                            function=func.__name__,
                            error=str(e)
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    actual_delay = min(delay, max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        actual_delay = actual_delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Function {func.__name__} failed, retrying in {actual_delay:.2f}s",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_retries + 1,
                        delay=actual_delay,
                        error=str(e)
                    )
                    
                    time.sleep(actual_delay)
                    
                    # Increase delay for next attempt
                    delay *= exponential_base
            
            # Should never reach here
            raise RuntimeError(f"Retry logic error in {func.__name__}")
        
        return wrapper
    return decorator


def retry_simple(max_retries: int = 1, delay: float = 1.0):
    """
    Simple retry decorator with fixed delay.
    
    Usage:
        @retry_simple(max_retries=2, delay=0.5)
        def simple_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt >= max_retries:
                        raise
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries + 1} for {func.__name__}",
                        error=str(e)
                    )
                    time.sleep(delay)
            
            raise RuntimeError(f"Retry logic error in {func.__name__}")
        
        return wrapper
    return decorator