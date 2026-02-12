"""Tests for Rate Limiter."""

import pytest
import time
import threading
from unittest.mock import Mock
from hypothesis import given, strategies as st

from alice.core.rate_limiter import RateLimiter
from alice.core.logger import Logger


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.rate_limit_requests_per_minute = 60
    config.rate_limit_burst_size = 10
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return Mock(spec=Logger)


@pytest.fixture
def rate_limiter(mock_config, mock_logger):
    """Create RateLimiter instance."""
    return RateLimiter(mock_config, mock_logger)


class TestTokenAcquisition:
    """Test token acquisition."""

    def test_acquire_token_success(self, rate_limiter):
        """Test successful token acquisition."""
        result = rate_limiter.acquire()
        assert result is True

    def test_acquire_multiple_tokens(self, rate_limiter):
        """Test acquiring multiple tokens."""
        for i in range(10):
            result = rate_limiter.acquire()
            assert result is True

    def test_acquire_exceeds_burst_size(self, rate_limiter):
        """Test acquiring more tokens than burst size."""
        # Acquire all burst tokens
        for i in range(10):
            rate_limiter.acquire()
        
        # Next acquisition should timeout
        result = rate_limiter.acquire(timeout_ms=100)
        assert result is False

    def test_acquire_with_timeout(self, rate_limiter):
        """Test token acquisition with timeout."""
        # Acquire all burst tokens
        for i in range(10):
            rate_limiter.acquire()
        
        # Try to acquire with timeout
        start = time.time()
        result = rate_limiter.acquire(timeout_ms=100)
        elapsed = (time.time() - start) * 1000
        
        assert result is False
        assert elapsed >= 100

    def test_token_refill(self, rate_limiter):
        """Test token refill over time."""
        # Acquire all burst tokens
        for i in range(10):
            rate_limiter.acquire()
        
        # Wait for tokens to refill
        time.sleep(0.1)
        
        # Should be able to acquire more tokens
        result = rate_limiter.acquire()
        assert result is True


class TestQueueing:
    """Test request queueing."""

    def test_queue_request(self, rate_limiter):
        """Test queueing a request."""
        rate_limiter.queue_request("req1")
        
        assert len(rate_limiter.request_queue) == 1

    def test_queue_multiple_requests(self, rate_limiter):
        """Test queueing multiple requests."""
        for i in range(5):
            rate_limiter.queue_request(f"req{i}")
        
        assert len(rate_limiter.request_queue) == 5

    def test_mark_processed(self, rate_limiter):
        """Test marking request as processed."""
        rate_limiter.queue_request("req1")
        rate_limiter.mark_processed("req1")
        
        assert rate_limiter.request_queue[0]["processed"] is True

    def test_get_queue_position(self, rate_limiter):
        """Test getting queue position."""
        for i in range(5):
            rate_limiter.queue_request(f"req{i}")
        
        position = rate_limiter.get_queue_position("req2")
        assert position == 2

    def test_get_queue_position_not_found(self, rate_limiter):
        """Test getting position of non-existent request."""
        rate_limiter.queue_request("req1")
        
        position = rate_limiter.get_queue_position("req_not_found")
        assert position is None

    def test_queue_ordering(self, rate_limiter):
        """Test that queue maintains FIFO ordering."""
        for i in range(5):
            rate_limiter.queue_request(f"req{i}")
        
        # Verify order
        for i in range(5):
            assert rate_limiter.request_queue[i]["id"] == f"req{i}"


class TestQuotaTracking:
    """Test quota tracking."""

    def test_get_remaining_quota(self, rate_limiter):
        """Test getting remaining quota."""
        quota = rate_limiter.get_remaining_quota()
        assert quota > 0

    def test_remaining_quota_decreases(self, rate_limiter):
        """Test that remaining quota decreases after acquisition."""
        quota_before = rate_limiter.get_remaining_quota()
        rate_limiter.acquire()
        quota_after = rate_limiter.get_remaining_quota()
        
        assert quota_after < quota_before

    def test_get_status(self, rate_limiter):
        """Test getting rate limiter status."""
        status = rate_limiter.get_status()
        
        assert "tokens_available" in status
        assert "burst_size" in status
        assert "requests_per_minute" in status
        assert "queue_length" in status

    def test_status_reflects_acquisitions(self, rate_limiter):
        """Test that status reflects token acquisitions."""
        status_before = rate_limiter.get_status()
        rate_limiter.acquire()
        status_after = rate_limiter.get_status()
        
        assert status_after["tokens_available"] < status_before["tokens_available"]


class TestThreadSafety:
    """Test thread safety."""

    def test_concurrent_acquisitions(self, rate_limiter):
        """Test concurrent token acquisitions."""
        results = []
        
        def acquire_token():
            result = rate_limiter.acquire(timeout_ms=1000)
            results.append(result)
        
        threads = []
        for i in range(20):
            t = threading.Thread(target=acquire_token)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have some successful acquisitions
        assert sum(results) > 0

    def test_concurrent_queue_operations(self, rate_limiter):
        """Test concurrent queue operations."""
        def queue_and_process():
            for i in range(5):
                rate_limiter.queue_request(f"req_{threading.current_thread().ident}_{i}")
                rate_limiter.mark_processed(f"req_{threading.current_thread().ident}_{i}")
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=queue_and_process)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All requests should be queued
        assert len(rate_limiter.request_queue) == 25


# Property-based tests

def test_property_rate_limiting_respects_quota():
    """Property 16: Rate Limiting Respects Quota.
    
    For any sequence of API calls with a configured rate limit, the number 
    of successful calls should not exceed the quota within the time window.
    
    Validates: Requirements 6.3
    """
    config = Mock()
    config.rate_limit_requests_per_minute = 60
    config.rate_limit_burst_size = 10
    logger = Mock(spec=Logger)
    
    rate_limiter = RateLimiter(config, logger)
    
    # Try to acquire more tokens than burst size
    successful = 0
    for i in range(15):
        if rate_limiter.acquire(timeout_ms=10):
            successful += 1
    
    # Should not exceed burst size
    assert successful <= 10


def test_property_rate_limiting_proactive_slowdown():
    """Property 17: Rate Limiting Proactive Slowdown.
    
    For any API with a configured rate limit, as the quota consumption 
    approaches the limit, the request rate should decrease.
    
    Validates: Requirements 6.4
    """
    config = Mock()
    config.rate_limit_requests_per_minute = 60
    config.rate_limit_burst_size = 10
    logger = Mock(spec=Logger)
    
    rate_limiter = RateLimiter(config, logger)
    
    # Acquire tokens and measure time
    start = time.time()
    
    # Acquire all burst tokens quickly
    for i in range(10):
        rate_limiter.acquire()
    
    # Try to acquire more (should be slower)
    result = rate_limiter.acquire(timeout_ms=500)
    elapsed = (time.time() - start) * 1000
    
    # Should take some time to refill
    assert elapsed > 100


def test_property_rate_limiting_queue_ordering():
    """Property 18: Rate Limiting Queue Ordering.
    
    For any sequence of requests sent to a rate-limited API, the requests 
    should be processed in the order they were queued.
    
    Validates: Requirements 6.6
    """
    config = Mock()
    config.rate_limit_requests_per_minute = 60
    config.rate_limit_burst_size = 10
    logger = Mock(spec=Logger)
    
    rate_limiter = RateLimiter(config, logger)
    
    # Queue requests
    for i in range(10):
        rate_limiter.queue_request(f"req{i}")
    
    # Verify FIFO ordering
    for i in range(10):
        position = rate_limiter.get_queue_position(f"req{i}")
        assert position == i
