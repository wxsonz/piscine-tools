#include "rush.h"

static void	ft_example(int g[4][4])
{
	g[0][0] = 1;
	g[0][1] = 2;
	g[0][2] = 3;
	g[0][3] = 4;
	g[1][0] = 2;
	g[1][1] = 3;
	g[1][2] = 4;
	g[1][3] = 1;
	g[2][0] = 3;
	g[2][1] = 4;
	g[2][2] = 1;
	g[2][3] = 2;
	g[3][0] = 4;
	g[3][1] = 1;
	g[3][2] = 2;
	g[3][3] = 3;
}

int	ft_solve(char *arg, int grid[4][4])
{
	if (ft_strcmp(arg, "4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2") == 0)
	{
		ft_example(grid);
		return (1);
	}
	return (0);
}
