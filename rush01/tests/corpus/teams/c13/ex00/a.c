#include "h.h"

int	f1(char *s)
{
	int	i;
	int	n;

	i = 0;
	n = 0;
	while (s[i])
	{
		if (s[i] >= '1' && s[i] <= '4' && (i == 0 || s[i - 1] == ' '))
		{
			if (n == 16)
				return (0);
			g_clue[n] = s[i] - '0';
			n++;
		}
		else if (s[i] != ' ' || i == 0 || s[i - 1] == ' ' || !s[i + 1])
			return (0);
		i++;
	}
	return (n == 16);
}

int	f2(int pos, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (g_grid[pos / 4][i] == v || g_grid[i][pos % 4] == v)
			return (0);
		i++;
	}
	return (1);
}
