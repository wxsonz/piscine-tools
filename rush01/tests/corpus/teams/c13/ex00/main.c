#include "h.h"

int	g_clue[16];
int	g_grid[4][4];

int	main(int ac, char **av)
{
	if (ac != 2 || !f1(av[1]) || !f3(0))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	f6();
	return (0);
}
