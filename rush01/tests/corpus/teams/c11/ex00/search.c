#include "rush01.h"

int	ft_place(int **m, int *clue, int n, int pos)
{
	int	v;

	if (pos == n * n)
		return (1);
	v = 1;
	while (v <= n)
	{
		if (ft_can_put(m, n, pos, v))
		{
			m[pos / n][pos % n] = v;
			if (ft_line_ok(m, clue, n, pos)
				&& ft_place(m, clue, n, pos + 1))
				return (1);
			m[pos / n][pos % n] = 0;
		}
		v++;
	}
	return (0);
}
