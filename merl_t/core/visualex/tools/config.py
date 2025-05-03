"""
VisuaLex configuration constants
"""

from merl_t.config import get_config_manager

# Get config manager
config = get_config_manager()

# Rate limiting
RATE_LIMIT = config.get("visualex.client.rate_limit", 10)
RATE_LIMIT_WINDOW = config.get("visualex.client.rate_limit_window", 60)  # seconds

# History
HISTORY_LIMIT = config.get("visualex.client.history_limit", 100)

# Cache settings
CACHE_ENABLED = config.get("visualex.cache.enabled", True)
CACHE_TTL = config.get("visualex.cache.ttl", 3600)  # 1 hour
MAX_CACHE_SIZE = config.get("visualex.cache.max_size", 1000)
