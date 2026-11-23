#include "rush.h"

int	main(int argc, char **argv)
{
	int	grid[4][4];
	int	clue[16];
	int	i;

	if (argc != 2 || !ft_parse(argv[1], clue))
	{
		ft_error();
		return (1);
	}
	i = 0;
	while (i < 16)
	{
		grid[i / 4][i % 4] = 0;
		i++;
	}
	if (!ft_solve(grid, clue, 0))
	{
		ft_error();
		return (1);
	}
	ft_print_grid(grid);
	return (0);
}
