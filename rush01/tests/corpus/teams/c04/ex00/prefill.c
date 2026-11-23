#include "board.h"

static int	ft_set(t_board *b, int r, int c, int v)
{
	if (b->grid[r][c] != 0 && b->grid[r][c] != v)
		return (0);
	b->grid[r][c] = v;
	return (1);
}

static int	ft_fill_col(t_board *b, int c)
{
	int	i;
	int	ok;

	ok = 1;
	i = 0;
	while (i < 4)
	{
		if (b->clue[c] == 4)
			ok = ok && ft_set(b, i, c, i + 1);
		if (b->clue[4 + c] == 4)
			ok = ok && ft_set(b, 3 - i, c, i + 1);
		i++;
	}
	if (b->clue[c] == 1)
		ok = ok && ft_set(b, 0, c, 4);
	if (b->clue[4 + c] == 1)
		ok = ok && ft_set(b, 3, c, 4);
	return (ok);
}

static int	ft_fill_row(t_board *b, int r)
{
	int	i;
	int	ok;

	ok = 1;
	i = 0;
	while (i < 4)
	{
		if (b->clue[8 + r] == 4)
			ok = ok && ft_set(b, r, i, i + 1);
		if (b->clue[12 + r] == 4)
			ok = ok && ft_set(b, r, 3 - i, i + 1);
		i++;
	}
	if (b->clue[8 + r] == 1)
		ok = ok && ft_set(b, r, 0, 4);
	if (b->clue[12 + r] == 1)
		ok = ok && ft_set(b, r, 3, 4);
	return (ok);
}

int	ft_prefill(t_board *b)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (!ft_fill_col(b, i) || !ft_fill_row(b, i))
			return (0);
		i++;
	}
	return (1);
}
