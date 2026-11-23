"""B1 (free style): the same catalog ids written the way some students do,
not in Norm style: one file, globals, `for` loops, long functions, a 2D
position (x, y) with carry. Snippets written for this test (PROOF-9)."""

import unittest

from c_team import TeamCase

COMMON = """\
#include <unistd.h>
#include <stdlib.h>

int g[9][9];
int clue[36];
int n;

int parse(char *s)
{
    int count = 0;

    for (int i = 0; s[i]; i++)
    {
        if (s[i] >= '1' && s[i] <= '9')
        {
            if (i > 0 && s[i - 1] != ' ')
                return (0);
            clue[count++] = s[i] - '0';
        }
        else if (s[i] != ' ')
            return (0);
    }
    if (count % 4 != 0)
        return (0);
    n = count / 4;
    return (n);
}

int seen(int *line, int len, int step)
{
    int top = 0;
    int count = 0;

    for (int i = 0; i < len; i++)
    {
        if (line[i * step] > top)
        {
            top = line[i * step];
            count++;
        }
    }
    return (count);
}

int fits(int x, int y, int v)
{
    for (int i = 0; i < n; i++)
        if ((i != x && g[i][y] == v) || (i != y && g[x][i] == v))
            return (0);
    return (1);
}

int all_clues(void)
{
    int line[9];

    for (int x = 0; x < n; x++)
    {
        for (int y = 0; y < n; y++)
            line[y] = g[x][y];
        if (seen(line, n, 1) != clue[x] || seen(line + n - 1, n, -1) != clue[n + x])
            return (0);
    }
    for (int y = 0; y < n; y++)
    {
        for (int x = 0; x < n; x++)
            line[x] = g[x][y];
        if (seen(line, n, 1) != clue[2 * n + y] || seen(line + n - 1, n, -1) != clue[3 * n + y])
            return (0);
    }
    return (1);
}

void show(void)
{
    char c;

    for (int y = 0; y < n; y++)
    {
        for (int x = 0; x < n; x++)
        {
            c = '0' + g[x][y];
            write(1, &c, 1);
            if (x < n - 1)
                write(1, " ", 1);
        }
        write(1, "\\n", 1);
    }
}

void result(int ok)
{
    if (ok)
        show();
    else
        write(1, "Error\\n", 6);
}
"""

ITERATIVE = COMMON + """
int search(void)
{
    int x = 0;
    int y = 0;
    int v;

    while (1)
    {
        if (y == n)
            return (all_clues());
        v = g[x][y] + 1;
        if (v > n)
        {
            g[x][y] = 0;
            x--;
            if (x < 0)
            {
                x = n - 1;
                y--;
            }
            if (y < 0)
                return (0);
            continue;
        }
        g[x][y] = v;
        if (fits(x, y, v))
        {
            x++;
            if (x == n)
            {
                x = 0;
                y++;
            }
        }
    }
}

int main(int argc, char **argv)
{
    if (argc != 2 || !parse(argv[1]))
        return (write(1, "Error\\n", 6), 1);
    result(search());
    return (0);
}
"""

ODOMETER = COMMON + """
int lines_unique(void)
{
    for (int a = 0; a < n; a++)
        for (int b = 0; b < n; b++)
            if (!fits(a, b, g[a][b]))
                return (0);
    return (1);
}

int next(void)
{
    int x = 0;
    int y = 0;

    while (y < n)
    {
        g[x][y]++;
        if (g[x][y] <= n)
            return (1);
        g[x][y] = 1;
        x++;
        if (x == n)
        {
            x = 0;
            y++;
        }
    }
    return (0);
}

int search(void)
{
    for (int i = 0; i < n * n; i++)
        g[i % n][i / n] = 1;
    while (1)
    {
        if (lines_unique() && all_clues())
            return (1);
        if (!next())
            return (0);
    }
}

int main(int argc, char **argv)
{
    if (argc != 2 || !parse(argv[1]))
        return (write(1, "Error\\n", 6), 1);
    result(search());
    return (0);
}
"""

