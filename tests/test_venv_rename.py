"""Tests for pyvm venv rename command."""

import json
from unittest.mock import patch

import pytest

from pyvm_updater.venv import rename_venv


@pytest.fixture
def venv_dir(tmp_path):
    """Create a temporary venv directory and registry."""
    venvs = tmp_path / "venvs"
    venvs.mkdir()
    registry_file = tmp_path / "venvs.json"
    return venvs, registry_file


def _make_fake_venv(venv_dir, name):
    """Create a fake venv directory with an activate script."""
    venv_path = venv_dir / name
    (venv_path / "bin").mkdir(parents=True)
    (venv_path / "bin" / "activate").touch()
    return venv_path


def _patch_venv(venv_dir, registry_file):
    """Return a dict of patches for venv module globals."""
    return {
        "pyvm_updater.venv.get_venv_dir": lambda: venv_dir,
        "pyvm_updater.venv.VENV_REGISTRY": registry_file,
    }


class TestRenameVenv:

    def test_rename_registered_venv(self, venv_dir):
        venvs, registry_file = venv_dir
        old_path = _make_fake_venv(venvs, "old-project")

        registry = {
            "old-project": {
                "path": str(old_path),
                "python_version": "3.13",
                "python_executable": "/usr/bin/python",
            }
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        with (
            patch(list(patches.keys())[0], patches[list(patches.keys())[0]]),
            patch(list(patches.keys())[1], patches[list(patches.keys())[1]]),
        ):
            success, msg = rename_venv("old-project", "new-project")

        assert success is True
        assert "Renamed" in msg

        # Disk: old gone, new exists
        assert not (venvs / "old-project").exists()
        assert (venvs / "new-project").exists()

        # Registry updated
        reg = json.loads(registry_file.read_text())
        assert "old-project" not in reg
        assert "new-project" in reg
        assert reg["new-project"]["python_version"] == "3.13"
        assert "new-project" in reg["new-project"]["path"]

    def test_rename_old_not_found(self, venv_dir):
        venvs, registry_file = venv_dir
        registry_file.write_text("{}")

        patches = _patch_venv(venvs, registry_file)
        with (
            patch(list(patches.keys())[0], patches[list(patches.keys())[0]]),
            patch(list(patches.keys())[1], patches[list(patches.keys())[1]]),
        ):
            success, msg = rename_venv("ghost", "new-name")

        assert success is False
        assert "not found" in msg

    def test_rename_new_name_already_in_registry(self, venv_dir):
        venvs, registry_file = venv_dir
        _make_fake_venv(venvs, "aaa")

        registry = {
            "aaa": {"path": str(venvs / "aaa"), "python_version": "3.12"},
            "bbb": {"path": str(venvs / "bbb"), "python_version": "3.12"},
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        with (
            patch(list(patches.keys())[0], patches[list(patches.keys())[0]]),
            patch(list(patches.keys())[1], patches[list(patches.keys())[1]]),
        ):
            success, msg = rename_venv("aaa", "bbb")

        assert success is False
        assert "already exists" in msg

    def test_rename_new_dir_already_exists(self, venv_dir):
        venvs, registry_file = venv_dir
        _make_fake_venv(venvs, "aaa")
        _make_fake_venv(venvs, "bbb")

        registry = {"aaa": {"path": str(venvs / "aaa"), "python_version": "3.12"}}
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        with (
            patch(list(patches.keys())[0], patches[list(patches.keys())[0]]),
            patch(list(patches.keys())[1], patches[list(patches.keys())[1]]),
        ):
            success, msg = rename_venv("aaa", "bbb")

        assert success is False
        assert "already exists" in msg

    def test_rename_stale_registry_entry(self, venv_dir):
        """Registry entry exists but folder is gone -- just update registry."""
        venvs, registry_file = venv_dir

        registry = {
            "stale": {"path": str(venvs / "stale"), "python_version": "3.11"},
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        with (
            patch(list(patches.keys())[0], patches[list(patches.keys())[0]]),
            patch(list(patches.keys())[1], patches[list(patches.keys())[1]]),
        ):
            success, msg = rename_venv("stale", "fresh")

        assert success is True
        reg = json.loads(registry_file.read_text())
        assert "stale" not in reg
        assert "fresh" in reg

    def test_rename_unregistered_venv_on_disk(self, venv_dir):
        """Folder exists but not in registry -- move and register."""
        venvs, registry_file = venv_dir
        _make_fake_venv(venvs, "orphan")
        registry_file.write_text("{}")

        patches = _patch_venv(venvs, registry_file)
        with (
            patch(list(patches.keys())[0], patches[list(patches.keys())[0]]),
            patch(list(patches.keys())[1], patches[list(patches.keys())[1]]),
        ):
            success, msg = rename_venv("orphan", "adopted")

        assert success is True
        assert not (venvs / "orphan").exists()
        assert (venvs / "adopted").exists()

        reg = json.loads(registry_file.read_text())
        assert "adopted" in reg
