"""B1: each parse / data / print entry and each tier 0-2 solve entry is
recognised on a minimal sample (one test per id). Each sample is the default
team (c_team.py) with one part swapped."""

import unittest

from c_team import MAIN, SOLVE_BT_UNIQUE, TeamCase, team_files

MAIN_NO_PARSE_CHECK = MAIN.replace(
    "if (argc != 2 || !ft_parse(argv[1], clues))", "if (argc != 2)").replace(
    "    i = 0;\n    while (i < 16)", "    ft_parse(argv[1], clues);\n"
    "    i = 0;\n    while (i < 16)", 1)

PARSE_SCAN = """\
int    ft_parse(char *str, int *clues)
{
    int    i;
    int    count;

    i = 0;
    count = 0;
    while (str[i] != '\\0')
    {
        if (str[i] >= '1' && str[i] <= '4')
        {
            if (count == 16)
                return (0);
            clues[count] = str[i] - '0';
            count++;
            if (str[i + 1] != ' ' && str[i + 1] != '\\0')
                return (0);
        }
        else if (str[i] != ' ')
            return (0);
        i++;
    }
    return (count == 16);
}
"""

SPLIT = """\
#include <stdlib.h>

int    ft_count_words(char *str)
{
    int    i;
    int    count;

    i = 0;
    count = 0;
    while (str[i])
    {
        if (str[i] != ' ' && (i == 0 || str[i - 1] == ' '))
            count++;
        i++;
    }
    return (count);
}

char    *ft_word(char *str, int len)
{
    char    *word;
    int     i;

    word = malloc(len + 1);
    i = 0;
    while (i < len)
    {
        word[i] = str[i];
        i++;
    }
    word[i] = '\\0';
    return (word);
}

char    **ft_split(char *str)
{
    char    **tab;
    int     i;
    int     k;
    int     len;

    tab = malloc(sizeof(char *) * (ft_count_words(str) + 1));
    i = 0;
    k = 0;
    while (str[i])
    {
        len = 0;
        while (str[i + len] && str[i + len] != ' ')
            len++;
        if (len > 0)
        {
            tab[k] = ft_word(str + i, len);
            k++;
            i = i + len;
        }
        else
            i++;
    }
    tab[k] = 0;
    return (tab);
}
"""

PARSE_SPLIT = """\
char    **ft_split(char *str);

int    ft_parse(char *str, int *clues)
{
    char    **words;
    int     i;

    words = ft_split(str);
    i = 0;
    while (words[i])
    {
        if (i >= 16 || words[i][1] != '\\0')
            return (0);
        if (words[i][0] < '1' || words[i][0] > '4')
            return (0);
        clues[i] = words[i][0] - '0';
        i++;
    }
    return (i == 16);
}
"""

PARSE_ATOI = """\
int    ft_atoi_at(char *str, int *i)
{
    int    res;

    res = 0;
    while (str[*i] >= '0' && str[*i] <= '9')
    {
        res = res * 10 + str[*i] - '0';
        (*i)++;
    }
    return (res);
}

int    ft_parse(char *str, int *clues)
{
    int    i;
    int    count;
    int    v;

    i = 0;
    count = 0;
    while (str[i])
    {
        v = ft_atoi_at(str, &i);
        if (count >= 16 || v < 1 || v > 4)
            return (0);
        clues[count] = v;
        count++;
        if (str[i] == ' ' && str[i + 1] != '\\0')
            i++;
        else if (str[i] != '\\0')
            return (0);
    }
    return (count == 16);
}
"""

PARSE_FSM = """\
int    ft_parse(char *str, int *clues)
{
    int    i;
    int    state;
    int    count;

    i = 0;
    state = 0;
    count = 0;
    while (str[i] != '\\0')
    {
        if (state == 0 && str[i] >= '1' && str[i] <= '4' && count < 16)
        {
            clues[count] = str[i] - '0';
            count++;
            state = 1;
        }
        else if (state == 1 && str[i] == ' ')
            state = 0;
        else
            return (0);
        i++;
    }
    return (state == 1 && count == 16);
}
"""

PARSE_NONE = """\
void    ft_parse(char *str, int *clues)
{
    int    i;

    i = 0;
    while (i < 16)
    {
        clues[i] = str[i * 2] - '0';
        i++;
    }
}
"""

