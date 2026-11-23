"""B4: digits written through ft_putnbr / ft_putchar -> print.char (the
printer is found by following calls 1-2 hops)."""

import unittest

from c_team import TeamCase, team_files

PRINT_PUTNBR = """\
#include <unistd.h>

void    ft_putchar(char c)
{
    write(1, &c, 1);
}

void    ft_putnbr(int nb)
{
    if (nb > 9)
        ft_putnbr(nb / 10);
    ft_putchar(nb % 10 + '0');
}

void    ft_print(int grid[4][4])
{
    int    r;
    int    c;

    r = 0;
    while (r < 4)
    {
        c = 0;
        while (c < 4)
        {
            ft_putnbr(grid[r][c]);
            if (c < 3)
                ft_putchar(' ');
            c++;
        }
        ft_putchar('\\n');
        r++;
    }
}
"""


class TestB4PrintWrappers(TeamCase):

    def test_putnbr_putchar(self):
        result = self.detect(team_files(print=PRINT_PUTNBR))
        v = result["parts"]["print"]
        self.assertEqual(v["id"], "print.char", self.explain(v))
        self.assertEqual(v["where"][0]["func"], "ft_print", self.explain(v))
        # ft_putnbr calls itself, but it prints: it is not the search
        self.assertEqual(result["parts"]["solve"]["id"], "solve.bt_unique")

    def test_putchar_only(self):
        self.assert_id(team_files(), "print", "print.char")


if __name__ == "__main__":
    unittest.main()
