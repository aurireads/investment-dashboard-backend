# Serviços de cache
from typing import Optional, Any
import json
import logging
from datetime import timedelta

import aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_redis_client() -> aioredis.Redis:
    """Get a new Redis client instance."""
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def set_cache(key: str, value: Any, ttl: int = settings.PRICE_CACHE_TTL):
    """
    Set a value in Redis cache with a time-to-live (TTL).
    """
    try:
        redis = await get_redis_client()
        await redis.set(key, json.dumps(value), ex=ttl)
        logger.debug(f"Cache set for key: {key}")
    except Exception as e:
        logger.error(f"Error setting cache for key {key}: {e}")

async def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from Redis cache. Returns None if not found.
    """
    try:
        redis = await get_redis_client()
        value = await redis.get(key)
        if value:
            logger.debug(f"Cache hit for key: {key}")
            return json.loads(value)
        logger.debug(f"Cache miss for key: {key}")
        return None
    except Exception as e:
        logger.error(f"Error getting cache for key {key}: {e}")
        return None

async def delete_cache(key: str):
    """Delete a key from the cache."""
    try:
        redis = await get_redis_client()
        await redis.delete(key)
        logger.debug(f"Cache deleted for key: {key}")
    except Exception as e:
        logger.error(f"Error deleting cache for key {key}: {e}")
        
async def refresh_asset_cache(asset_id: int, ticker: str):
    """
    Refresh the cache for a specific asset.
    """
    key = f"asset:{asset_id}:price"
    
    # In a real scenario, you would fetch from Yahoo Finance here
    # For now, let's just delete the key
    await delete_cache(key)
    logger.info(f"Cache refreshed for asset {asset_id} ({ticker})")