SOLVE_ROWCOL = """\
#include "rush.h"

int    ft_solve_rc(int grid[4][4], int *clues, int row, int col)
{
    int    v;

    if (row == 4)
        return (ft_check_all(grid, clues));
    if (col == 4)
        return (ft_solve_rc(grid, clues, row + 1, 0));
    v = 1;
    while (v <= 4)
    {
        if (ft_is_free(grid, row, col, v))
        {
            grid[row][col] = v;
            if (ft_solve_rc(grid, clues, row, col + 1))
                return (1);
            grid[row][col] = 0;
        }
        v++;
    }
    return (0);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    (void)pos;
    return (ft_solve_rc(grid, clues, 0, 0));
}
"""

PADDED = {
    "main.c": """\
#include <unistd.h>

int     ft_parse(char *str, int b[6][6]);
int     ft_solve(int b[6][6], int pos);
void    ft_print(int b[6][6]);

int    main(int argc, char **argv)
{
    int    b[6][6];

    if (argc != 2 || !ft_parse(argv[1], b) || !ft_solve(b, 0))
    {
        write(1, "Error\\n", 6);
        return (1);
    }
    ft_print(b);
    return (0);
}
""",
    "parse.c": """\
int    ft_parse(char *str, int b[6][6])
{
    int    i;
    int    v;

    i = 0;
    while (i < 16)
    {
        if (str[i * 2] < '1' || str[i * 2] > '4')
            return (0);
        if (i < 15 && str[i * 2 + 1] != ' ')
            return (0);
        v = str[i * 2] - '0';
        if (i < 4)
            b[0][i + 1] = v;
        else if (i < 8)
            b[5][i - 3] = v;
        else if (i < 12)
            b[i - 7][0] = v;
        else
            b[i - 11][5] = v;
        i++;
    }
    return (str[31] == '\\0');
}
""",
    "check.c": """\
int    ft_free_cell(int b[6][6], int row, int col, int v)
{
    int    i;

    i = 1;
    while (i <= 4)
    {
        if (b[row][i] == v || b[i][col] == v)
            return (0);
        i++;
    }
    return (1);
}

int    ft_seen_down(int b[6][6], int col)
{
    int    i;
    int    max;
    int    count;

    i = 1;
    max = 0;
    count = 0;
    while (i <= 4)
    {
        if (b[i][col] > max)
        {
            max = b[i][col];
            count++;
        }
        i++;
    }
    return (count == b[0][col]);
}

int    ft_seen_left(int b[6][6], int row)
{
    int    i;
    int    max;
    int    count;

    i = 1;
    max = 0;
    count = 0;
    while (i <= 4)
    {
        if (b[row][i] > max)
        {
            max = b[row][i];
            count++;
        }
        i++;
    }
    return (count == b[row][0]);
}

int    ft_board_ok(int b[6][6])
{
    int    i;

    i = 1;
    while (i <= 4)
    {
        if (!ft_seen_down(b, i) || !ft_seen_left(b, i))
            return (0);
        i++;
    }
    return (1);
}
""",
    "solve.c": """\
int    ft_free_cell(int b[6][6], int row, int col, int v);
int    ft_board_ok(int b[6][6]);

int    ft_solve(int b[6][6], int pos)
{
    int    v;
    int    r;
    int    c;

    if (pos == 16)
        return (ft_board_ok(b));
    r = pos / 4 + 1;
    c = pos % 4 + 1;
    v = 1;
    while (v <= 4)
    {
        if (ft_free_cell(b, r, c, v))
        {
            b[r][c] = v;
            if (ft_solve(b, pos + 1))
                return (1);
            b[r][c] = 0;
        }
        v++;
    }
    return (0);
}
""",
    "print.c": """\
#include <unistd.h>

void    ft_print(int b[6][6])
{
    int     r;
    int     c;
    char    ch;

    r = 1;
    while (r <= 4)
    {
        c = 1;
        while (c <= 4)
        {
            ch = b[r][c] + '0';
            write(1, &ch, 1);
            if (c < 4)
                write(1, " ", 1);
            c++;
        }
        write(1, "\\n", 1);
        r++;
    }
}
""",
}

MAIN_MALLOC = MAIN.replace("int    grid[4][4];", "int    **grid;").replace(
    "    i = 0;\n    while (i < 16)\n", "    grid = malloc(sizeof(int *) * 4);"
    "\n    i = 0;\n    while (i < 4)\n    {\n        grid[i] = malloc(sizeof"
    "(int) * 4);\n        i++;\n    }\n    i = 0;\n    while (i < 16)\n", 1)

