"""Tests for bitemporal CLI commands."""

from unittest.mock import patch

from src.base.bitemporal.cli import main


class TestCLIValidate:

    @patch("src.base.bitemporal.cli._load_facts")
    def test_validate_runs_all_rules(self, mock_load, capsys):
        """validate command runs all 5 temporal DQ rules."""
        import datetime

        mock_load.return_value = [
            {
                "cik": 320193,
                "concept": "Assets",
                "unit": "USD",
                "val": 1000.0,
                "start_date": datetime.date(2023, 1, 1),
                "end_date": datetime.date(2023, 12, 31),
                "filed_date": datetime.date(2024, 2, 15),
                "accession_number": "A1",
                "is_superseded": False,
                "superseded_by": None,
            }
        ]

        main(["validate"])
        output = capsys.readouterr().out
        assert "5/5 rules passed" in output
        assert "BASE-BT-001" in output
        assert "BASE-BT-005" in output


class TestCLISnapshots:

    @patch("src.base.bitemporal.cli._load_table")
    def test_snapshots_command(self, mock_load_table, capsys):
        """snapshots command calls get_labeled_snapshots."""
        from unittest.mock import MagicMock

        mock_table = MagicMock()
        mock_table.snapshots.return_value = []
        mock_load_table.return_value = mock_table

        with patch(
            "src.base.bitemporal.snapshot_registry.get_snapshots",
            return_value=[],
        ):
            main(["snapshots"])

        output = capsys.readouterr().out
        assert "Snapshots" in output
        assert "0" in output
