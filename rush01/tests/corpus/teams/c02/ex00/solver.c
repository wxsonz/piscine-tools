#include "skyscraper.h"

static int	ft_next(int grid[4][4], int views[4][4], int row, int col)
{
	if (col == 3)
		return (ft_place(grid, views, row + 1, 0));
	return (ft_place(grid, views, row, col + 1));
}

int	ft_place(int grid[4][4], int views[4][4], int row, int col)
{
	int	v;

	if (row == 4)
		return (1);
	v = 1;
	while (v <= 4)
	{
		if (ft_can_put(grid, row, col, v))
		{
			grid[row][col] = v;
			if (ft_lines_ok(grid, views, row, col)
				&& ft_next(grid, views, row, col))
				return (1);
			grid[row][col] = 0;
		}
		v++;
	}
	return (0);
}
