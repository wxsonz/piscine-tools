#include "rush01.h"

static int	ft_cols_ok(int grid[4][4], int *clue)
{
	int	tmp[4];
	int	c;
	int	r;

	c = 0;
	while (c < 4)
	{
		r = 0;
		while (r < 4)
		{
			tmp[r] = grid[r][c];
			r++;
		}
		if (ft_vis(tmp, 0) != clue[c] || ft_vis(tmp, 1) != clue[4 + c])
			return (0);
		c++;
	}
	return (1);
}

static int	ft_row_ok(int grid[4][4], int *clue, int r)
{
	int	c;
	int	up;

	if (ft_vis(grid[r], 0) != clue[8 + r])
		return (0);
	if (ft_vis(grid[r], 1) != clue[12 + r])
		return (0);
	up = 0;
	while (up < r)
	{
		c = 0;
		while (c < 4)
		{
			if (grid[up][c] == grid[r][c])
				return (0);
			c++;
		}
		up++;
	}
	return (1);
}

int	ft_rows(int grid[4][4], int *clue, int r)
{
	int	p;
	int	c;

	if (r == 4)
		return (ft_cols_ok(grid, clue));
	p = 0;
	while (p < 24)
	{
		c = 0;
		while (c < 4)
		{
			grid[r][c] = g_perm[p][c];
			c++;
		}
		if (ft_row_ok(grid, clue, r) && ft_rows(grid, clue, r + 1))
			return (1);
		p++;
	}
	return (0);
}