SOLVE_FLAT = """\
int    ft_free_flat(int *grid, int pos, int v)
{
    int    i;

    i = 0;
    while (i < 4)
    {
        if (grid[pos / 4 * 4 + i] == v || grid[i * 4 + pos % 4] == v)
            return (0);
        i++;
    }
    return (1);
}

int    ft_flat_ok(int *grid, int *clues);

int    ft_solve(int *grid, int *clues, int pos)
{
    int    v;

    if (pos == 16)
        return (ft_flat_ok(grid, clues));
    v = 1;
    while (v <= 4)
    {
        if (ft_free_flat(grid, pos, v))
        {
            grid[pos] = v;
            if (ft_solve(grid, clues, pos + 1))
                return (1);
            grid[pos] = 0;
        }
        v++;
    }
    return (0);
}
"""

CHECK_FLAT = """\
int    ft_seen(int *grid, int start, int step)
{
    int    i;
    int    max;
    int    count;

    i = 0;
    max = 0;
    count = 0;
    while (i < 4)
    {
        if (grid[start + i * step] > max)
        {
            max = grid[start + i * step];
            count++;
        }
        i++;
    }
    return (count);
}

int    ft_flat_ok(int *grid, int *clues)
{
    int    i;

    i = 0;
    while (i < 4)
    {
        if (ft_seen(grid, i, 4) != clues[i])
            return (0);
        if (ft_seen(grid, 12 + i, -4) != clues[4 + i])
            return (0);
        if (ft_seen(grid, i * 4, 1) != clues[8 + i])
            return (0);
        if (ft_seen(grid, i * 4 + 3, -1) != clues[12 + i])
            return (0);
        i++;
    }
    return (1);
}
"""

SOLVE_CHAR = """\
int    ft_free_char(char grid[4][4], int row, int col, char v)
{
    int    i;

    i = 0;
    while (i < 4)
    {
        if (grid[row][i] == v || grid[i][col] == v)
            return (0);
        i++;
    }
    return (1);
}

int    ft_char_ok(char grid[4][4], int *clues);

int    ft_solve(char grid[4][4], int *clues, int pos)
{
    char    v;

    if (pos == 16)
        return (ft_char_ok(grid, clues));
    v = '1';
    while (v <= '4')
    {
        if (ft_free_char(grid, pos / 4, pos % 4, v))
        {
            grid[pos / 4][pos % 4] = v;
            if (ft_solve(grid, clues, pos + 1))
                return (1);
            grid[pos / 4][pos % 4] = '0';
        }
        v++;
    }
    return (0);
}
"""

PRINT_CHAR_GRID = """\
#include <unistd.h>

void    ft_print(char grid[4][4])
{
    int    r;
    int    c;

    r = 0;
    while (r < 4)
    {
        c = 0;
        while (c < 4)
        {
            write(1, &grid[r][c], 1);
            if (c < 3)
                write(1, " ", 1);
            c++;
        }
        write(1, "\\n", 1);
        r++;
    }
}
"""

STRUCT_H = """\
#ifndef RUSH_H
# define RUSH_H

typedef struct s_board
{
    int    n;
    int    grid[4][4];
    int    clues[16];
}    t_board;

int     ft_parse(char *str, int *clues);
int     ft_is_free(int grid[4][4], int row, int col, int v);
int     ft_check_all(int grid[4][4], int *clues);
void    ft_print(int grid[4][4]);

#endif
"""

STRUCT_MAIN = """\
#include <unistd.h>
#include "rush.h"

int    ft_solve(t_board *b, int pos);

int    main(int argc, char **argv)
{
    t_board    b;
    int        i;

    b.n = 4;
    if (argc != 2 || !ft_parse(argv[1], b.clues))
    {
        write(1, "Error\\n", 6);
        return (1);
    }
    i = 0;
    while (i < 16)
    {
        b.grid[i / 4][i % 4] = 0;
        i++;
    }
    if (!ft_solve(&b, 0))
        write(1, "Error\\n", 6);
    else
        ft_print(b.grid);
    return (0);
}
"""

