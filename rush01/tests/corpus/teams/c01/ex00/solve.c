#include "rush.h"

int	ft_solve(int grid[4][4], int *clue, int pos)
{
	int	v;

	if (pos == 16)
		return (ft_check_clues(grid, clue));
	v = 1;
	while (v <= 4)
	{
		if (ft_is_valid(grid, pos, v))
		{
			grid[pos / 4][pos % 4] = v;
			if (ft_solve(grid, clue, pos + 1))
				return (1);
			grid[pos / 4][pos % 4] = 0;
		}
		v++;
	}
	return (0);
}
