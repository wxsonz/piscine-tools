#include "board.h"

int	main(int argc, char **argv)
{
	t_board	b;
	int		i;

	i = 0;
	while (i < 16)
	{
		b.grid[i / 4][i % 4] = 0;
		i++;
	}
	if (argc != 2 || !ft_parse(argv[1], &b) || !ft_prefill(&b)
		|| !ft_search(&b, 0))
	{
		ft_putstr("Error\n");
		return (1);
	}
	ft_print_board(&b);
	return (0);
}
