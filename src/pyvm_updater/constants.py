# Configuration and constants for pyvm_updater
"""Constants and configuration for pyvm_updater."""

from pathlib import Path

# Network configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
DOWNLOAD_TIMEOUT = 120  # seconds
REQUEST_TIMEOUT = 15  # seconds

# History file location
HISTORY_FILE = Path.home() / ".pyvm_history.json"

# Local metadata cache (versions, security, EOL)
METADATA_DB = Path.home() / ".pyvm_metadata.sqlite"
METADATA_TTL_SECONDS = 24 * 60 * 60  # 24h TTL for cached metadata
