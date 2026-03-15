"""Tests for the Chaos Monkey kill switch.

These are the most important tests in the chaos monkey spec.
If the kill switch doesn't work, nothing else matters.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestSafetyCheck:
    """Three-layer kill switch must block unless ALL conditions are met."""

    def test_blocked_when_config_disabled(self):
        """Layer 1: CHAOS_MONKEY_ENABLED=False → sys.exit."""
        with patch("src.infra.chaos_monkey.safety.CHAOS_MONKEY_ENABLED", False):
            with pytest.raises(SystemExit) as exc_info:
                from src.infra.chaos_monkey.safety import safety_check
                safety_check(Path("/data/shadow/warehouse"))
            assert "CHAOS_MONKEY_ENABLED is False" in str(exc_info.value)

    def test_blocked_when_env_not_dev(self):
        """Layer 2: SEC_EDGAIR_ENV != 'dev' → sys.exit."""
        with patch("src.infra.chaos_monkey.safety.CHAOS_MONKEY_ENABLED", True):
            with patch.dict(os.environ, {"SEC_EDGAIR_ENV": "prod"}, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    from src.infra.chaos_monkey.safety import safety_check
                    safety_check(Path("/data/shadow/warehouse"))
                assert "must be 'dev'" in str(exc_info.value)

    def test_blocked_when_env_missing(self):
        """Layer 2: SEC_EDGAIR_ENV not set → sys.exit."""
        with patch("src.infra.chaos_monkey.safety.CHAOS_MONKEY_ENABLED", True):
            env = os.environ.copy()
            env.pop("SEC_EDGAIR_ENV", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(SystemExit) as exc_info:
                    from src.infra.chaos_monkey.safety import safety_check
                    safety_check(Path("/data/shadow/warehouse"))
                assert "must be 'dev'" in str(exc_info.value)

    def test_blocked_when_path_not_shadow(self):
        """Layer 3: Output path without '/shadow/' → sys.exit."""
        with patch("src.infra.chaos_monkey.safety.CHAOS_MONKEY_ENABLED", True):
            with patch.dict(os.environ, {"SEC_EDGAIR_ENV": "dev"}, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    from src.infra.chaos_monkey.safety import safety_check
                    safety_check(Path("/data/raw/iceberg_warehouse"))
                assert "does not contain '/shadow/'" in str(exc_info.value)

    def test_passes_when_all_conditions_met(self):
        """All three layers satisfied → no exit, returns None."""
        with patch("src.infra.chaos_monkey.safety.CHAOS_MONKEY_ENABLED", True):
            with patch.dict(os.environ, {"SEC_EDGAIR_ENV": "dev"}, clear=False):
                from src.infra.chaos_monkey.safety import safety_check
                # Should not raise
                result = safety_check(Path("/data/shadow/warehouse"))
                assert result is None

    def test_blocked_when_env_is_staging(self):
        """Layer 2: SEC_EDGAIR_ENV='staging' is not 'dev' → sys.exit."""
        with patch("src.infra.chaos_monkey.safety.CHAOS_MONKEY_ENABLED", True):
            with patch.dict(os.environ, {"SEC_EDGAIR_ENV": "staging"}, clear=False):
                with pytest.raises(SystemExit):
                    from src.infra.chaos_monkey.safety import safety_check
                    safety_check(Path("/data/shadow/warehouse"))
