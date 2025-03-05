import asyncio
from functools import wraps
from typing import TypeVar, Callable

T = TypeVar('T')


def async_retry(
        retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            return await func(*args, **kwargs)

        return wrapper

    return decorator
