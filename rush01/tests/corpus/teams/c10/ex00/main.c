#include "rush.h"

int	main(int argc, char **argv)
{
	int	clue[16];
	int	grid[4][4];

	if (argc != 2 || !ft_parse(argv[1], clue))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	if (!ft_solve(argv[1], grid))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_print(grid);
	return (0);
}