STRUCT_SOLVE = """\
#include "rush.h"

int    ft_solve(t_board *b, int pos)
{
    int    v;

    if (pos == b->n * b->n)
        return (ft_check_all(b->grid, b->clues));
    v = 1;
    while (v <= b->n)
    {
        if (ft_is_free(b->grid, pos / 4, pos % 4, v))
        {
            b->grid[pos / 4][pos % 4] = v;
            if (ft_solve(b, pos + 1))
                return (1);
            b->grid[pos / 4][pos % 4] = 0;
        }
        v++;
    }
    return (0);
}
"""

SOLVE_BITS = """\
#include "rush.h"

int    ft_solve_bits(int grid[4][4], int *masks, int *clues, int pos)
{
    int    v;
    int    r;
    int    c;

    if (pos == 16)
        return (ft_check_all(grid, clues));
    r = pos / 4;
    c = pos % 4;
    v = 1;
    while (v <= 4)
    {
        if (!(masks[r] & (1 << v)) && !(masks[4 + c] & (1 << v)))
        {
            grid[r][c] = v;
            masks[r] |= (1 << v);
            masks[4 + c] |= (1 << v);
            if (ft_solve_bits(grid, masks, clues, pos + 1))
                return (1);
            masks[r] &= ~(1 << v);
            masks[4 + c] &= ~(1 << v);
            grid[r][c] = 0;
        }
        v++;
    }
    return (0);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    masks[8];
    int    i;

    i = 0;
    while (i < 8)
    {
        masks[i] = 0;
        i++;
    }
    return (ft_solve_bits(grid, masks, clues, pos));
}
"""

SOLVE_CANDS = """\
#include "rush.h"

void    ft_cross(int cand[4][4][5], int pos, int v, int on)
{
    int    i;

    i = 0;
    while (i < 4)
    {
        cand[pos / 4][i][v] = on;
        cand[i][pos % 4][v] = on;
        i++;
    }
}

int    ft_solve_c(int grid[4][4], int cand[4][4][5], int *clues, int pos)
{
    int    v;

    if (pos == 16)
        return (ft_check_all(grid, clues));
    v = 1;
    while (v <= 4)
    {
        if (cand[pos / 4][pos % 4][v] == 1)
        {
            grid[pos / 4][pos % 4] = v;
            ft_cross(cand, pos, v, 0);
            if (ft_solve_c(grid, cand, clues, pos + 1))
                return (1);
            ft_cross(cand, pos, v, 1);
            grid[pos / 4][pos % 4] = 0;
        }
        v++;
    }
    return (0);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    cand[4][4][5];
    int    i;

    i = 0;
    while (i < 80)
    {
        cand[i / 20][i / 5 % 4][i % 5] = 1;
        i++;
    }
    return (ft_solve_c(grid, cand, clues, pos));
}
"""

PRINT_LINE = """\
#include <unistd.h>

void    ft_print(int grid[4][4])
{
    char    line[8];
    int     r;
    int     c;

    r = 0;
    while (r < 4)
    {
        c = 0;
        while (c < 4)
        {
            line[c * 2] = grid[r][c] + '0';
            line[c * 2 + 1] = ' ';
            c++;
        }
        line[7] = '\\n';
        write(1, line, 8);
        r++;
    }
}
"""

PRINT_BOARD = """\
#include <unistd.h>

void    ft_print(int grid[4][4])
{
    char    out[32];
    int     pos;

    pos = 0;
    while (pos < 16)
    {
        out[pos * 2] = grid[pos / 4][pos % 4] + '0';
        if (pos % 4 == 3)
            out[pos * 2 + 1] = '\\n';
        else
            out[pos * 2 + 1] = ' ';
        pos++;
    }
    write(1, out, 32);
}
"""

PRINT_PUTSTR = """\
#include <unistd.h>

void    ft_putstr(char *str)
{
    int    i;

    i = 0;
    while (str[i])
        i++;
    write(1, str, i);
}

void    ft_print(int grid[4][4])
{
    char    out[33];
    int     pos;

    pos = 0;
    while (pos < 16)
    {
        out[pos * 2] = grid[pos / 4][pos % 4] + '0';
        out[pos * 2 + 1] = ' ';
        if (pos % 4 == 3)
            out[pos * 2 + 1] = '\\n';
        pos++;
    }
    out[32] = '\\0';
    ft_putstr(out);
}
"""

