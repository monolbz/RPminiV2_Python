"""
Cache management module for route optimizer.
Handles caching of Google Maps API responses to reduce costs.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta


# Cache configuration
CACHE_DIR = Path('.cache')
CACHE_EXPIRY_DAYS = 30  # Cache entries expire after 30 days


def init_cache():
    """Initialize cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(exist_ok=True)


def generate_cache_key(params):
    """
    Generate a unique cache key from API parameters.

    Args:
        params: Dictionary of parameters to hash

    Returns:
        String MD5 hash of the parameters
    """
    # Sort params for consistent hashing
    sorted_params = json.dumps(params, sort_keys=True)
    return hashlib.md5(sorted_params.encode()).hexdigest()


def get_from_cache(cache_key):
    """
    Retrieve data from cache if it exists and is not expired.

    Args:
        cache_key: The cache key to look up

    Returns:
        Cached data or None if not found or expired
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)

        # Check if cache entry has expired
        cached_time = datetime.fromisoformat(cached_data['timestamp'])
        expiry_time = cached_time + timedelta(days=CACHE_EXPIRY_DAYS)

        if datetime.now() > expiry_time:
            # Cache expired, delete it
            cache_file.unlink()
            return None

        return cached_data['data']

    except (json.JSONDecodeError, KeyError, ValueError):
        # Invalid cache file, delete it
        cache_file.unlink()
        return None


def save_to_cache(cache_key, data):
    """
    Save data to cache with current timestamp.

    Args:
        cache_key: The cache key to save under
        data: The data to cache
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"

    cache_entry = {
        'timestamp': datetime.now().isoformat(),
        'data': data
    }

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_entry, f, indent=2)
