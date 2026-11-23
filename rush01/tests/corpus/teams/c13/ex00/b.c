#include "h.h"

int	f4(int *a)
{
	int	i;
	int	m;
	int	n;

	i = 0;
	m = 0;
	n = 0;
	while (i < 4)
	{
		if (a[i] > m)
		{
			m = a[i];
			n++;
		}
		i++;
	}
	return (n);
}

static int	chk(void)
{
	int	i;
	int	j;
	int	t[4];
	int	u[4];

	i = 0;
	while (i < 4)
	{
		j = 0;
		while (j < 4)
		{
			t[j] = g_grid[j][i];
			u[j] = g_grid[3 - j][i];
			j++;
		}
		if (f4(t) != g_clue[i] || f4(u) != g_clue[4 + i])
			return (0);
		if (f4(g_grid[i]) != g_clue[8 + i])
			return (0);
		i++;
	}
	return (1);
}

static int	chk2(void)
{
	int	i;
	int	j;
	int	r[4];

	i = 0;
	while (i < 4)
	{
		j = 0;
		while (j < 4)
		{
			r[j] = g_grid[i][3 - j];
			j++;
		}
		if (f4(r) != g_clue[12 + i])
			return (0);
		i++;
	}
	return (1);
}

int	f3(int pos)
{
	int	v;

	if (pos == 16)
		return (chk() && chk2());
	v = 1;
	while (v <= 4)
	{
		if (f2(pos, v))
		{
			g_grid[pos / 4][pos % 4] = v;
			if (f3(pos + 1))
				return (1);
			g_grid[pos / 4][pos % 4] = 0;
		}
		v++;
	}
	return (0);
}
