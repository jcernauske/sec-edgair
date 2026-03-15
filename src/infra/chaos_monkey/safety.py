"""Three-layer kill switch for the Chaos Monkey.

ALL three layers must pass or the process hard-exits with sys.exit().
No exceptions. No fallback. No "continue anyway" flag.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from src.config import CHAOS_MONKEY_ENABLED

logger = logging.getLogger(__name__)


def safety_check(output_path: Path) -> None:
    """Three-layer kill switch. ALL must pass or hard exit.

    Layer 1: CHAOS_MONKEY_ENABLED must be True in src/config.py
    Layer 2: SEC_EDGAIR_ENV environment variable must equal "dev"
    Layer 3: Output path must contain "/shadow/" (no writing to real data)

    This function either returns None (all clear) or calls sys.exit().
    """
    # Layer 1: Config flag
    if not CHAOS_MONKEY_ENABLED:
        sys.exit(
            "CHAOS MONKEY BLOCKED: CHAOS_MONKEY_ENABLED is False in src/config.py. "
            "Set it to True to enable adversarial testing."
        )

    # Layer 2: Environment variable
    env = os.environ.get("SEC_EDGAIR_ENV", "")
    if env != "dev":
        sys.exit(
            f"CHAOS MONKEY BLOCKED: SEC_EDGAIR_ENV={env!r}, must be 'dev'. "
            f"Set the environment variable: export SEC_EDGAIR_ENV=dev"
        )

    # Layer 3: Output path validation
    output_str = str(Path(output_path).resolve())
    if "/shadow/" not in output_str:
        sys.exit(
            f"CHAOS MONKEY BLOCKED: output path {output_path} does not contain '/shadow/'. "
            f"The chaos monkey can only write to shadow zone paths."
        )

    # All clear
    logger.warning(
        "\U0001f412 CHAOS MONKEY ACTIVE — injecting adversarial data into shadow zone"
    )
    logger.warning("  Output path: %s", output_path)
    logger.warning("  Environment: %s", env)
