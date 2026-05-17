"""Tests for colorized list output."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from pyvm_updater.cli import _status_color, cli


class TestStatusColor:
    """Tests for the _status_color helper."""

    def test_bugfix_is_green(self):
        assert _status_color("bugfix") == "green"

    def test_active_is_green(self):
        assert _status_color("active") == "green"

    def test_security_is_yellow(self):
        assert _status_color("security") == "yellow"

    def test_eol_is_red(self):
        assert _status_color("end of life") == "red"
        assert _status_color("end-of-life, last release was 3.9.25") == "red"

    def test_prerelease_is_cyan(self):
        assert _status_color("pre-release") == "cyan"

    def test_unknown_is_white(self):
        assert _status_color("something else") == "white"

    def test_case_insensitive(self):
        assert _status_color("BUGFIX") == "green"
        assert _status_color("Security") == "yellow"
        assert _status_color("End Of Life") == "red"


class TestListNoColor:
    """Tests for --no-color flag."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch("pyvm_updater.cli.get_active_python_releases")
    def test_no_color_omits_legend(self, mock_releases, runner):
        mock_releases.return_value = [
            {
                "series": "3.13",
                "latest_version": "3.13.0",
                "status": "bugfix",
                "end_of_support": "2029-10",
            },
        ]
        result = runner.invoke(cli, ["list", "--no-color"])
        assert result.exit_code == 0
        assert "●" not in result.output

    @patch("pyvm_updater.cli.get_active_python_releases")
    def test_default_includes_legend(self, mock_releases, runner):
        mock_releases.return_value = [
            {
                "series": "3.13",
                "latest_version": "3.13.0",
                "status": "bugfix",
                "end_of_support": "2029-10",
            },
        ]
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "stable" in result.output
        assert "security" in result.output
        assert "end-of-life" in result.output
        assert "pre-release" in result.output
