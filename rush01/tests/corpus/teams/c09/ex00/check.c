#include "rush01.h"

static int	ft_count(int a, int b, int c, int d)
{
	int	n;

	n = 1;
	if (b > a)
		n++;
	if (c > a && c > b)
		n++;
	if (d > a && d > b && d > c)
		n++;
	return (n);
}

static int	ft_latin(int g[4][4])
{
	int	i;
	int	j;

	i = 0;
	while (i < 4)
	{
		j = 0;
		while (j < i)
		{
			if (g[i][0] == g[j][0] || g[i][1] == g[j][1]
				|| g[i][2] == g[j][2] || g[i][3] == g[j][3])
				return (0);
			j++;
		}
		i++;
	}
	return (1);
}

int	ft_all_ok(int g[4][4], int *clue)
{
	int	i;

	if (!ft_latin(g))
		return (0);
	i = 0;
	while (i < 4)
	{
		if (ft_count(g[0][i], g[1][i], g[2][i], g[3][i]) != clue[i]
			|| ft_count(g[3][i], g[2][i], g[1][i], g[0][i]) != clue[4 + i]
			|| ft_count(g[i][0], g[i][1], g[i][2], g[i][3]) != clue[8 + i]
			|| ft_count(g[i][3], g[i][2], g[i][1], g[i][0]) != clue[12 + i])
			return (0);
		i++;
	}
	return (1);
}
