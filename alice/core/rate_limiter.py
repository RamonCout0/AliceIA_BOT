"""Rate Limiter for API quota management."""

import time
import threading
from typing import Optional
from collections import deque
from datetime import datetime, timedelta

from alice.core.logger import Logger


class RateLimiter:
    """Rate limiting with token bucket algorithm."""

    def __init__(self, config: any, logger: Logger):
        """Initialize RateLimiter.
        
        Args:
            config: Configuration object with rate limiting settings
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.requests_per_minute = getattr(config, "rate_limit_requests_per_minute", 60)
        self.burst_size = getattr(config, "rate_limit_burst_size", 10)
        
        # Token bucket state
        self.tokens = self.burst_size
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
        # Request queue for ordering
        self.request_queue = deque()
        self.queue_lock = threading.Lock()

    def acquire(self, timeout_ms: Optional[int] = None) -> bool:
        """Acquire a token for making a request.
        
        Args:
            timeout_ms: Maximum time to wait for a token (milliseconds)
            
        Returns:
            True if token acquired, False if timeout
        """
        timeout_seconds = (timeout_ms / 1000.0) if timeout_ms else None
        start_time = time.time()
        
        while True:
            with self.lock:
                # Refill tokens based on time elapsed
                self._refill_tokens()
                
                # Check if token available
                if self.tokens >= 1:
                    self.tokens -= 1
                    self.logger.debug(
                        "RateLimiter",
                        "Token acquired",
                        {"tokens_remaining": self.tokens}
                    )
                    return True
            
            # Check timeout
            if timeout_seconds:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    self.logger.warning(
                        "RateLimiter",
                        "Token acquisition timeout",
                        {"timeout_ms": timeout_ms, "elapsed_ms": elapsed * 1000}
                    )
                    return False
            
            # Wait before retrying
            time.sleep(0.01)

    def queue_request(self, request_id: str) -> None:
        """Queue a request for ordered processing.
        
        Args:
            request_id: Unique identifier for the request
        """
        with self.queue_lock:
            self.request_queue.append({
                "id": request_id,
                "timestamp": datetime.now(),
                "processed": False
            })

    def mark_processed(self, request_id: str) -> None:
        """Mark a request as processed.
        
        Args:
            request_id: Unique identifier for the request
        """
        with self.queue_lock:
            for req in self.request_queue:
                if req["id"] == request_id:
                    req["processed"] = True
                    break

    def get_queue_position(self, request_id: str) -> Optional[int]:
        """Get position of request in queue.
        
        Args:
            request_id: Unique identifier for the request
            
        Returns:
            Position in queue (0-based), or None if not found
        """
        with self.queue_lock:
            for i, req in enumerate(self.request_queue):
                if req["id"] == request_id:
                    return i
        return None

    def get_remaining_quota(self) -> int:
        """Get remaining quota in current minute.
        
        Returns:
            Number of requests remaining
        """
        with self.lock:
            self._refill_tokens()
            # Calculate remaining quota based on tokens and refill rate
            tokens_per_second = self.requests_per_minute / 60.0
            max_tokens = self.requests_per_minute
            return int(self.tokens + (tokens_per_second * 60))

    def get_status(self) -> dict:
        """Get rate limiter status.
        
        Returns:
            Dictionary with status information
        """
        with self.lock:
            self._refill_tokens()
            return {
                "tokens_available": self.tokens,
                "burst_size": self.burst_size,
                "requests_per_minute": self.requests_per_minute,
                "queue_length": len(self.request_queue),
            }

    def _refill_tokens(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add (requests per minute / 60 seconds)
        tokens_per_second = self.requests_per_minute / 60.0
        tokens_to_add = elapsed * tokens_per_second
        
        # Add tokens up to burst size
        self.tokens = min(self.tokens + tokens_to_add, self.burst_size)
        self.last_refill = now
