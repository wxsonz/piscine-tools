# 003 Python and JS formatting
Status: accepted
Date: 2026-11-22

## Context
CODE-10 (Allman braces, tabs, 80 columns, snake_case) is written for C, C++
and TypeScript. This tool is Python 3.10 plus plain JS.

## Choice
- Python: PEP 8 (4 spaces, 79–100 columns), snake_case, as in rush00's tool
  (CODE-12). Everything else in the book holds: numbered step comments
  (`# 1. ...`, CODE-3), `<folder>_<verb>` names for published functions
  (CODE-8), file header lines (CODE-9), errors as values (CODE-11).
  Code must run on **Python 3.10**: no `tomllib`, no `except*`, no `type`
  statements, no 3.12 f-string quote nesting. The laptop has 3.14: don't rely
  on it.
- JS (in `web/www/`): CODE-10 as for TypeScript: Allman braces, tabs,
  snake_case, no frameworks, no build step. CSS: plain, as in notebook.css.

## Why
Python has no braces, and tabs in Python fight every tool; following
rush00's Python keeps the repo one style. JS is TypeScript's family, so the
book's TS rules fit it unchanged.
