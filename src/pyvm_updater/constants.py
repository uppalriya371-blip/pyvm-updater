# Configuration and constants for pyvm_updater
"""Constants and configuration for pyvm_updater."""

from .paths import get_cache_dir, get_data_dir

# Network configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
DOWNLOAD_TIMEOUT = 120  # seconds
REQUEST_TIMEOUT = 15  # seconds

# History file location (XDG_DATA_HOME/pyvm/history.json)
HISTORY_FILE = get_data_dir() / "history.json"

# Local metadata cache (XDG_CACHE_HOME/pyvm/metadata.sqlite)
METADATA_DB = get_cache_dir() / "metadata.sqlite"
METADATA_TTL_SECONDS = 24 * 60 * 60  # 24h TTL for cached metadata