ROWS_GENERATED = COMMON + """
int *orders[9];
int norders[9];
int want_left;
int want_right;

void swap(int *a, int *b)
{
    int t;

    t = *a;
    *a = *b;
    *b = t;
}

void gen(int *p, int k, int *count, int *out)
{
    if (k == n)
    {
        if (seen(p, n, 1) == want_left && seen(p + n - 1, n, -1) == want_right)
        {
            if (out)
                for (int j = 0; j < n; j++)
                    out[*count * n + j] = p[j];
            (*count)++;
        }
        return ;
    }
    for (int i = k; i < n; i++)
    {
        swap(&p[k], &p[i]);
        gen(p, k + 1, count, out);
        swap(&p[k], &p[i]);
    }
}

void put_row(int y, int *row)
{
    for (int x = 0; x < n; x++)
        g[x][y] = row[x];
}

int row_ok(int y, int *row)
{
    for (int x = 0; x < n; x++)
        for (int r = 0; r < y; r++)
            if (g[x][r] == row[x])
                return (0);
    return (1);
}

int rows(int y)
{
    if (y == n)
        return (all_clues());
    for (int k = 0; k < norders[y]; k++)
    {
        if (row_ok(y, &orders[y][k * n]))
        {
            put_row(y, &orders[y][k * n]);
            if (rows(y + 1))
                return (1);
        }
    }
    return (0);
}

int search(void)
{
    int p[9];

    for (int y = 0; y < n; y++)
    {
        for (int i = 0; i < n; i++)
            p[i] = i + 1;
        want_left = clue[2 * n + y];
        want_right = clue[3 * n + y];
        norders[y] = 0;
        gen(p, 0, &norders[y], 0);
        orders[y] = malloc(sizeof(int) * norders[y] * n);
        norders[y] = 0;
        gen(p, 0, &norders[y], orders[y]);
    }
    return (rows(0));
}

int main(int argc, char **argv)
{
    if (argc != 2 || !parse(argv[1]))
        return (write(1, "Error\\n", 6), 1);
    result(search());
    return (0);
}
"""

RECURSIVE_FOR = COMMON + """
int search(int pos)
{
    if (pos == n * n)
        return (all_clues());
    for (int v = 1; v <= n; v++)
    {
        if (fits(pos % n, pos / n, v))
        {
            g[pos % n][pos / n] = v;
            if (search(pos + 1))
                return (1);
            g[pos % n][pos / n] = 0;
        }
    }
    return (0);
}

int main(int argc, char **argv)
{
    if (argc != 2 || !parse(argv[1]))
        return (write(1, "Error\\n", 6), 1);
    result(search(0));
    return (0);
}
"""


class TestB1FreeStyle(TeamCase):

    def test_iterative_while_one(self):
        self.assert_id({"rush.c": ITERATIVE}, "solve", "solve.bt_iter")

    def test_odometer_brute_force(self):
        v = self.assert_id({"rush.c": ODOMETER}, "solve", "solve.brute16")
        self.assertNotEqual(v["confidence"], "unrecognized")

    def test_generated_row_orders(self):
        v = self.assert_id({"rush.c": ROWS_GENERATED}, "solve",
                           "solve.row_perm")
        self.assertEqual(v["where"][0]["func"], "rows", self.explain(v))
        idiom = [f["text"] for f in v["facts"] if f["key"] == "idiom"]
        self.assertTrue(idiom and "y + 1" in idiom[0], self.explain(v))

    def test_for_loops_backtracking(self):
        result = self.detect({"rush.c": RECURSIVE_FOR})
        self.assertEqual(result["parts"]["solve"]["id"], "solve.bt_unique",
                         self.explain(result["parts"]["solve"]))
        self.assertEqual(result["parts"]["data"]["id"], "data.grid2d")

    def test_direct_write_print_is_clear(self):
        # write(1, &c, 1) per cell, a space between digits: nothing missing
        v = self.assert_id({"rush.c": ITERATIVE}, "print", "print.char")
        self.assertEqual(v["confidence"], "clear", self.explain(v))

    def test_result_passed_to_a_printer_is_tested(self):
        v = self.part({"rush.c": ITERATIVE}, "solve")
        facts = [f["text"] for f in v["facts"] if f["key"] == "no_solution"]
        self.assertTrue(facts and facts[0].startswith("no solution → Error"),
                        self.explain(v))


if __name__ == "__main__":
    unittest.main()
