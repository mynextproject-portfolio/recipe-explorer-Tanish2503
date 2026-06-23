import os
import time

from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request):
    """Use a unique key per request in test mode to bypass rate limiting."""
    if os.getenv("TESTING") == "1":
        return f"test-{time.time_ns()}"
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
