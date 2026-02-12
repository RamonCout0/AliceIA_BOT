"""Error Handler with retry logic and timeout management."""

import asyncio
import logging
import time
from typing import Any, Callable, Optional, TypeVar
from datetime import datetime

from alice.core.logger import Logger

T = TypeVar("T")


class ErrorHandler:
    """Manages retries, timeouts, and error recovery."""

    def __init__(self, config: Any, logger: Logger):
        """Initialize ErrorHandler.
        
        Args:
            config: Configuration object with retry settings
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.max_retries = getattr(config, "groq_max_retries", 5)
        self.backoff_factor = 2.0
        self.base_delay = 1.0

    def is_transient_error(self, error: Exception) -> bool:
        """Determine if error is transient (retry) or permanent (fail fast).
        
        Args:
            error: Exception to classify
            
        Returns:
            True if error is transient, False if permanent
        """
        error_str = str(error).lower()
        
        # Transient errors
        transient_indicators = [
            "timeout",
            "429",  # Rate Limited
            "503",  # Service Unavailable
            "504",  # Gateway Timeout
            "connection",
            "temporary",
            "temporarily",
        ]
        
        for indicator in transient_indicators:
            if indicator in error_str:
                return True
        
        # Permanent errors
        permanent_indicators = [
            "401",  # Unauthorized
            "403",  # Forbidden
            "404",  # Not Found
            "invalid api key",
            "unauthorized",
            "forbidden",
            "not found",
        ]
        
        for indicator in permanent_indicators:
            if indicator in error_str:
                return False
        
        # Default to transient for unknown errors
        return True

    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        timeout_ms: Optional[int] = None,
        **kwargs
    ) -> T:
        """Execute function with retry logic and timeout.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            timeout_ms: Timeout in milliseconds (optional)
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from function
            
        Raises:
            Exception: If all retries fail or permanent error occurs
        """
        last_error = None
        func_name = getattr(func, "__name__", str(func))
        
        for attempt in range(self.max_retries + 1):
            try:
                # Execute with timeout if specified
                if timeout_ms:
                    return self._execute_with_timeout(func, timeout_ms, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as error:
                last_error = error
                
                # Log error with context
                self.logger.error(
                    "ErrorHandler",
                    f"Error in {func_name} (attempt {attempt + 1}/{self.max_retries + 1})",
                    {
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "attempt": attempt + 1,
                        "max_retries": self.max_retries + 1,
                    }
                )
                
                # Check if error is permanent
                if not self.is_transient_error(error):
                    self.logger.error(
                        "ErrorHandler",
                        f"Permanent error in {func_name}, failing fast",
                        {
                            "error_type": type(error).__name__,
                            "error_message": str(error),
                        }
                    )
                    raise
                
                # If max retries reached, raise
                if attempt >= self.max_retries:
                    self.logger.error(
                        "ErrorHandler",
                        f"Max retries reached for {func_name}",
                        {
                            "error_type": type(error).__name__,
                            "error_message": str(error),
                            "max_retries": self.max_retries,
                        }
                    )
                    raise
                
                # Calculate backoff delay
                delay = self.base_delay * (self.backoff_factor ** attempt)
                self.logger.info(
                    "ErrorHandler",
                    f"Retrying {func_name} after {delay:.1f}s",
                    {"delay_seconds": delay, "attempt": attempt + 1}
                )
                time.sleep(delay)
        
        # Should not reach here, but raise last error if we do
        if last_error:
            raise last_error

    def _execute_with_timeout(
        self,
        func: Callable[..., T],
        timeout_ms: int,
        *args,
        **kwargs
    ) -> T:
        """Execute function with timeout.
        
        Args:
            func: Function to execute
            timeout_ms: Timeout in milliseconds
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from function
            
        Raises:
            TimeoutError: If function exceeds timeout
        """
        timeout_seconds = timeout_ms / 1000.0
        start_time = time.time()
        func_name = getattr(func, "__name__", str(func))
        
        try:
            # For synchronous functions, we can't truly interrupt
            # but we can check time after execution
            result = func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000
            
            if elapsed > timeout_ms:
                raise TimeoutError(
                    f"Function {func_name} exceeded timeout of {timeout_ms}ms "
                    f"(took {elapsed:.0f}ms)"
                )
            
            return result
            
        except TimeoutError:
            raise
        except Exception as error:
            elapsed = (time.time() - start_time) * 1000
            if elapsed > timeout_ms:
                raise TimeoutError(
                    f"Function {func_name} exceeded timeout of {timeout_ms}ms "
                    f"(took {elapsed:.0f}ms)"
                ) from error
            raise

    def trigger_alert(self, error: Exception) -> None:
        """Send alert for critical errors.
        
        Args:
            error: Exception that triggered the alert
        """
        self.logger.critical(
            "ErrorHandler",
            "CRITICAL ERROR - Alert triggered",
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )
        # TODO: Implement Discord notification or other alert mechanism
