#include "board.h"

static int	ft_seen(int *l, int start, int step)
{
	int	i;
	int	max;
	int	seen;

	max = 0;
	seen = 0;
	i = 0;
	while (i < 4)
	{
		if (l[start + i * step] > max)
		{
			max = l[start + i * step];
			seen++;
		}
		i++;
	}
	return (seen);
}

static int	ft_latin(t_board *b)
{
	int	i;
	int	j;
	int	row;
	int	col;

	i = 0;
	while (i < 4)
	{
		row = 0;
		col = 0;
		j = 0;
		while (j < 4)
		{
			row = row + (1 << b->grid[i][j]);
			col = col + (1 << b->grid[j][i]);
			j++;
		}
		if (row != 30 || col != 30)
			return (0);
		i++;
	}
	return (1);
}

int	ft_verify(t_board *b)
{
	int	*g;
	int	i;

	if (!ft_latin(b))
		return (0);
	g = &b->grid[0][0];
	i = 0;
	while (i < 4)
	{
		if (ft_seen(g, i, 4) != b->clue[i])
			return (0);
		if (ft_seen(g, 12 + i, -4) != b->clue[4 + i])
			return (0);
		if (ft_seen(g, i * 4, 1) != b->clue[8 + i])
			return (0);
		if (ft_seen(g, i * 4 + 3, -1) != b->clue[12 + i])
			return (0);
		i++;
	}
	return (1);
}
