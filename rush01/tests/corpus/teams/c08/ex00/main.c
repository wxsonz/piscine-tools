#include "skyline.h"

int	main(int argc, char **argv)
{
	int	clue[16];
	int	grid[4][4];
	int	cand[4][4][4];

	if (argc != 2 || !ft_get_clues(argv[1], clue))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_init_cand(cand);
	if (!ft_cands(grid, cand, clue, 0))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_print_all(grid);
	return (0);
}
