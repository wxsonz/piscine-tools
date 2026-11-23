#include "rush01.h"

static int	ft_vis(int *line, int n, int rev)
{
	int	i;
	int	max;
	int	seen;
	int	k;

	i = 0;
	max = 0;
	seen = 0;
	while (i < n)
	{
		k = rev * (n - 1) + i * (1 - 2 * rev);
		if (line[k] > max)
		{
			max = line[k];
			seen++;
		}
		i++;
	}
	return (seen);
}

int	ft_can_put(int **m, int n, int pos, int v)
{
	int	i;

	i = 0;
	while (i < n)
	{
		if (m[pos / n][i] == v || m[i][pos % n] == v)
			return (0);
		i++;
	}
	return (1);
}

static int	ft_col_ok(int **m, int *clue, int n, int c)
{
	int	line[9];
	int	i;

	i = 0;
	while (i < n)
	{
		line[i] = m[i][c];
		i++;
	}
	return (ft_vis(line, n, 0) == clue[c]
		&& ft_vis(line, n, 1) == clue[n + c]);
}

int	ft_line_ok(int **m, int *clue, int n, int pos)
{
	int	r;

	r = pos / n;
	if (pos % n == n - 1)
	{
		if (ft_vis(m[r], n, 0) != clue[2 * n + r])
			return (0);
		if (ft_vis(m[r], n, 1) != clue[3 * n + r])
			return (0);
	}
	if (r == n - 1)
		return (ft_col_ok(m, clue, n, pos % n));
	return (1);
}
