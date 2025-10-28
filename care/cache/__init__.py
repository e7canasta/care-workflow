from redis.exceptions import ConnectionError, TimeoutError

from care.logger import logger
from care.cache.memory import MemoryCache
from care.cache.redis import RedisCache
from care.env import REDIS_HOST, REDIS_PORT, REDIS_SSL, REDIS_TIMEOUT

if REDIS_HOST is not None:
    try:
        cache = RedisCache(
            host=REDIS_HOST, port=REDIS_PORT, ssl=REDIS_SSL, timeout=REDIS_TIMEOUT
        )
        logger.info(f"Redis Cache initialised")
    except (TimeoutError, ConnectionError):
        logger.error(
            f"Could not connect to Redis under {REDIS_HOST}:{REDIS_PORT}. MemoryCache to be used."
        )
        cache = MemoryCache()
        logger.info(f"Memory Cache initialised")
else:
    cache = MemoryCache()
    logger.info(f"Memory Cache initialised")
