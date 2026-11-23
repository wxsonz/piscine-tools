#include "skyscraper.h"

int	main(int argc, char **argv)
{
	int	clues[16];
	int	grid[16];
	int	i;

	if (argc != 2 || !ft_parser(argv[1], clues))
	{
		ft_error();
		return (1);
	}
	i = 0;
	while (i < 16)
	{
		grid[i] = 0;
		i++;
	}
	if (!ft_backtrack(grid, clues, 0))
	{
		ft_error();
		return (1);
	}
	ft_print_grid(grid);
	return (0);
}
