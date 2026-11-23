"""B1 (tier 3 + detector gaps): unit tests for used[] permutation generator
(solve.row_perm), count-down odometers (solve.brute16), and the remaining
tier-3 solve rules (solve.bits, solve.mrv, solve.propagate,
solve.line_solver, solve.dlx). Snippets written for this test (PROOF-9)."""

import unittest

from c_team import TeamCase, team_files
from test_b01_catalog_ids import PERMS, SOLVE_BITS
from test_b01_free_style import COMMON

ROWS_USED_PERM = COMMON + """
int *orders[9];
int norders[9];
int want_left;
int want_right;

void build_perm(int k, int *p, int *used, int *count, int *out)
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
    for (int v = 1; v <= n; v++)
    {
        if (!used[v])
        {
            used[v] = 1;
            p[k] = v;
            build_perm(k + 1, p, used, count, out);
            used[v] = 0;
        }
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

int place_rows(int y)
{
    if (y == n)
        return (all_clues());
    for (int k = 0; k < norders[y]; k++)
    {
        if (row_ok(y, &orders[y][k * n]))
        {
            put_row(y, &orders[y][k * n]);
            if (place_rows(y + 1))
                return (1);
        }
    }
    return (0);
}

int search(void)
{
    int p[9];
    int used[10] = {0};

    for (int y = 0; y < n; y++)
    {
        want_left = clue[2 * n + y];
        want_right = clue[3 * n + y];
        norders[y] = 0;
        build_perm(0, p, used, &norders[y], 0);
        orders[y] = malloc(sizeof(int) * norders[y] * n);
        norders[y] = 0;
        build_perm(0, p, used, &norders[y], orders[y]);
    }
    return (place_rows(0));
}

int main(int argc, char **argv)
{
    if (argc != 2 || !parse(argv[1]))
        return (write(1, "Error\\n", 6), 1);
    result(search());
    return (0);
}
"""

ODOMETER_COUNTDOWN_POS = COMMON + """
int lines_unique(void)
{
    for (int a = 0; a < n; a++)
        for (int b = 0; b < n; b++)
            if (!fits(a, b, g[a][b]))
                return (0);
    return (1);
}

int next_grid(void)
{
    int pos = n * n - 1;

    while (pos >= 0)
    {
        g[pos / n][pos % n]++;
        if (g[pos / n][pos % n] <= n)
            return (1);
        g[pos / n][pos % n] = 1;
        pos--;
    }
    return (0);
}

int search(void)
{
    for (int i = 0; i < n * n; i++)
        g[i / n][i % n] = 1;
    while (1)
    {
        if (lines_unique() && all_clues())
            return (1);
        if (!next_grid())
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

ODOMETER_COUNTDOWN_VAL = COMMON + """
int lines_unique(void)
{
    for (int a = 0; a < n; a++)
        for (int b = 0; b < n; b++)
            if (!fits(a, b, g[a][b]))
                return (0);
    return (1);
}

int prev_grid(void)
{
    int pos = n * n - 1;

    while (pos >= 0)
    {
        g[pos / n][pos % n]--;
        if (g[pos / n][pos % n] >= 1)
            return (1);
        g[pos / n][pos % n] = n;
        pos--;
    }
    return (0);
}

