"""B9: unrelated C (a hello world) -> all parts unrecognized, with where."""

import unittest

from c_team import TeamCase

HELLO = """\
#include <unistd.h>

int    main(void)
{
    write(1, "Hello, world\\n", 13);
    return (0);
}
"""


class TestB9HelloWorld(TeamCase):

    def test_all_unrecognized(self):
        parts = self.detect({"hello.c": HELLO})["parts"]
        for name, v in parts.items():
            self.assertIsNone(v["id"], f"{name}: {self.explain(v)}")
            self.assertEqual(v["confidence"], "unrecognized")
            self.assertEqual(v["name"], "unrecognized")
            self.assertEqual(v["where"][0]["func"], "main", name)
            self.assertEqual(v["where"][0]["file"], "ex00/hello.c", name)


if __name__ == "__main__":
    unittest.main()
