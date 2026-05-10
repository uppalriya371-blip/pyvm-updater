"""Tests for pyvm_updater.paths module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pyvm_updater.paths import (
    get_cache_dir,
    get_config_dir,
    get_config_file,
    get_data_dir,
    get_history_file,
    get_metadata_db,
    get_plugins_dir,
    get_venv_dir,
    get_venv_registry_file,
    migrate_legacy_paths,
)


class TestXDGPaths:
    """Tests for XDG path resolution."""

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_config_dir_default(self, mock_win):
        """Test default config dir on Linux/macOS."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_config_dir()
            assert result == Path.home() / ".config" / "pyvm"

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_config_dir_xdg_override(self, mock_win):
        """Test config dir respects XDG_CONFIG_HOME."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": "/custom/config"}):
            result = get_config_dir()
            assert result == Path("/custom/config/pyvm")

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_data_dir_default(self, mock_win):
        """Test default data dir on Linux/macOS."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_data_dir()
            assert result == Path.home() / ".local" / "share" / "pyvm"

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_data_dir_xdg_override(self, mock_win):
        """Test data dir respects XDG_DATA_HOME."""
        with patch.dict("os.environ", {"XDG_DATA_HOME": "/custom/data"}):
            result = get_data_dir()
            assert result == Path("/custom/data/pyvm")

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_cache_dir_default(self, mock_win):
        """Test default cache dir on Linux/macOS."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_cache_dir()
            assert result == Path.home() / ".cache" / "pyvm"

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_cache_dir_xdg_override(self, mock_win):
        """Test cache dir respects XDG_CACHE_HOME."""
        with patch.dict("os.environ", {"XDG_CACHE_HOME": "/custom/cache"}):
            result = get_cache_dir()
            assert result == Path("/custom/cache/pyvm")

    @patch("pyvm_updater.paths._is_windows", return_value=True)
    def test_windows_uses_localappdata(self, mock_win):
        """Test Windows paths use LOCALAPPDATA."""
        with patch.dict("os.environ", {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}):
            config = get_config_dir()
            data = get_data_dir()
            cache = get_cache_dir()
            assert "AppData" in str(config)
            assert "AppData" in str(data)
            assert "AppData" in str(cache)


class TestConcreteFilePaths:
    """Tests for concrete file path helpers."""

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_history_file(self, mock_win):
        with patch.dict("os.environ", {}, clear=True):
            result = get_history_file()
            assert result.name == "history.json"
            assert "pyvm" in str(result)

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_metadata_db(self, mock_win):
        with patch.dict("os.environ", {}, clear=True):
            result = get_metadata_db()
            assert result.name == "metadata.sqlite"
            assert ".cache" in str(result)

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_venv_dir(self, mock_win):
        with patch.dict("os.environ", {}, clear=True):
            result = get_venv_dir()
            assert result.name == "venvs"

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_venv_registry(self, mock_win):
        with patch.dict("os.environ", {}, clear=True):
            result = get_venv_registry_file()
            assert result.name == "venvs.json"

    @patch("pyvm_updater.paths._is_windows", return_value=False)
    def test_plugins_dir(self, mock_win):
        with patch.dict("os.environ", {}, clear=True):
            result = get_plugins_dir()
            assert result.name == "plugins"
            assert ".config" in str(result)


class TestMigration:
    """Tests for legacy path migration."""

    @pytest.fixture
    def migration_env(self, tmp_path):
        """Set up a fake home with legacy files and XDG targets."""
        home = tmp_path / "home"
        home.mkdir()

        # Create legacy files
        legacy_history = home / ".pyvm_history.json"
        legacy_history.write_text('[{"action": "install", "version": "3.12.1"}]')

        legacy_metadata = home / ".pyvm_metadata.sqlite"
        legacy_metadata.write_bytes(b"fake sqlite data")

        legacy_pyvm = home / ".pyvm"
        legacy_pyvm.mkdir()
        (legacy_pyvm / "venvs.json").write_text('{"myenv": {}}')
        venvs = legacy_pyvm / "venvs"
        venvs.mkdir()
        (venvs / "myenv").mkdir()
        (venvs / "myenv" / "pyvenv.cfg").write_text("home = /usr/bin")

        # XDG targets
        data_dir = tmp_path / "data" / "pyvm"
        cache_dir = tmp_path / "cache" / "pyvm"

        return {
            "home": home,
            "data_dir": data_dir,
            "cache_dir": cache_dir,
            "legacy_history": legacy_history,
            "legacy_metadata": legacy_metadata,
            "legacy_pyvm": legacy_pyvm,
        }

    def test_migration_moves_files(self, migration_env):
        """Test that migration moves legacy files to XDG locations."""
        env = migration_env

        with patch("pyvm_updater.paths.get_data_dir", return_value=env["data_dir"]):
            with patch("pyvm_updater.paths.get_cache_dir", return_value=env["cache_dir"]):
                with patch("pyvm_updater.paths.get_history_file", return_value=env["data_dir"] / "history.json"):
                    with patch("pyvm_updater.paths.get_metadata_db", return_value=env["cache_dir"] / "metadata.sqlite"):
                        with patch("pyvm_updater.paths.get_venv_registry_file", return_value=env["data_dir"] / "venvs.json"):
                            with patch("pyvm_updater.paths.get_venv_dir", return_value=env["data_dir"] / "venvs"):
                                with patch("pyvm_updater.paths._LEGACY_PATHS", {
                                    "history": env["legacy_history"],
                                    "metadata": env["legacy_metadata"],
                                    "venv_dir": env["legacy_pyvm"] / "venvs",
                                    "venv_registry": env["legacy_pyvm"] / "venvs.json",
                                    "config_dir": env["home"] / ".config" / "pyvm",
                                    "config_file": env["home"] / ".config" / "pyvm" / "config.toml",
                                }):
                                    with patch("pyvm_updater.paths._migration_done", return_value=False):
                                        with patch("pyvm_updater.paths._mark_migration_done"):
                                            migrate_legacy_paths()

        # Verify files moved
        assert (env["data_dir"] / "history.json").exists()
        assert (env["cache_dir"] / "metadata.sqlite").exists()
        assert (env["data_dir"] / "venvs.json").exists()
        assert (env["data_dir"] / "venvs" / "myenv" / "pyvenv.cfg").exists()

        # Verify old files are gone
        assert not env["legacy_history"].exists()
        assert not env["legacy_metadata"].exists()

    def test_migration_skips_if_already_done(self, migration_env):
        """Test that migration doesn't run twice."""
        env = migration_env

        with patch("pyvm_updater.paths._migration_done", return_value=True):
            migrate_legacy_paths()

        # Legacy files should still exist (not moved)
        assert env["legacy_history"].exists()
        assert env["legacy_metadata"].exists()

    def test_migration_handles_missing_legacy_files(self, tmp_path):
        """Test migration gracefully handles non-existent legacy files."""
        data_dir = tmp_path / "data" / "pyvm"

        with patch("pyvm_updater.paths.get_data_dir", return_value=data_dir):
            with patch("pyvm_updater.paths._LEGACY_PATHS", {
                "history": tmp_path / "nonexistent.json",
                "metadata": tmp_path / "nonexistent.sqlite",
                "venv_dir": tmp_path / "nonexistent_dir",
                "venv_registry": tmp_path / "nonexistent_registry.json",
                "config_dir": tmp_path / "nonexistent_config",
                "config_file": tmp_path / "nonexistent_config" / "config.toml",
            }):
                with patch("pyvm_updater.paths._migration_done", return_value=False):
                    with patch("pyvm_updater.paths._mark_migration_done"):
                        # Should not raise
                        migrate_legacy_paths()
