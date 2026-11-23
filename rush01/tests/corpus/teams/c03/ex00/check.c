#include "rush01.h"

static int	vis(int a, int b, int c, int d)
{
	int	top;
	int	n;

	top = a;
	n = 1;
	if (b > top)
	{
		top = b;
		n++;
	}
	if (c > top)
	{
		top = c;
		n++;
	}
	if (d > top)
		n++;
	return (n);
}

int	ft_cols_ok(int **g, int *clue)
{
	int	c;

	c = 0;
	while (c < 4)
	{
		if (vis(g[0][c], g[1][c], g[2][c], g[3][c]) != clue[c])
			return (0);
		if (vis(g[3][c], g[2][c], g[1][c], g[0][c]) != clue[4 + c])
			return (0);
		c++;
	}
	return (1);
}

int	ft_row_end_ok(int **g, int *clue, int row, int col)
{
	if (col < 3)
		return (1);
	if (vis(g[row][0], g[row][1], g[row][2], g[row][3]) != clue[8 + row])
		return (0);
	if (vis(g[row][3], g[row][2], g[row][1], g[row][0]) != clue[12 + row])
		return (0);
	return (1);
}
