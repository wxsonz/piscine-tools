#include "board.h"

int	main(int argc, char **argv)
{
	int	b[6][6];

	ft_clear(b);
	if (argc != 2 || !ft_load(argv[1], b) || !ft_walk(b))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	ft_out(b);
	return (0);
}
