import asyncio
import functools
import logging
import uuid
import time
import inspect
import json

logger = logging.getLogger("crud_logs")

def mask_sensitive_data(data, sensitive_keys={"password", "api_key", "token"}):
    """Recursively mask sensitive fields in the data."""
    if isinstance(data, dict):
        return {k: mask_sensitive_data(v, sensitive_keys) if k not in sensitive_keys else "****" for k, v in data.items()}
    if isinstance(data, list):
        return [mask_sensitive_data(i, sensitive_keys) for i in data]
    return data

def log_action(action_name, tags=None):
    """Decorator to log actions with enhanced features."""
    tags = tags or {}

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await log_action_wrapper(func, args, kwargs, action_name, tags)

        def sync_wrapper(*args, **kwargs):
            return log_action_wrapper(func, args, kwargs, action_name, tags)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

def log_action_wrapper(func, args, kwargs, action_name, tags):
    """Wrapper function to handle logging for both sync and async functions."""
    correlation_id = kwargs.get("correlation_id", str(uuid.uuid4()))
    start_time = time.time()

    sanitized_args = mask_sensitive_data(args)
    sanitized_kwargs = mask_sensitive_data(kwargs)

    log_data = {
        "action": action_name,
        "correlation_id": correlation_id,
        "args": sanitized_args,
        "kwargs": sanitized_kwargs,
        "tags": tags,
        "status": "started",
    }
    logger.info(json.dumps(log_data))

    try:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = asyncio.run(result)

        duration = time.time() - start_time
        log_data.update({
            "status": "succeeded",
            "result": result,
            "duration": f"{duration:.2f}s",
        })
        logger.info(json.dumps(log_data))
        return result
    except Exception as e:
        duration = time.time() - start_time
        log_data.update({
            "status": "failed",
            "error": str(e),
            "duration": f"{duration:.2f}s",
        })
        logger.error(json.dumps(log_data), exc_info=True)
        raise
