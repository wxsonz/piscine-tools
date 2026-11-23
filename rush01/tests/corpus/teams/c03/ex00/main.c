#include "rush01.h"

int	main(int argc, char **argv)
{
	int	clue[16];
	int	**g;

	if (argc != 2 || !ft_parse_clues(argv[1], clue))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	g = ft_new_grid();
	if (g == NULL)
		return (1);
	if (!ft_bt(g, clue, 0, 0))
	{
		ft_free_grid(g);
		write(1, "Error\n", 6);
		return (1);
	}
	ft_show(g);
	ft_free_grid(g);
	return (0);
}
