"""Tests for peer comparison CLI."""

import datetime

from src.consumable.peer_comparison.cli import main


def test_cli_build(tmp_path, monkeypatch):
    """CLI build command runs without error when given valid paths."""
    warehouse = tmp_path / "iceberg_warehouse"
    catalog_db = tmp_path / "catalog.db"

    # We can't easily build without source data, so test that the CLI parses
    # arguments correctly and calls the right function
    import src.consumable.peer_comparison.cli as cli_mod

    called = {}

    def mock_build(args):
        called["build"] = True

    monkeypatch.setattr(cli_mod, "cmd_build", mock_build)
    main(["--warehouse", str(warehouse), "--catalog", str(catalog_db), "build"])
    assert called.get("build") is True


def test_cli_status(tmp_path, monkeypatch):
    """CLI status command runs without error."""
    import src.consumable.peer_comparison.cli as cli_mod

    called = {}

    def mock_status(args):
        called["status"] = True

    monkeypatch.setattr(cli_mod, "cmd_status", mock_status)
    main(["status"])
    assert called.get("status") is True


def test_cli_coverage(tmp_path, monkeypatch):
    """CLI coverage command runs without error."""
    import src.consumable.peer_comparison.cli as cli_mod

    called = {}

    def mock_coverage(args):
        called["coverage"] = True

    monkeypatch.setattr(cli_mod, "cmd_coverage", mock_coverage)
    main(["coverage"])
    assert called.get("coverage") is True


def test_cli_all(tmp_path, monkeypatch):
    """CLI all command calls build, status, and coverage."""
    import src.consumable.peer_comparison.cli as cli_mod

    calls = []

    def mock_build(args):
        calls.append("build")

    def mock_status(args):
        calls.append("status")

    def mock_coverage(args):
        calls.append("coverage")

    monkeypatch.setattr(cli_mod, "cmd_build", mock_build)
    monkeypatch.setattr(cli_mod, "cmd_status", mock_status)
    monkeypatch.setattr(cli_mod, "cmd_coverage", mock_coverage)
    main(["all"])
    assert calls == ["build", "status", "coverage"]
