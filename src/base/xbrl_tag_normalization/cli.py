"""Backwards-compatibility shim — re-exports from src.base.concept_normalization.cli.

Usage:
    python -m src.base.xbrl_tag_normalization.cli normalize
    (Deprecated — use python -m src.base.concept_normalization.cli instead)
"""

from src.base.concept_normalization.cli import main  # noqa: F401

if __name__ == "__main__":
    main()
