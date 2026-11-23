"""B4: printf -> forbidden, where "binary" (puts or printf in nm -u) and
"source" with file and line."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, run_judge

MAIN = ("#include <stdio.h>\n\nint\tmain(void)\n{\n"
        "\tprintf(\"Error\\n\");\n\treturn (0);\n}\n")


class TestB4PrintfForbidden(unittest.TestCase):
    def test_printf(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": MAIN}, [PDF_ENTRY])
        names = r["forbidden"]["names"]
        source = [x for x in names if x["where"] == "source"]
        binary = [x for x in names if x["where"] == "binary"]
        self.assertEqual(source, [{"name": "printf", "where": "source",
                                   "file": "ex00/main.c", "line": 5}])
        self.assertEqual(len(binary), 1)
        self.assertIn(binary[0]["name"], ("puts", "printf"))
        self.assertTrue(any("<stdio.h>" in n for n in r["forbidden"]["notes"]))

    def test_write_malloc_free_are_fine(self):
        main = ("#include <stdlib.h>\n#include <unistd.h>\n\nint\tmain(void)\n{\n"
                "\tchar\t*p;\n\n\tp = malloc(4);\n\twrite(1, \"Error\\n\", 6);\n"
                "\tfree(p);\n\treturn (0);\n}\n")
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": main}, [PDF_ENTRY])
        self.assertEqual(r["forbidden"]["names"], [])

    def test_function_pointer_calls_are_theirs(self):
        main = ("#include <stdlib.h>\n#include <unistd.h>\n\n"
                "int\tapply(int (*f)(int), int v)\n{\n\treturn (f(v));\n}\n\n"
                "int\ttwice(int v)\n{\n\treturn (v * 2);\n}\n\n"
                "int\tmain(int argc, char **argv)\n{\n\tint\tn = atoi(argv[0]);\n"
                "\tint\t(*g)(int);\n\n\tg = twice;\n"
                "\twrite(1, \"x\", apply(g, n) + g(argc) * 0);\n\treturn (0);\n}\n")
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": main}, [PDF_ENTRY])
        source = [(x["name"], x["line"]) for x in r["forbidden"]["names"]
                  if x["where"] == "source"]
        self.assertEqual(source, [("atoi", 16)])
        self.assertIn("atoi", [x["name"] for x in r["forbidden"]["names"]
                               if x["where"] == "binary"])


if __name__ == "__main__":
    unittest.main()
