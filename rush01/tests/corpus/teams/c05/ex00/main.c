#include "sky.h"

int	main(int ac, char **av)
{
	int	grid[16];
	int	clue[16];
	int	i;

	i = 0;
	while (i < 16)
	{
		grid[i] = 0;
		i++;
	}
	if (ac != 2 || !ft_scan(av[1], clue) || !ft_fill(grid, clue, 0))
	{
		write(1, "Error\n", 6);
		return (0);
	}
	ft_show(grid);
	return (0);
}
