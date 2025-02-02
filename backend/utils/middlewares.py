from fastapi import FastAPI, Request, HTTPException, Depends, status
from slowapi.util import get_remote_address
from redis import asyncio as aioredis
from dotenv import load_dotenv
import os
import logging

from settings import settings
from schema.user import UserInDB
from auth.authorization import get_current_active_user


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def check_password_changed(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Restrict access to users who have not changed their password after the first login.
    """
    if not current_user.password_changed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must change your password before accessing this resource.",
        )


class SecurityMiddleware:
    def __init__(self):
        self.redis = None  # Async Redis client

        # Load settings from environment variables
        self.max_requests_per_minute = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 60))
        self.block_time = int(os.getenv("BLOCK_TIME", 300))
        self.max_failed_attempts = int(os.getenv("MAX_FAILED_ATTEMPTS", 3))
        self.failed_attempts_expiration = int(os.getenv("FAILED_ATTEMPTS_EXPIRATION", 3600))
        self.request_expiration = int(os.getenv("REQUEST_EXPIRATION", 60))

    async def setup_redis(self):
        """Initialize async Redis connection."""
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None  # Disable Redis if connection fails

    async def __call__(self, request: Request, call_next):
        """Global Rate Limiting Middleware"""
        if not self.redis:
            logger.warning("Redis unavailable, skipping rate limiting.")
            return await call_next(request)

        ip = get_remote_address(request)
        user_id = request.headers.get("Authorization", f"ip:{ip}")  # Use user token if available
        blocked_key = f"security:blocked:{user_id}"
        requests_key = f"security:requests:{user_id}"

        # Check if the user/IP is blocked
        if await self.redis.exists(blocked_key):
            time_left = await self.redis.ttl(blocked_key)
            logger.warning(f"Blocked request from {user_id}. Time left: {time_left} seconds.")
            raise HTTPException(
                status_code=403,
                detail=f"Too many requests. Try again in {time_left} seconds.",
            )

        # Get request count
        request_count = await self.get_int_value(requests_key)

        # If the user/IP exceeds rate limit, block them
        if request_count >= self.max_requests_per_minute:
            await self.redis.set(blocked_key, "1", ex=self.block_time)
            logger.warning(f"User {user_id} blocked for {self.block_time} seconds due to rate limit.")
            raise HTTPException(
                status_code=403,
                detail="Too many requests. Try again later.",
            )

        # Increment request count in Redis using a pipeline
        async with self.redis.pipeline() as pipe:
            pipe.incr(requests_key)
            pipe.expire(requests_key, self.request_expiration)
            await pipe.execute()

        response = await call_next(request)
        return response

    async def is_locked(self, username: str) -> bool:
        """Check if a user is locked due to too many failed login attempts."""
        if not self.redis:
            return False  # Fail-safe mode
        lock_key = f"security:locked:{username}"
        return await self.redis.exists(lock_key)

    async def track_failed_login(self, username: str) -> int:
        """Track failed login attempts for a user."""
        if not self.redis:
            return 0  # Fail-safe mode

        failed_attempts_key = f"security:failed_attempts:{username}"
        failed_attempts = await self.get_int_value(failed_attempts_key)

        # Increment failed attempts using a pipeline
        async with self.redis.pipeline() as pipe:
            pipe.incr(failed_attempts_key)
            pipe.expire(failed_attempts_key, self.failed_attempts_expiration)
            await pipe.execute()

        logger.info(f"User {username} failed login attempt {failed_attempts + 1}/{self.max_failed_attempts}")
        return failed_attempts + 1

    async def lock_user(self, username: str):
        """Lock a user with an exponentially increasing ban time after multiple failures."""
        if not self.redis:
            return  # Fail-safe mode

        lock_key = f"security:locked:{username}"
        previous_ban_time = await self.get_int_value(lock_key)
        new_ban_time = max(previous_ban_time * 2, self.block_time)  # Exponential backoff

        await self.redis.set(lock_key, "1", ex=new_ban_time)
        logger.warning(f"User {username} is locked for {new_ban_time} seconds.")

    async def get_int_value(self, key: str) -> int:
        """Helper function to safely get an integer value from Redis."""
        try:
            value = await self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            logger.error(f"Redis error: {e}")
            return 0  # Fail-safe mode

security_middleware = SecurityMiddleware()
