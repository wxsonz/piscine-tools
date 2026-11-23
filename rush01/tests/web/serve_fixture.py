#!/usr/bin/env python3
"""Serve the dashboard on the fixture teams, for a look by eye (PROOF-10):

  python3 rush01/tests/web/serve_fixture.py [port]     (default 4243)

then open http://localhost:<port>/ . Teams c01 (runs, wrong grids, a
diagnosis) and d3 (does not build) live in a temp dir removed on Ctrl-C.
"""

import sys
import tempfile

import fake_app


def main(argv):
    port = int(argv[0]) if argv else 4243
    with tempfile.TemporaryDirectory(prefix="rush01-web-fixture-") as root:
        fake = fake_app.fake_make(root)
        fake["gate"].set()
        fake_app.web_serve(fake["app"], port)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
