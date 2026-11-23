"""B14: the eval sheet's "lines to ask about": bit shifts, complex lines,
recursion with its returns, and malloc results never compared with NULL."""

import unittest

from c_team import TeamCase, team_files

EXTRA = """\
#include <stdlib.h>

int    ft_bits(int mask, int v)
{
    return (mask | (1 << v));
}

int    *ft_unchecked(void)
{
    int    *tab;

    tab = malloc(sizeof(int) * 16);
    tab[0] = 0;
    return (tab);
}

int    *ft_checked(void)
{
    int    *tab;

    tab = malloc(sizeof(int) * 16);
    if (!tab)
        return (0);
    return (tab);
}

int    *ft_checked_inline(void)
{
    int    *tab;

    if (!(tab = malloc(sizeof(int) * 16)))
        return (0);
    return (tab);
}

int    *ft_passes_up(void)
{
    return (malloc(sizeof(int) * 4));
}

int    ft_long(int *a, int i, int j)
{
    return (a[i] + a[j] * 2 - a[i + j] % 4 == a[0] && a[1] != a[2] || !a[3]);
}
"""


class TestB14AskLines(TeamCase):

    def ask(self):
        project = self.detect(team_files(extra=EXTRA))["project"]
        return project["ask"]

    def lines_of(self, items, kind):
        return {a["line"] for a in items if a["kind"] == kind}

    def line_no(self, needle):
        return EXTRA.split("\n").index(needle) + 1

    def test_shift(self):
        items = self.ask()
        self.assertEqual(self.lines_of(items, "shift"),
                         {self.line_no("    return (mask | (1 << v));")})

    def test_complex(self):
        items = self.ask()
        want = self.line_no("    return (a[i] + a[j] * 2 - a[i + j] % 4 == "
                            "a[0] && a[1] != a[2] || !a[3]);")
        self.assertIn(want, self.lines_of(items, "complex"), items)

    def test_recursion_lists_returns(self):
        rec = [a for a in self.ask() if a["kind"] == "recursion"]
        self.assertEqual([a["file"] for a in rec], ["ex00/solve.c"], rec)
        self.assertIn("ft_solve() calls itself", rec[0]["why"])
        self.assertIn("return (1)", rec[0]["why"])

    def test_malloc(self):
        items = [a for a in self.ask() if a["kind"] == "malloc"]
        lines = {a["line"] for a in items}
        unchecked = self.line_no("    tab = malloc(sizeof(int) * 16);")
        passes_up = self.line_no("    return (malloc(sizeof(int) * 4));")
        # only the first `tab = malloc` (ft_unchecked) and the passed-up one
        self.assertEqual(lines, {unchecked, passes_up}, items)
        self.assertTrue(any("callers" in a["why"] for a in items))


if __name__ == "__main__":
    unittest.main()
