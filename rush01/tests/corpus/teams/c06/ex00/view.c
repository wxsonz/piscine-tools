#include "board.h"

static int	ft_see(int *p, int step)
{
	int	i;
	int	max;
	int	seen;

	max = 0;
	seen = 0;
	i = 0;
	while (i < 4)
	{
		if (*p > max)
		{
			max = *p;
			seen++;
		}
		p += step;
		i++;
	}
	return (seen);
}

int	ft_free_to_put(int b[6][6], int r, int c, int v)
{
	int	k;

	k = 1;
	while (k <= 4)
	{
		if (b[r][k] == v || b[k][c] == v)
			return (0);
		k++;
	}
	return (1);
}

int	ft_clues_ok(int b[6][6])
{
	int	i;

	i = 1;
	while (i <= 4)
	{
		if (ft_see(&b[1][i], 6) != b[0][i])
			return (0);
		if (ft_see(&b[4][i], -6) != b[5][i])
			return (0);
		if (ft_see(&b[i][1], 1) != b[i][0])
			return (0);
		if (ft_see(&b[i][4], -1) != b[i][5])
			return (0);
		i++;
	}
	return (1);
}
