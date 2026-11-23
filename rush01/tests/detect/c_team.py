"""Small fake teams for the detect tests: Norm-style C parts written into a
temp dir (PROOF-9). A test swaps one part and checks that part's verdict.

In the C below, 4 spaces stand for one tab (the Norm indents with tabs);
team_write turns them back into tabs.
"""

import os
import tempfile
import unittest

from detect import detect_team

HEADER = """\
#ifndef RUSH_H
# define RUSH_H

int     ft_parse(char *str, int *clues);
int     ft_solve(int grid[4][4], int *clues, int pos);
void    ft_print(int grid[4][4]);
int     ft_is_free(int grid[4][4], int row, int col, int v);
int     ft_check_all(int grid[4][4], int *clues);
int     ft_count_row(int grid[4][4], int row, int rev);
int     ft_count_col(int grid[4][4], int col, int rev);
void    ft_error(void);

#endif
"""

MAIN = """\
#include <unistd.h>
#include "rush.h"

void    ft_error(void)
{
    write(1, "Error\\n", 6);
}

int    main(int argc, char **argv)
{
    int    clues[16];
    int    grid[4][4];
    int    i;

    if (argc != 2 || !ft_parse(argv[1], clues))
    {
        ft_error();
        return (1);
    }
    i = 0;
    while (i < 16)
    {
        grid[i / 4][i % 4] = 0;
        i++;
    }
    if (!ft_solve(grid, clues, 0))
    {
        ft_error();
        return (1);
    }
    ft_print(grid);
    return (0);
}
"""

PARSE_FIXED = """\
int    ft_strlen(char *str)
{
    int    i;

    i = 0;
    while (str[i] != '\\0')
        i++;
    return (i);
}

int    ft_parse(char *str, int *clues)
{
    int    i;

    if (ft_strlen(str) != 31)
        return (0);
    i = 0;
    while (i < 31)
    {
        if (i % 2 == 0 && (str[i] < '1' || str[i] > '4'))
            return (0);
        if (i % 2 == 1 && str[i] != ' ')
            return (0);
        if (i % 2 == 0)
            clues[i / 2] = str[i] - '0';
        i++;
    }
    return (1);
}
"""

CHECK = """\
int    ft_is_free(int grid[4][4], int row, int col, int v)
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

int    ft_count_row(int grid[4][4], int row, int rev)
{
    int    i;
    int    max;
    int    count;
    int    cell;

    i = 0;
    max = 0;
    count = 0;
    while (i < 4)
    {
        cell = grid[row][i];
        if (rev)
            cell = grid[row][3 - i];
        if (cell > max)
        {
            max = cell;
            count++;
        }
        i++;
    }
    return (count);
}

int    ft_count_col(int grid[4][4], int col, int rev)
{
    int    i;
    int    max;
    int    count;
    int    cell;

    i = 0;
    max = 0;
    count = 0;
    while (i < 4)
    {
        cell = grid[i][col];
        if (rev)
            cell = grid[3 - i][col];
        if (cell > max)
        {
            max = cell;
            count++;
        }
        i++;
    }
    return (count);
}

int    ft_check_all(int grid[4][4], int *clues)
{
    int    i;

    i = 0;
    while (i < 4)
    {
        if (ft_count_col(grid, i, 0) != clues[i])
            return (0);
        if (ft_count_col(grid, i, 1) != clues[4 + i])
            return (0);
        if (ft_count_row(grid, i, 0) != clues[8 + i])
            return (0);
        if (ft_count_row(grid, i, 1) != clues[12 + i])
            return (0);
        i++;
    }
    return (1);
}
"""

SOLVE_BT_UNIQUE = """\
#include "rush.h"

int    ft_solve(int grid[4][4], int *clues, int pos)
{
    int    v;

    if (pos == 16)
        return (ft_check_all(grid, clues));
    v = 1;
    while (v <= 4)
    {
        if (ft_is_free(grid, pos / 4, pos % 4, v))
        {
            grid[pos / 4][pos % 4] = v;
            if (ft_solve(grid, clues, pos + 1))
                return (1);
            grid[pos / 4][pos % 4] = 0;
        }
        v++;
    }
    return (0);
}
"""

PRINT_CHAR = """\
#include <unistd.h>

void    ft_putchar(char c)
{
    write(1, &c, 1);
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
            ft_putchar(grid[r][c] + '0');
            if (c < 3)
                ft_putchar(' ');
            c++;
        }
        ft_putchar('\\n');
        r++;
    }
}
"""

DEFAULT = {"rush.h": HEADER, "main.c": MAIN, "parse.c": PARSE_FIXED,
           "check.c": CHECK, "solve.c": SOLVE_BT_UNIQUE,
           "print.c": PRINT_CHAR}


def team_files(**parts):
    """The default team with some files replaced (None drops a file)."""
    files = dict(DEFAULT)
    for name, text in parts.items():
        key = name.replace("_", ".") if "_" in name else name + ".c"
        if text is None:
            files.pop(key, None)
        else:
            files[key] = text
    return files


def team_write(root, files, ex_dir="ex00"):
    """Write files under root/ex_dir; 4 spaces become one tab (the Norm)."""
    folder = os.path.join(root, ex_dir)
    os.makedirs(folder, exist_ok=True)
    for name, text in files.items():
        path = os.path.join(folder, name)
        if isinstance(text, bytes):
            with open(path, "wb") as fh:
                fh.write(text)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace("    ", "\t"))
    return root


class TeamCase(unittest.TestCase):
    """detect_team on a team written into a fresh temp dir."""

    def detect(self, files, ex_dir="ex00"):
        with tempfile.TemporaryDirectory(prefix="rush01-detect-") as tmp:
            team_write(tmp, files, ex_dir)
            result = detect_team(tmp, ex_dir)
        self.assertIsNone(result["error"], result["error"])
        return result

    def part(self, files, part):
        return self.detect(files)["parts"][part]

    def assert_id(self, files, part, want):
        v = self.part(files, part)
        self.assertEqual(v["id"], want, self.explain(v))
        return v

    @staticmethod
    def explain(v):
        lines = [f"got {v['id']} ({v['confidence']}) also={v['also']}"]
        lines += [f"  {e['file']}:{e['line']} {e['why']}"
                  for e in v["evidence"]]
        lines += [f"  fact {f['key']}: {f['text']}" for f in v["facts"]]
        return "\n".join(lines)
