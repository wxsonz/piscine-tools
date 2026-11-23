#include "rush01.h"

static int	ft_inner(int grid[4][4], int *clue, int *pick)
{
	pick[2] = 0;
	while (pick[2] < 24)
	{
		pick[3] = 0;
		while (pick[3] < 24)
		{
			ft_load(grid, pick);
			if (ft_all_ok(grid, clue))
				return (1);
			pick[3]++;
		}
		pick[2]++;
	}
	return (0);
}

int	ft_brute(int grid[4][4], int *clue)
{
	int	pick[4];

	pick[0] = 0;
	while (pick[0] < 24)
	{
		pick[1] = 0;
		while (pick[1] < 24)
		{
			if (ft_inner(grid, clue, pick))
				return (1);
			pick[1]++;
		}
		pick[0]++;
	}
	return (0);
}
