#include "skyscraper.h"

static int	ft_count(int *l, int start, int dir)
{
	int	i;
	int	max;
	int	seen;
	int	k;

	i = start;
	max = 0;
	seen = 0;
	k = 0;
	while (k < 4)
	{
		if (l[i] > max)
		{
			max = l[i];
			seen++;
		}
		i += dir;
		k++;
	}
	return (seen);
}

int	ft_can_put(int grid[4][4], int row, int col, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (grid[row][i] == v || grid[i][col] == v)
			return (0);
		i++;
	}
	return (1);
}

static int	ft_col_ok(int grid[4][4], int views[4][4], int col)
{
	int	tmp[4];
	int	i;

	i = 0;
	while (i < 4)
	{
		tmp[i] = grid[i][col];
		i++;
	}
	return (ft_count(tmp, 0, 1) == views[0][col]
		&& ft_count(tmp, 3, -1) == views[1][col]);
}

int	ft_lines_ok(int grid[4][4], int views[4][4], int row, int col)
{
	if (col == 3)
	{
		if (ft_count(grid[row], 0, 1) != views[2][row])
			return (0);
		if (ft_count(grid[row], 3, -1) != views[3][row])
			return (0);
	}
	if (row == 3)
		return (ft_col_ok(grid, views, col));
	return (1);
}
