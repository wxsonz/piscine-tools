"""judge/: build a team's turn-in and judge it against the puzzle bank.
Published names only (judge/CONTRACT.md); shapes in tool/SHAPES.md.
"""

from .judge_evaluate import judge_team
from .judge_probe import judge_tools

__all__ = ["judge_team", "judge_tools"]
