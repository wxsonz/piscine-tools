#include "sky.h"

static int	ft_row_free(int *grid, int pos, int v)
{
	int	i;

	i = pos - pos % 4;
	while (i < pos)
	{
		if (grid[i] == v)
			return (0);
		i++;
	}
	return (1);
}

int	ft_fill(int *grid, int *clue, int pos)
{
	int	v;

	if (pos == 16)
		return (ft_valid(grid, clue));
	v = 1;
	while (v <= 4)
	{
		if (ft_row_free(grid, pos, v))
		{
			grid[pos] = v;
			if (ft_fill(grid, clue, pos + 1))
				return (1);
		}
		v++;
	}
	grid[pos] = 0;
	return (0);
}