int search(void)
{
    for (int i = 0; i < n * n; i++)
        g[i / n][i % n] = n;
    while (1)
    {
        if (lines_unique() && all_clues())
            return (1);
        if (!prev_grid())
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

SOLVE_MRV = """\
#include "rush.h"

int    ft_pick_best(int grid[4][4], int *br, int *bc)
{
    int    r;
    int    c;
    int    v;
    int    cnt;
    int    best;

    best = 99;
    r = 0;
    while (r < 4)
    {
        c = 0;
        while (c < 4)
        {
            if (grid[r][c] == 0)
            {
                cnt = 0;
                v = 1;
                while (v <= 4)
                {
                    if (ft_is_valid(grid, r, c, v))
                        cnt++;
                    v++;
                }
                if (cnt < best)
                {
                    best = cnt;
                    *br = r;
                    *bc = c;
                }
            }
            c++;
        }
        r++;
    }
    return (best < 99);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    r;
    int    c;
    int    v;

    if (!ft_pick_best(grid, &r, &c))
        return (ft_check_all(grid, clues));
    v = 1;
    while (v <= 4)
    {
        if (ft_is_valid(grid, r, c, v))
        {
            grid[r][c] = v;
            if (ft_solve(grid, clues, pos + 1))
                return (1);
            grid[r][c] = 0;
        }
        v++;
    }
    return (0);
}
"""

SOLVE_PROPAGATE = """\
#include "rush.h"

int    ft_single_val(int mask)
{
    int    v;

    v = 1;
    while (v <= 4)
    {
        if (mask == (1 << v))
            return (v);
        v++;
    }
    return (0);
}

int    ft_propagate(int grid[4][4], int cand[4][4])
{
    int    changed;
    int    r;
    int    c;
    int    v;

    changed = 1;
    while (changed)
    {
        changed = 0;
        r = 0;
        while (r < 4)
        {
            c = 0;
            while (c < 4)
            {
                if (grid[r][c] == 0 && (cand[r][c] & (cand[r][c] - 1)) == 0)
                {
                    v = ft_single_val(cand[r][c]);
                    grid[r][c] = v;
                    changed = 1;
                }
                c++;
            }
            r++;
        }
    }
    return (1);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    cand[4][4];
    int    r;
    int    c;

    r = 0;
    while (r < 4)
    {
        c = 0;
        while (c < 4)
        {
            cand[r][c] = 30;
            cand[r][c] &= ~(1 << 0);
            c++;
        }
        r++;
    }
    ft_propagate(grid, cand);
    if (pos == 16)
        return (ft_check_all(grid, clues));
    return (ft_solve(grid, clues, pos + 1));
}
"""

SOLVE_LINE_SOLVER = """\
#include "rush.h"

void    ft_intersect(int perms[24][4], int row_ok[4][24], int col_ok[4][24])
{
    int    mask[4][4];
    int    r;
    int    c;
    int    p;

    r = 0;
    while (r < 4)
    {
        c = 0;
        while (c < 4)
        {
            mask[r][c] = 0;
            c++;
        }
        p = 0;
        while (p < 24)
        {
            if (row_ok[r][p])
            {
                c = 0;
                while (c < 4)
                {
                    mask[r][c] |= (1 << perms[p][c]);
                    c++;
                }
            }
            p++;
        }
        r++;
    }
    c = 0;
    while (c < 4)
    {
        p = 0;
        while (p < 24)
        {
            if (col_ok[c][p])
            {
                r = 0;
                while (r < 4)
                {
                    if (!(mask[r][c] & (1 << perms[p][r])))
                        col_ok[c][p] = 0;
                    r++;
                }
            }
            p++;
        }
        c++;
    }
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    perms[24][4];
    int    row_ok[4][24];
    int    col_ok[4][24];

    ft_fill_perms(perms);
    ft_intersect(perms, row_ok, col_ok);
    if (pos == 16)
        return (ft_check_all(grid, clues));
    grid[pos / 4][pos % 4] = 1;
    return (ft_solve(grid, clues, pos + 1));
}
"""

DLX_H = """\
#ifndef DLX_H
# define DLX_H

typedef struct s_node
{
    struct s_node    *left;
    struct s_node    *right;
    struct s_node    *up;
    struct s_node    *down;
    int              col;
}    t_node;

#endif
"""

DLX_C = """\
#include <unistd.h>
#include "dlx.h"

void    cover(t_node *c)
{
    t_node    *i;
    t_node    *j;

    c->right->left = c->left;
    c->left->right = c->right;
    i = c->down;
    while (i != c)
    {
        j = i->right;
        while (j != i)
        {
            j->down->up = j->up;
            j->up->down = j->down;
            j = j->right;
        }
        i = i->down;
    }
}

void    uncover(t_node *c)
{
    c->right->left = c;
    c->left->right = c;
}

int    search(t_node *head, int k)
{
    if (head->right == head)
        return (1);
    cover(head->right);
    if (search(head, k + 1))
        return (1);
    uncover(head->right);
    return (0);
}

int    main(int argc, char **argv)
{
    t_node    head;

    if (argc != 2 || !argv[1][0])
        return (write(1, "Error\\n", 6), 1);
    head.left = &head;
    head.right = &head;
    head.up = &head;
    head.down = &head;
    search(&head, 0);
    return (0);
}
"""


class TestB1Tier3AndGaps(TeamCase):
    def test_used_array_perm_gen_is_row_perm(self):
        v = self.assert_id({"rush.c": ROWS_USED_PERM}, "solve",
                           "solve.row_perm")
        self.assertEqual(v["where"][0]["func"], "place_rows", self.explain(v))

    def test_countdown_pos_odometer_is_brute16(self):
        v = self.assert_id({"rush.c": ODOMETER_COUNTDOWN_POS}, "solve",
                           "solve.brute16")
        self.assertNotEqual(v["confidence"], "unrecognized")

    def test_countdown_value_odometer_is_brute16(self):
        v = self.assert_id({"rush.c": ODOMETER_COUNTDOWN_VAL}, "solve",
                           "solve.brute16")
        self.assertNotEqual(v["confidence"], "unrecognized")

    def test_solve_bits(self):
        self.assert_id(team_files(solve=SOLVE_BITS), "solve", "solve.bits")

    def test_solve_mrv(self):
        self.assert_id(team_files(solve=SOLVE_MRV), "solve", "solve.mrv")

    def test_solve_propagate(self):
        self.assert_id(team_files(solve=SOLVE_PROPAGATE), "solve",
                       "solve.propagate")

    def test_solve_line_solver(self):
        self.assert_id(team_files(solve=SOLVE_LINE_SOLVER, perms=PERMS),
                       "solve", "solve.line_solver")

    def test_solve_dlx(self):
        self.assert_id({"dlx.h": DLX_H, "dlx.c": DLX_C}, "solve", "solve.dlx")


if __name__ == "__main__":
    unittest.main()
