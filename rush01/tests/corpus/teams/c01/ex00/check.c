#include "rush.h"

static int	ft_seen(int a, int b, int c, int d)
{
	int	max;
	int	count;

	max = a;
	count = 1;
	if (b > max)
	{
		max = b;
		count++;
	}
	if (c > max)
	{
		max = c;
		count++;
	}
	if (d > max)
		count++;
	return (count);
}

int	ft_is_valid(int grid[4][4], int pos, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (grid[pos / 4][i] == v)
			return (0);
		if (grid[i][pos % 4] == v)
			return (0);
		i++;
	}
	return (1);
}

static int	ft_check_cols(int g[4][4], int *clue)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (ft_seen(g[0][i], g[1][i], g[2][i], g[3][i]) != clue[i])
			return (0);
		if (ft_seen(g[3][i], g[2][i], g[1][i], g[0][i]) != clue[4 + i])
			return (0);
		i++;
	}
	return (1);
}

int	ft_check_clues(int g[4][4], int *clue)
{
	int	i;

	if (!ft_check_cols(g, clue))
		return (0);
	i = 0;
	while (i < 4)
	{
		if (ft_seen(g[i][0], g[i][1], g[i][2], g[i][3]) != clue[8 + i])
			return (0);
		if (ft_seen(g[i][3], g[i][2], g[i][1], g[i][0]) != clue[12 + i])
			return (0);
		i++;
	}
	return (1);
}
