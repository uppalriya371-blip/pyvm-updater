"""Tests for progress spinner on check, list, and update commands."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from pyvm_updater.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCheckSpinner:
    """Tests for spinner on pyvm check."""

    @patch("pyvm_updater.cli.check_python_version")
    def test_check_shows_version_report(self, mock_check, runner):
        mock_check.return_value = ("3.13.0", "3.13.0", False)
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 0
        assert "Python Version Check Report" in result.output
        assert "3.13.0" in result.output
        assert "You are up-to-date" in result.output or "up-to-date" in result.output

    @patch("pyvm_updater.cli.check_python_version")
    def test_check_calls_silent_true(self, mock_check, runner):
        mock_check.return_value = ("3.13.0", "3.14.0", True)
        runner.invoke(cli, ["check"])
        mock_check.assert_called_once_with(silent=True)

    @patch("pyvm_updater.cli.check_python_version")
    def test_check_update_available_message(self, mock_check, runner):
        mock_check.return_value = ("3.12.0", "3.14.0", True)
        result = runner.invoke(cli, ["check"])
        assert "new version" in result.output.lower() or "3.14.0" in result.output
        assert "pyvm update" in result.output

    @patch("pyvm_updater.cli.check_python_version")
    def test_check_fetch_failure(self, mock_check, runner):
        mock_check.return_value = ("3.13.0", None, False)
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 1
        assert "Could not fetch latest version information" in result.output


class TestListSpinner:
    """Tests for spinner on pyvm list."""

    @patch("pyvm_updater.cli.get_active_python_releases")
    def test_list_no_fetching_text(self, mock_releases, runner):
        """Spinner replaces the old 'Fetching Python versions...' text."""
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
        # The old static text should not appear
        assert "Fetching Python versions..." not in result.output
        # But the table should still be there
        assert "SERIES" in result.output
        assert "3.13" in result.output


class TestUpdateSpinner:
    """Tests for spinner on pyvm update."""

    @patch("pyvm_updater.cli.check_python_version")
    def test_update_no_update_message(self, mock_check, runner):
        mock_check.return_value = ("3.13.0", "3.13.0", False)
        result = runner.invoke(cli, ["update"])
        assert result.exit_code == 0
        assert "latest version" in result.output.lower()

    @patch("pyvm_updater.cli.check_python_version")
    def test_update_calls_silent_true(self, mock_check, runner):
        mock_check.return_value = ("3.13.0", "3.13.0", False)
        runner.invoke(cli, ["update"])
        mock_check.assert_called_once_with(silent=True)
