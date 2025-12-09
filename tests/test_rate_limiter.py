# ============================================================================
# tests/test_rate_limiter.py - Rate limiter tests
# ============================================================================

import pytest
import asyncio
from shared.rate_limiter import InMemoryRateLimiter


class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.fixture
    def limiter(self):
        """Create a fresh rate limiter for each test"""
        return InMemoryRateLimiter()

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, limiter):
        """Test that requests under the limit are allowed"""
        for i in range(5):
            allowed, _ = await limiter.is_allowed("test_key", max_requests=10, window_seconds=60)
            assert allowed is True

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, limiter):
        """Test that requests over the limit are blocked"""
        # Use up the limit
        for i in range(10):
            allowed, _ = await limiter.is_allowed("test_key", max_requests=10, window_seconds=60)
            assert allowed is True

        # Next request should be blocked
        allowed, retry_after = await limiter.is_allowed("test_key", max_requests=10, window_seconds=60)
        assert allowed is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, limiter):
        """Test that different keys have independent limits"""
        # Max out key1
        for i in range(5):
            await limiter.is_allowed("key1", max_requests=5, window_seconds=60)

        # key1 should be blocked
        allowed1, _ = await limiter.is_allowed("key1", max_requests=5, window_seconds=60)
        assert allowed1 is False

        # key2 should still be allowed
        allowed2, _ = await limiter.is_allowed("key2", max_requests=5, window_seconds=60)
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_entries(self, limiter):
        """Test that cleanup removes stale entries"""
        # Add some entries
        await limiter.is_allowed("old_key", max_requests=10, window_seconds=60)

        # Cleanup with 0 max age (removes everything)
        await limiter.cleanup(max_age_seconds=0)

        # Should be allowed again since entries were cleaned
        allowed, _ = await limiter.is_allowed("old_key", max_requests=1, window_seconds=60)
        assert allowed is True
