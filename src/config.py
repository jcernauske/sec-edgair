"""Project-level configuration for SEC EDGAIR.

Global settings that apply across all zones and pipelines.
"""

# Human approval gate toggle (global)
# When True: proposals pause for human review before proceeding
# When False: auto-promote if confidence >= module-level CONFIDENCE_FLOOR
#
# This controls ALL human-in-the-loop gates:
#   - Entity resolution: proposed CIK mappings
#   - Tag normalization: proposed concept → CDE mappings
#   - Data modeling: conceptual → logical → physical model progression (Base/Consumable)
REQUIRE_HUMAN_APPROVAL = True
