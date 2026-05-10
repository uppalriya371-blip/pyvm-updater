"""Centralized path resolution following XDG Base Directory Specification.

On Linux/macOS:
    Config  -> $XDG_CONFIG_HOME/pyvm  (default: ~/.config/pyvm)
    Data    -> $XDG_DATA_HOME/pyvm    (default: ~/.local/share/pyvm)
    Cache   -> $XDG_CACHE_HOME/pyvm   (default: ~/.cache/pyvm)

On Windows:
    All     -> %LOCALAPPDATA%/pyvm
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
from pathlib import Path

log = logging.getLogger("pyvm.paths")

_APP_NAME = "pyvm"


def _is_windows() -> bool:
    return platform.system() == "Windows"


# --- XDG directory resolution ---


def get_config_dir() -> Path:
    """Return the configuration directory for pyvm."""
    if _is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / _APP_NAME / "config"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / _APP_NAME
    return Path.home() / ".config" / _APP_NAME


def get_data_dir() -> Path:
    """Return the data directory for pyvm (history, venvs, registry)."""
    if _is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / _APP_NAME / "data"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / _APP_NAME
    return Path.home() / ".local" / "share" / _APP_NAME


def get_cache_dir() -> Path:
    """Return the cache directory for pyvm (metadata sqlite)."""
    if _is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / _APP_NAME / "cache"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / _APP_NAME
    return Path.home() / ".cache" / _APP_NAME


# --- Concrete file paths ---


def get_config_file() -> Path:
    return get_config_dir() / "config.toml"


def get_history_file() -> Path:
    return get_data_dir() / "history.json"


def get_metadata_db() -> Path:
    return get_cache_dir() / "metadata.sqlite"


def get_venv_dir() -> Path:
    return get_data_dir() / "venvs"


def get_venv_registry_file() -> Path:
    return get_data_dir() / "venvs.json"


def get_plugins_dir() -> Path:
    return get_config_dir() / "plugins"


# --- Legacy paths (pre-XDG) ---

_LEGACY_PATHS = {
    "history": Path.home() / ".pyvm_history.json",
    "metadata": Path.home() / ".pyvm_metadata.sqlite",
    "venv_dir": Path.home() / ".pyvm" / "venvs",
    "venv_registry": Path.home() / ".pyvm" / "venvs.json",
    "config_dir": Path.home() / ".config" / "pyvm",
    "config_file": Path.home() / ".config" / "pyvm" / "config.toml",
}


# --- Migration ---

_MIGRATED_FLAG = ".migrated_xdg"


def _migration_done() -> bool:
    """Check if migration has already been performed."""
    return (get_data_dir() / _MIGRATED_FLAG).exists()


def _mark_migration_done() -> None:
    """Write a flag file so migration only runs once."""
    get_data_dir().mkdir(parents=True, exist_ok=True)
    (get_data_dir() / _MIGRATED_FLAG).touch()


def _move_file(src: Path, dst: Path) -> bool:
    """Move a single file from src to dst. Returns True on success."""
    if not src.exists():
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        log.info(f"Migrated {src} -> {dst}")
        return True
    except (OSError, shutil.Error) as e:
        log.warning(f"Failed to migrate {src} -> {dst}: {e}")
        return False


def _move_directory(src: Path, dst: Path) -> bool:
    """Move a directory tree from src to dst. Returns True on success."""
    if not src.exists() or not src.is_dir():
        return False
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # Merge contents if destination already exists
            for item in src.iterdir():
                target = dst / item.name
                if not target.exists():
                    shutil.move(str(item), str(target))
            shutil.rmtree(str(src), ignore_errors=True)
        else:
            shutil.move(str(src), str(dst))
        log.info(f"Migrated {src} -> {dst}")
        return True
    except (OSError, shutil.Error) as e:
        log.warning(f"Failed to migrate {src} -> {dst}: {e}")
        return False


def migrate_legacy_paths() -> None:
    """Migrate data from old locations to XDG-compliant paths.

    This runs once on first launch after the update. It moves files
    from the legacy locations to the new XDG directories and writes
    a flag file to prevent running again.
    """
    if _migration_done():
        return

    migrated_any = False

    # History file
    old_history = _LEGACY_PATHS["history"]
    if old_history.exists():
        if _move_file(old_history, get_history_file()):
            migrated_any = True

    # Metadata cache
    old_metadata = _LEGACY_PATHS["metadata"]
    if old_metadata.exists():
        if _move_file(old_metadata, get_metadata_db()):
            migrated_any = True

    # Venv registry
    old_registry = _LEGACY_PATHS["venv_registry"]
    if old_registry.exists():
        if _move_file(old_registry, get_venv_registry_file()):
            migrated_any = True

    # Venv directory
    old_venv_dir = _LEGACY_PATHS["venv_dir"]
    if old_venv_dir.exists() and old_venv_dir.is_dir():
        if _move_directory(old_venv_dir, get_venv_dir()):
            migrated_any = True

    # Clean up empty ~/.pyvm directory if it's now empty
    old_pyvm_dir = Path.home() / ".pyvm"
    if old_pyvm_dir.exists() and old_pyvm_dir.is_dir():
        try:
            if not any(old_pyvm_dir.iterdir()):
                old_pyvm_dir.rmdir()
        except OSError:
            pass

    if migrated_any:
        log.info("Legacy file migration complete.")

    _mark_migration_done()


def ensure_directories() -> None:
    """Create all XDG directories if they don't exist."""
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_cache_dir().mkdir(parents=True, exist_ok=True)
