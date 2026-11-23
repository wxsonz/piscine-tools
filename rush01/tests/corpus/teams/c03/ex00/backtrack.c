#include "rush01.h"

static int	fits(int **g, int row, int col, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (g[row][i] == v || g[i][col] == v)
			return (0);
		i++;
	}
	return (1);
}

static int	next_cell(int **g, int *clue, int row, int col)
{
	if (col == 3)
		return (ft_bt(g, clue, row + 1, 0));
	return (ft_bt(g, clue, row, col + 1));
}

int	ft_bt(int **g, int *clue, int row, int col)
{
	int	v;

	if (row == 4)
		return (ft_cols_ok(g, clue));
	v = 1;
	while (v <= 4)
	{
		if (fits(g, row, col, v))
		{
			g[row][col] = v;
			if (ft_row_end_ok(g, clue, row, col)
				&& next_cell(g, clue, row, col))
				return (1);
			g[row][col] = 0;
		}
		v++;
	}
	return (0);
}
