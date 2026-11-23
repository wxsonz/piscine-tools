#include "rush.h"

static int	seen(int *line, int n)
{
	int	i;
	int	max;
	int	count;

	i = 0;
	max = 0;
	count = 0;
	while (i < n)
	{
		if (line[i] > max)
		{
			max = line[i];
			count++;
		}
		i++;
	}
	return (count);
}

int	row_ok(int grid[9][9], int *clues, int n, int row)
{
	int	line[9];
	int	i;

	i = -1;
	while (++i < n)
		line[i] = grid[row][i];
	if (seen(line, n) != clues[row])
		return (0);
	i = -1;
	while (++i < n)
		line[i] = grid[row][n - 1 - i];
	return (seen(line, n) == clues[n + row]);
}

int	col_ok(int grid[9][9], int *clues, int n, int col)
{
	int	line[9];
	int	i;

	i = -1;
	while (++i < n)
		line[i] = grid[i][col];
	if (seen(line, n) != clues[2 * n + col])
		return (0);
	i = -1;
	while (++i < n)
		line[i] = grid[n - 1 - i][col];
	return (seen(line, n) == clues[3 * n + col]);
}

static int	fits(int grid[9][9], int n, int pos, int v)
{
	int	i;

	i = 0;
	while (i < n)
	{
		if (grid[pos / n][i] == v || grid[i][pos % n] == v)
			return (0);
		i++;
	}
	return (1);
}

int	solve(int grid[9][9], int *clues, int n, int pos)
{
	int	v;

	if (pos == n * n)
		return (1);
	v = 0;
	while (++v <= n)
	{
		if (!fits(grid, n, pos, v))
			continue ;
		grid[pos / n][pos % n] = v;
		if ((pos % n != n - 1 || row_ok(grid, clues, n, pos / n))
			&& (pos / n != n - 1 || col_ok(grid, clues, n, pos % n))
			&& solve(grid, clues, n, pos + 1))
			return (1);
		grid[pos / n][pos % n] = 0;
	}
	return (0);
}
