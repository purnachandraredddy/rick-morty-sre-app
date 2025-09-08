"""Redis cache management."""
import json
import pickle
from typing import Any, Optional

import redis.asyncio as redis
import structlog

from app.config import settings

logger = structlog.get_logger()


class CacheManager:
    """Redis cache manager with async support."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=False,  # We'll handle encoding ourselves
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self._connected = False
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            try:
                await self.redis_client.aclose()
                self._connected = False
                logger.info("Disconnected from Redis cache")
            except Exception as e:
                logger.error("Error disconnecting from Redis", error=str(e))

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._connected or not self.redis_client:
            return None

        try:
            full_key = f"{settings.cache_prefix}{key}"
            data = await self.redis_client.get(full_key)
            if data:
                try:
                    # Try JSON first (for simple data)
                    return json.loads(data.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Fall back to pickle for complex objects
                    return pickle.loads(data)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self._connected or not self.redis_client:
            return False

        try:
            full_key = f"{settings.cache_prefix}{key}"
            ttl = ttl or settings.cache_ttl

            # Try to serialize as JSON first
            try:
                data = json.dumps(value, default=str).encode("utf-8")
            except (TypeError, ValueError):
                # Fall back to pickle for complex objects
                data = pickle.dumps(value)

            await self.redis_client.setex(full_key, ttl, data)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected or not self.redis_client:
            return False

        try:
            full_key = f"{settings.cache_prefix}{key}"
            result = await self.redis_client.delete(full_key)
            return bool(result)
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._connected or not self.redis_client:
            return False

        try:
            full_key = f"{settings.cache_prefix}{key}"
            result = await self.redis_client.exists(full_key)
            return bool(result)
        except Exception as e:
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        if not self._connected or not self.redis_client:
            return 0

        try:
            full_pattern = f"{settings.cache_prefix}{pattern}"
            keys = await self.redis_client.keys(full_pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Cache clear pattern failed", pattern=pattern, error=str(e))
            return 0

    async def health_check(self) -> dict:
        """Check cache health."""
        try:
            if not self.redis_client:
                return {"status": "disconnected", "error": "No Redis client"}

            logger.info("Starting cache health check")
            await self.redis_client.ping()
            info = await self.redis_client.info()

            return {
                "status": "healthy",
                "connected": self._connected,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "connected": False}


# Global cache instance
cache = CacheManager()
