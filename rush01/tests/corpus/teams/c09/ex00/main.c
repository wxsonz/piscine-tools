#include "rush01.h"

int	main(int argc, char **argv)
{
	int	clue[16];
	int	grid[4][4];

	if (argc != 2)
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_get_clues(argv[1], clue);
	if (!ft_brute(grid, clue))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_put_grid(grid);
	return (0);
}
