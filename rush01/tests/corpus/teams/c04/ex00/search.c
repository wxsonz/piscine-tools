#include "board.h"

static int	ft_ok_here(t_board *b, int pos, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (b->grid[pos / 4][i] == v || b->grid[i][pos % 4] == v)
			return (0);
		i++;
	}
	return (1);
}

int	ft_search(t_board *b, int pos)
{
	int	v;

	if (pos == 16)
		return (ft_verify(b));
	if (b->grid[pos / 4][pos % 4] != 0)
		return (ft_search(b, pos + 1));
	v = 1;
	while (v <= 4)
	{
		if (ft_ok_here(b, pos, v))
		{
			b->grid[pos / 4][pos % 4] = v;
			if (ft_search(b, pos + 1))
				return (1);
			b->grid[pos / 4][pos % 4] = 0;
		}
		v++;
	}
	return (0);
}
