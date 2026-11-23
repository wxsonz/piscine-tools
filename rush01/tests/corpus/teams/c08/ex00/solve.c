#include "skyline.h"

static int	ft_seen(int a, int b, int c, int d)
{
	int	best;
	int	n;

	best = a;
	n = 1;
	if (b > best)
	{
		best = b;
		n++;
	}
	if (c > best)
	{
		best = c;
		n++;
	}
	if (d > best)
		n++;
	return (n);
}

int	ft_check(int g[4][4], int *clue)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (ft_seen(g[0][i], g[1][i], g[2][i], g[3][i]) != clue[i])
			return (0);
		if (ft_seen(g[3][i], g[2][i], g[1][i], g[0][i]) != clue[4 + i])
			return (0);
		if (ft_seen(g[i][0], g[i][1], g[i][2], g[i][3]) != clue[8 + i])
			return (0);
		if (ft_seen(g[i][3], g[i][2], g[i][1], g[i][0]) != clue[12 + i])
			return (0);
		i++;
	}
	return (1);
}

int	ft_cands(int grid[4][4], int cand[4][4][4], int *clue, int pos)
{
	int	next[4][4][4];
	int	v;

	if (pos == 16)
		return (ft_check(grid, clue));
	v = 0;
	while (v < 4)
	{
		if (cand[pos / 4][pos % 4][v])
		{
			ft_copy_cand(next, cand);
			ft_remove(next, pos / 4, pos % 4, v);
			grid[pos / 4][pos % 4] = v + 1;
			if (ft_cands(grid, next, clue, pos + 1))
				return (1);
		}
		v++;
	}
	grid[pos / 4][pos % 4] = 0;
	return (0);
}
