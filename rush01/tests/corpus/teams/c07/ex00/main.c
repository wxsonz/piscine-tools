#include "rush01.h"

int	main(int argc, char **argv)
{
	int	grid[4][4];
	int	clue[16];

	if (argc != 2 || !ft_parse(argv[1], clue))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	if (!ft_rows(grid, clue, 0))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_display(grid);
	return (0);
}