HARDCODE_MAIN = """\
#include <unistd.h>

int    ft_strcmp(char *a, char *b)
{
    int    i;

    i = 0;
    while (a[i] && a[i] == b[i])
        i++;
    return (a[i] - b[i]);
}

int    main(int argc, char **argv)
{
    if (argc == 2 && ft_strcmp(argv[1], "4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2") == 0)
        write(1, "1 2 3 4\\n2 3 4 1\\n3 4 1 2\\n4 1 2 3\\n", 32);
    else
        write(1, "Error\\n", 6);
    return (0);
}
"""

SOLVE_BRUTE16 = """\
#include "rush.h"

int    ft_lines_ok(int grid[4][4])
{
    int    i;
    int    j;
    int    k;

    i = 0;
    while (i < 4)
    {
        j = 0;
        while (j < 4)
        {
            k = j + 1;
            while (k < 4)
            {
                if (grid[i][j] == grid[i][k] || grid[j][i] == grid[k][i])
                    return (0);
                k++;
            }
            j++;
        }
        i++;
    }
    return (1);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    long    n;
    long    k;

    n = 0;
    while (n < 4294967296)
    {
        k = n;
        pos = 0;
        while (pos < 16)
        {
            grid[pos / 4][pos % 4] = k % 4 + 1;
            k = k / 4;
            pos++;
        }
        if (ft_lines_ok(grid) && ft_check_all(grid, clues))
            return (1);
        n++;
    }
    return (0);
}
"""

PERMS = """\
void    ft_fill_perms(int perms[24][4])
{
    int    v[4];
    int    k;

    k = 0;
    v[0] = 1;
    while (v[0] <= 4)
    {
        v[1] = 1;
        while (v[1] <= 4)
        {
            v[2] = 1;
            while (v[2] <= 4)
            {
                v[3] = 10 - v[0] - v[1] - v[2];
                if (v[0] != v[1] && v[0] != v[2] && v[1] != v[2]
                    && v[3] != v[0] && v[3] != v[1] && v[3] != v[2])
                {
                    perms[k][0] = v[0];
                    perms[k][1] = v[1];
                    perms[k][2] = v[2];
                    perms[k][3] = v[3];
                    k++;
                }
                v[2]++;
            }
            v[1]++;
        }
        v[0]++;
    }
}
"""

COPY_ROW = """\
void    ft_copy_row(int grid[4][4], int row, int *perm)
{
    int    c;

    c = 0;
    while (c < 4)
    {
        grid[row][c] = perm[c];
        c++;
    }
}
"""

SOLVE_PERM_LOOPS = COPY_ROW + """
int    ft_cols_unique(int grid[4][4]);
void   ft_fill_perms(int perms[24][4]);

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    perms[24][4];
    int    a;
    int    b;
    int    c;
    int    d;

    ft_fill_perms(perms);
    a = -1;
    while (++a < 24)
    {
        b = -1;
        while (++b < 24)
        {
            c = -1;
            while (++c < 24)
            {
                d = -1;
                while (++d < 24)
                {
                    ft_copy_row(grid, 0, perms[a]);
                    ft_copy_row(grid, 1, perms[b]);
                    ft_copy_row(grid, 2, perms[c]);
                    ft_copy_row(grid, 3, perms[d]);
                    if (ft_cols_unique(grid) && ft_check_all(grid, clues))
                        return (pos + 1);
                }
            }
        }
    }
    return (0);
}
"""

COLS_UNIQUE = """\
int    ft_cols_unique(int grid[4][4])
{
    int    c;
    int    i;
    int    j;

    c = 0;
    while (c < 4)
    {
        i = 0;
        while (i < 4)
        {
            j = i + 1;
            while (j < 4)
            {
                if (grid[i][c] == grid[j][c])
                    return (0);
                j++;
            }
            i++;
        }
        c++;
    }
    return (1);
}
"""

SOLVE_BT_END = """\
#include "rush.h"

int    ft_lines_ok(int grid[4][4])
{
    int    i;
    int    j;
    int    k;

    i = 0;
    while (i < 4)
    {
        j = 0;
        while (j < 4)
        {
            k = j + 1;
            while (k < 4)
            {
                if (grid[i][j] == grid[i][k] || grid[j][i] == grid[k][i])
                    return (0);
                k++;
            }
            j++;
        }
        i++;
    }
    return (1);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    v;

    if (pos == 16)
        return (ft_lines_ok(grid) && ft_check_all(grid, clues));
    v = 1;
    while (v <= 4)
    {
        grid[pos / 4][pos % 4] = v;
        if (ft_solve(grid, clues, pos + 1))
            return (1);
        v++;
    }
    grid[pos / 4][pos % 4] = 0;
    return (0);
}
"""

