"""Tests for amendment analysis CLI."""

from src.consumable.amendment_analysis.cli import main


def test_cli_status_not_created(capsys):
    """Status on non-existent table should print a message."""
    try:
        main(["--warehouse", "/tmp/nonexistent", "--catalog", "/tmp/nonexistent.db", "status"])
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "not yet created" in captured.out or "Amendment Analysis" in captured.out
