#include "skyscraper.h"

int	ft_row_col_ok(int *grid, int pos, int v)
{
	int	i;
	int	row;
	int	col;

	row = pos / 4;
	col = pos % 4;
	i = 0;
	while (i < 4)
	{
		if (grid[row * 4 + i] == v || grid[i * 4 + col] == v)
			return (0);
		i++;
	}
	return (1);
}

static int	ft_visible(int *grid, int start, int step)
{
	int	i;
	int	tallest;
	int	count;

	tallest = 0;
	count = 0;
	i = 0;
	while (i < 4)
	{
		if (grid[start + i * step] > tallest)
		{
			tallest = grid[start + i * step];
			count++;
		}
		i++;
	}
	return (count);
}

int	ft_clues_ok(int *grid, int *clues)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (ft_visible(grid, i, 4) != clues[i])
			return (0);
		if (ft_visible(grid, 12 + i, -4) != clues[4 + i])
			return (0);
		if (ft_visible(grid, i * 4, 1) != clues[8 + i])
			return (0);
		if (ft_visible(grid, i * 4 + 3, -1) != clues[12 + i])
			return (0);
		i++;
	}
	return (1);
}
