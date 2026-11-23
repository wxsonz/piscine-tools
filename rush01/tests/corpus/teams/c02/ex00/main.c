#include "skyscraper.h"

static void	ft_fail(void)
{
	write(1, "Error\n", 6);
}

int	main(int ac, char **av)
{
	int	views[4][4];
	int	grid[4][4];
	int	i;

	if (ac != 2 || !ft_read_input(av[1], views))
	{
		ft_fail();
		return (0);
	}
	i = 0;
	while (i < 16)
	{
		grid[i / 4][i % 4] = 0;
		i++;
	}
	if (ft_place(grid, views, 0, 0))
		ft_print_rows(grid);
	else
		ft_fail();
	return (0);
}
