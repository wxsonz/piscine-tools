"""B5: `int g[..][..] = {0};` that emits memset -> not forbidden; note
"compiler-generated". On gcc 16 / clang a [4][4] emits no memset; [9][9]
and up do, so the test uses [16][16] and checks nm first (PROOF-8)."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, nm_undefined, run_judge

MAIN = ("#include <unistd.h>\n\nint\tmain(int argc, char **argv)\n{\n"
        "\tint\tg[16][16] = {0};\n\n\tg[argc][0] = 1;\n"
        "\twrite(1, argv[0], g[1][0]);\n\treturn (0);\n}\n")


class TestB5ZeroInit(unittest.TestCase):
    def test_memset_from_zero_init(self):
        self.assertIn("memset", nm_undefined(MAIN), "toolchain fact changed")
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": MAIN}, [PDF_ENTRY])
        self.assertTrue(r["built"])
        self.assertEqual(r["forbidden"]["names"], [])
        self.assertIn("compiler-generated: memset (e.g. = {0})", r["forbidden"]["notes"])

    def test_memset_called_in_source_is_forbidden(self):
        main = ("#include <string.h>\n#include <unistd.h>\n\n"
                "int\tmain(int argc, char **argv)\n{\n\tchar\tb[64];\n\n"
                "\tmemset(b, 'x', argc);\n\twrite(1, b, argc);\n"
                "\t(void)argv;\n\treturn (0);\n}\n")
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": main}, [PDF_ENTRY])
        source = [x for x in r["forbidden"]["names"] if x["where"] == "source"]
        self.assertEqual([x["name"] for x in source], ["memset"])
        self.assertFalse(any("compiler-generated" in n for n in r["forbidden"]["notes"]))


if __name__ == "__main__":
    unittest.main()
