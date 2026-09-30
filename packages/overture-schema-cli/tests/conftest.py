"""Shared test fixtures for CLI tests."""

from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """Provide a CliRunner running in an empty working directory."""
    monkeypatch.chdir(tmp_path)
    return CliRunner()
