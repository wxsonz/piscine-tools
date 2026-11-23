#include "board.h"

static int	ft_pick(int b[6][6], int pos)
{
	int	v;
	int	r;
	int	c;

	r = pos / 4 + 1;
	c = pos % 4 + 1;
	v = b[r][c] + 1;
	b[r][c] = 0;
	while (v <= 4 && !ft_free_to_put(b, r, c, v))
		v++;
	if (v > 4)
		return (0);
	b[r][c] = v;
	return (1);
}

int	ft_walk(int b[6][6])
{
	int	pos;

	pos = 0;
	while (pos >= 0 && pos < 16)
	{
		if (ft_pick(b, pos))
		{
			pos++;
			if (pos == 16 && ft_clues_ok(b))
				return (1);
			if (pos == 16)
				pos--;
		}
		else
			pos--;
	}
	return (0);
}
