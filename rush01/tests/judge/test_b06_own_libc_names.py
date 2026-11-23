"""B6: a team's own ft_strlen / strlen -> not forbidden; own strlen gets the
"defines own" note."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, run_judge

MAIN = ("#include <unistd.h>\n\nint\tft_strlen(char *s)\n{\n\tint\ti;\n\n"
        "\ti = 0;\n\twhile (s[i])\n\t\ti++;\n\treturn (i);\n}\n\n"
        "unsigned long\tstrlen(const char *s)\n{\n\tunsigned long\ti;\n\n"
        "\ti = 0;\n\twhile (s[i])\n\t\ti++;\n\treturn (i);\n}\n\n"
        "int\tmain(int argc, char **argv)\n{\n"
        "\twrite(1, argv[0], ft_strlen(argv[0]) + strlen(argv[0]) * 0);\n"
        "\t(void)argc;\n\treturn (0);\n}\n")


class TestB6OwnLibcNames(unittest.TestCase):
    def test_own_strlen(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": MAIN}, [PDF_ENTRY])
        self.assertTrue(r["built"], r["build_log"])
        self.assertEqual(r["forbidden"]["names"], [])
        self.assertIn("defines own strlen", r["forbidden"]["notes"])
        self.assertFalse(any("ft_strlen" in n for n in r["forbidden"]["notes"]))


if __name__ == "__main__":
    unittest.main()
