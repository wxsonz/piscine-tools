#include "sky.h"

int	ft_look(int *grid, int start, int step)
{
	int	i;
	int	max;
	int	seen;
	int	pos;

	max = 0;
	seen = 0;
	i = 0;
	pos = start;
	while (i < 4)
	{
		if (grid[pos] > max)
		{
			max = grid[pos];
			seen++;
		}
		pos += step;
		i++;
	}
	return (seen);
}

static int	ft_col_mask(int *grid, int c)
{
	int	mask;
	int	r;

	mask = 0;
	r = 0;
	while (r < 4)
	{
		mask += 1 << grid[c + r * 4];
		r++;
	}
	return (mask);
}

int	ft_valid(int *grid, int *clue)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (ft_col_mask(grid, i) != 30)
			return (0);
		if (ft_look(grid, i, 4) != clue[i])
			return (0);
		if (ft_look(grid, 12 + i, -4) != clue[4 + i])
			return (0);
		if (ft_look(grid, i * 4, 1) != clue[8 + i])
			return (0);
		if (ft_look(grid, i * 4 + 3, -1) != clue[12 + i])
			return (0);
		i++;
	}
	return (1);
}
