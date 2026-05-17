"""Tests for pyvm venv duplicate command."""

import json
from unittest.mock import patch

import pytest

from pyvm_updater.venv import _fix_venv_paths, duplicate_venv


@pytest.fixture
def venv_dir(tmp_path):
    """Create a temporary venv directory and registry."""
    venvs = tmp_path / "venvs"
    venvs.mkdir()
    registry_file = tmp_path / "venvs.json"
    return venvs, registry_file


def _make_fake_venv(venv_dir, name):
    """Create a fake venv directory with activate scripts and pyvenv.cfg."""
    venv_path = venv_dir / name
    bin_dir = venv_path / "bin"
    bin_dir.mkdir(parents=True)

    # Create activate script with hardcoded path
    activate = bin_dir / "activate"
    activate.write_text(f'VIRTUAL_ENV="{venv_path}"\nexport VIRTUAL_ENV\n')

    # Create pyvenv.cfg
    cfg = venv_path / "pyvenv.cfg"
    cfg.write_text("home = /usr/bin\ninclude-system-site-packages = false\n")

    return venv_path


def _patch_venv(venv_dir, registry_file):
    """Return context managers for patching venv module globals."""
    return {
        "pyvm_updater.venv.get_venv_dir": lambda: venv_dir,
        "pyvm_updater.venv.VENV_REGISTRY": registry_file,
    }


def _apply_patches(patches):
    """Helper to create nested patch context managers."""
    keys = list(patches.keys())
    return patch(keys[0], patches[keys[0]]), patch(keys[1], patches[keys[1]])


class TestDuplicateVenv:

    def test_duplicate_registered_venv(self, venv_dir):
        venvs, registry_file = venv_dir
        source_path = _make_fake_venv(venvs, "base-env")

        registry = {
            "base-env": {
                "path": str(source_path),
                "python_version": "3.13",
                "python_executable": "/usr/bin/python",
                "system_site_packages": False,
            }
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("base-env", "experimental-env")

        assert success is True
        assert "Duplicated" in msg

        # Both exist on disk
        assert source_path.exists()
        assert (venvs / "experimental-env").exists()
        assert (venvs / "experimental-env" / "bin" / "activate").exists()

        # Registry has both
        reg = json.loads(registry_file.read_text())
        assert "base-env" in reg
        assert "experimental-env" in reg
        assert reg["experimental-env"]["python_version"] == "3.13"
        assert "experimental-env" in reg["experimental-env"]["path"]

    def test_duplicate_source_not_found(self, venv_dir):
        venvs, registry_file = venv_dir
        registry_file.write_text("{}")

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("ghost", "new-name")

        assert success is False
        assert "not found" in msg

    def test_duplicate_new_name_in_registry(self, venv_dir):
        venvs, registry_file = venv_dir
        _make_fake_venv(venvs, "aaa")

        registry = {
            "aaa": {"path": str(venvs / "aaa"), "python_version": "3.12"},
            "bbb": {"path": str(venvs / "bbb"), "python_version": "3.12"},
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("aaa", "bbb")

        assert success is False
        assert "already exists" in msg

    def test_duplicate_new_dir_exists(self, venv_dir):
        venvs, registry_file = venv_dir
        _make_fake_venv(venvs, "aaa")
        _make_fake_venv(venvs, "bbb")

        registry = {"aaa": {"path": str(venvs / "aaa"), "python_version": "3.12"}}
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("aaa", "bbb")

        assert success is False
        assert "already exists" in msg

    def test_duplicate_fixes_activate_paths(self, venv_dir):
        """Activate script in the copy should reference the new path."""
        venvs, registry_file = venv_dir
        source_path = _make_fake_venv(venvs, "original")

        registry = {
            "original": {"path": str(source_path), "python_version": "3.13"},
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("original", "clone")

        assert success is True

        new_activate = venvs / "clone" / "bin" / "activate"
        text = new_activate.read_text()
        assert str(venvs / "clone") in text
        assert str(venvs / "original") not in text

    def test_duplicate_fixes_script_wrappers(self, venv_dir):
        """Scripts like pip should have their shebang/path updated."""
        venvs, registry_file = venv_dir
        source_path = _make_fake_venv(venvs, "original")

        # Make a fake pip script
        bin_dir = source_path / "bin"
        pip_script = bin_dir / "pip"
        pip_script.write_text(f"#!{source_path}/bin/python\nprint('pip')")

        # Make a fake binary executable (like pip.exe)
        pip_exe = bin_dir / "pip.exe"
        old_bytes = str(source_path).encode("utf-8")
        pip_exe.write_bytes(b"PK\x03\x04" + old_bytes + b"\x00\x01")

        registry = {
            "original": {"path": str(source_path), "python_version": "3.13"},
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("original", "clone")

        assert success is True

        new_pip = venvs / "clone" / "bin" / "pip"
        assert str(venvs / "clone") in new_pip.read_text()
        assert str(venvs / "original") not in new_pip.read_text()

        new_pip_exe = venvs / "clone" / "bin" / "pip.exe"
        assert str(venvs / "clone").encode("utf-8") in new_pip_exe.read_bytes()
        assert str(venvs / "original").encode("utf-8") not in new_pip_exe.read_bytes()

    def test_duplicate_unregistered_venv(self, venv_dir):
        """Venv on disk but not in registry should still be duplicated."""
        venvs, registry_file = venv_dir
        _make_fake_venv(venvs, "orphan")
        registry_file.write_text("{}")

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            success, msg = duplicate_venv("orphan", "adopted")

        assert success is True
        assert (venvs / "adopted").exists()

        reg = json.loads(registry_file.read_text())
        assert "adopted" in reg

    def test_duplicate_preserves_source(self, venv_dir):
        """Source venv should remain untouched after duplication."""
        venvs, registry_file = venv_dir
        source_path = _make_fake_venv(venvs, "keep-me")

        registry = {
            "keep-me": {"path": str(source_path), "python_version": "3.13"},
        }
        registry_file.write_text(json.dumps(registry))

        patches = _patch_venv(venvs, registry_file)
        p1, p2 = _apply_patches(patches)
        with p1, p2:
            duplicate_venv("keep-me", "copy")

        # Source still intact
        assert source_path.exists()
        activate_text = (source_path / "bin" / "activate").read_text()
        assert str(source_path) in activate_text


class TestFixVenvPaths:

    def test_replaces_old_path_in_activate(self, tmp_path):
        old_path = tmp_path / "old-env"
        new_path = tmp_path / "new-env"
        new_path.mkdir()
        bin_dir = new_path / "bin"
        bin_dir.mkdir()

        activate = bin_dir / "activate"
        activate.write_text(f'VIRTUAL_ENV="{old_path}"\n')

        _fix_venv_paths(new_path, old_path)

        text = activate.read_text()
        assert str(new_path) in text
        assert str(old_path) not in text

    def test_handles_missing_scripts(self, tmp_path):
        """Should not crash if some activate scripts don't exist."""
        old_path = tmp_path / "old"
        new_path = tmp_path / "new"
        new_path.mkdir()

        # Should not raise
        _fix_venv_paths(new_path, old_path)
