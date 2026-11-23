"""detect: name the approach of each part of a team's rush01 code (static).

Published (CONTRACT.md): detect_team, detect_catalog. Everything else in
this folder is inside.
"""

from .detect_catalog import catalog_entries as _catalog_entries
from .detect_verdict import detect_team

__all__ = ["detect_team", "detect_catalog"]


def detect_catalog():
    """Every catalog entry of PLAN.md §7.3 (SHAPES "catalog entry")."""
    return _catalog_entries()
