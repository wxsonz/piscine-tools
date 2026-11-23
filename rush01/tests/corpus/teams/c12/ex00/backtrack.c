#include "skyscraper.h"

int	ft_backtrack(int *grid, int *clues, int pos)
{
	int	v;

	if (pos == 16)
		return (ft_clues_ok(grid, clues));
	v = 1;
	while (v <= 4)
	{
		if (ft_row_col_ok(grid, pos, v))
		{
			grid[pos] = v;
			if (ft_backtrack(grid, clues, pos + 1))
				return (1);
			grid[pos] = 0;
		}
		v++;
	}
	return (0);
}
