"""Regenerate bank/ with the default seed: python3 -m puzzle (run from
rush01/tool). The only entry point of puzzle/ (CONTRACT.md)."""

import os

from . import puzzle_make_bank, puzzle_save_bank

puzzle_save_bank(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "bank"), puzzle_make_bank())
