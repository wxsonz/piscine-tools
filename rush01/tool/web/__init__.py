"""web: the dashboard and team page server for rush01 (tool/web/CONTRACT.md).

Only web_serve is published; the web_*.py modules are this folder's inside.
"""

from .web_server import web_serve

__all__ = ["web_serve"]