SOLVE_CLUE_LINE = """\
#include "rush.h"

int    ft_row_ok(int grid[4][4], int *clues, int row)
{
    return (ft_count_row(grid, row, 0) == clues[8 + row]
        && ft_count_row(grid, row, 1) == clues[12 + row]);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    v;
    int    r;
    int    c;

    if (pos == 16)
        return (ft_check_all(grid, clues));
    r = pos / 4;
    c = pos % 4;
    v = 1;
    while (v <= 4)
    {
        if (ft_is_free(grid, r, c, v))
        {
            grid[r][c] = v;
            if ((c != 3 || ft_row_ok(grid, clues, r))
                && ft_solve(grid, clues, pos + 1))
                return (1);
            grid[r][c] = 0;
        }
        v++;
    }
    return (0);
}
"""

SOLVE_ITER = """\
#include "rush.h"

int    ft_is_ok(int grid[4][4], int pos)
{
    int    i;
    int    r;
    int    c;

    r = pos / 4;
    c = pos % 4;
    i = 0;
    while (i < 4)
    {
        if (i != c && grid[r][i] == grid[r][c])
            return (0);
        if (i != r && grid[i][c] == grid[r][c])
            return (0);
        i++;
    }
    return (1);
}

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    pos = 0;
    while (pos >= 0)
    {
        if (pos == 16)
        {
            if (ft_check_all(grid, clues))
                return (1);
            pos--;
        }
        grid[pos / 4][pos % 4]++;
        if (grid[pos / 4][pos % 4] > 4)
        {
            grid[pos / 4][pos % 4] = 0;
            pos--;
        }
        else if (ft_is_ok(grid, pos))
            pos++;
    }
    return (0);
}
"""

SOLVE_ROW_PERM = COPY_ROW + """
int    ft_cols_free(int grid[4][4], int row)
{
    int    c;
    int    i;

    c = 0;
    while (c < 4)
    {
        i = 0;
        while (i < row)
        {
            if (grid[i][c] == grid[row][c])
                return (0);
            i++;
        }
        c++;
    }
    return (1);
}

int    ft_rows(int grid[4][4], int perms[24][4], int *clues, int row)
{
    int    p;

    if (row == 4)
        return (ft_check_all(grid, clues));
    p = 0;
    while (p < 24)
    {
        ft_copy_row(grid, row, perms[p]);
        if (ft_cols_free(grid, row) && ft_rows(grid, perms, clues, row + 1))
            return (1);
        p++;
    }
    return (0);
}

void   ft_fill_perms(int perms[24][4]);

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    perms[24][4];

    ft_fill_perms(perms);
    return (ft_rows(grid, perms, clues, pos));
}
"""

PREFILL = """\
void    ft_prefill(int grid[4][4], int *clues)
{
    int    i;
    int    k;

    i = 0;
    while (i < 4)
    {
        if (clues[i] == 4)
        {
            k = 0;
            while (k < 4)
            {
                grid[k][i] = k + 1;
                k++;
            }
        }
        if (clues[8 + i] == 1)
            grid[i][0] = 4;
        i++;
    }
}
"""

MAIN_PREFILL = MAIN.replace("    if (!ft_solve(grid, clues, 0))",
                            "    ft_prefill(grid, clues);\n"
                            "    if (!ft_solve(grid, clues, 0))").replace(
    "#include \"rush.h\"\n", "#include \"rush.h\"\n\nvoid    ft_prefill(int "
    "grid[4][4], int *clues);\n")

SOLVE_PREFILL_AWARE = SOLVE_BT_UNIQUE.replace(
    "    v = 1;\n", "    if (grid[pos / 4][pos % 4] != 0)\n"
    "        return (ft_solve(grid, clues, pos + 1));\n    v = 1;\n")


class TestB1CatalogIds(TeamCase):

    # parse ---------------------------------------------------------------
    def test_parse_fixed(self):
        self.assert_id(team_files(), "parse", "parse.fixed")

    def test_parse_scan(self):
        self.assert_id(team_files(parse=PARSE_SCAN), "parse", "parse.scan")

    def test_parse_split(self):
        self.assert_id(team_files(parse=PARSE_SPLIT, split=SPLIT), "parse",
                       "parse.split")

    def test_parse_atoi(self):
        self.assert_id(team_files(parse=PARSE_ATOI), "parse", "parse.atoi")

    def test_parse_fsm(self):
        self.assert_id(team_files(parse=PARSE_FSM), "parse", "parse.fsm")

    def test_parse_none(self):
        self.assert_id(team_files(parse=PARSE_NONE, main=MAIN_NO_PARSE_CHECK),
                       "parse", "parse.none")

    # data ----------------------------------------------------------------
    def test_data_grid2d(self):
        self.assert_id(team_files(solve=SOLVE_ROWCOL), "data", "data.grid2d")

    def test_data_padded(self):
        self.assert_id(PADDED, "data", "data.padded")

    def test_data_malloc2d(self):
        solve = SOLVE_BT_UNIQUE.replace("int grid[4][4]", "int **grid")
        self.assert_id(team_files(main=MAIN_MALLOC, solve=solve), "data",
                       "data.malloc2d")

    def test_data_flat(self):
        main = MAIN.replace("int    grid[4][4];", "int    grid[16];").replace(
            "grid[i / 4][i % 4] = 0;", "grid[i] = 0;")
        self.assert_id(team_files(main=main, solve=SOLVE_FLAT,
                                  check=CHECK_FLAT), "data", "data.flat")

    def test_data_char(self):
        main = MAIN.replace("int    grid[4][4];", "char    grid[4][4];")
        self.assert_id(team_files(main=main, solve=SOLVE_CHAR,
                                  print=PRINT_CHAR_GRID), "data", "data.char")

    def test_data_struct(self):
        self.assert_id(team_files(rush_h=STRUCT_H, main=STRUCT_MAIN,
                                  solve=STRUCT_SOLVE), "data", "data.struct")

    def test_data_bits(self):
        v = self.part(team_files(solve=SOLVE_BITS), "data")
        self.assertIn("data.bits", [v["id"]] + v["also"], self.explain(v))

    def test_data_cand(self):
        v = self.part(team_files(solve=SOLVE_CANDS), "data")
        self.assertIn("data.cand", [v["id"]] + v["also"], self.explain(v))

    # print ---------------------------------------------------------------
    def test_print_char(self):
        self.assert_id(team_files(), "print", "print.char")

    def test_print_line(self):
        self.assert_id(team_files(print=PRINT_LINE), "print", "print.line")

    def test_print_board(self):
        self.assert_id(team_files(print=PRINT_BOARD), "print", "print.board")

    def test_print_putstr(self):
        self.assert_id(team_files(print=PRINT_PUTSTR), "print",
                       "print.putstr")

    # solve, tiers 0-2 ----------------------------------------------------
    def test_solve_hardcode(self):
        self.assert_id({"main.c": HARDCODE_MAIN}, "solve", "solve.hardcode")

    def test_solve_brute16(self):
        self.assert_id(team_files(solve=SOLVE_BRUTE16), "solve",
                       "solve.brute16")

    def test_solve_brute_perm_loops(self):
        self.assert_id(team_files(solve=SOLVE_PERM_LOOPS, perms=PERMS,
                                  cols=COLS_UNIQUE), "solve",
                       "solve.brute_perm_loops")

    def test_solve_bt_end(self):
        self.assert_id(team_files(solve=SOLVE_BT_END), "solve",
                       "solve.bt_end")

    def test_solve_bt_unique(self):
        self.assert_id(team_files(), "solve", "solve.bt_unique")

    def test_solve_bt_clue_line(self):
        self.assert_id(team_files(solve=SOLVE_CLUE_LINE), "solve",
                       "solve.bt_clue_line")

    def test_solve_bt_iter(self):
        self.assert_id(team_files(solve=SOLVE_ITER), "solve", "solve.bt_iter")

    def test_solve_row_perm(self):
        self.assert_id(team_files(solve=SOLVE_ROW_PERM, perms=PERMS), "solve",
                       "solve.row_perm")

    def test_solve_prefill(self):
        v = self.assert_id(team_files(main=MAIN_PREFILL, prefill=PREFILL,
                                      solve=SOLVE_PREFILL_AWARE), "solve",
                           "solve.prefill")
        self.assertEqual(v["also"], ["solve.bt_unique"], self.explain(v))

    def test_solve_cands(self):
        self.assert_id(team_files(solve=SOLVE_CANDS), "solve", "solve.cands")


if __name__ == "__main__":
    unittest.main()
