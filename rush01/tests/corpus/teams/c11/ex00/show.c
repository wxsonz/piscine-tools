#include "rush01.h"

void	ft_show(int **m, int n)
{
	char	line[20];
	int		r;
	int		i;

	r = 0;
	while (r < n)
	{
		i = 0;
		while (i < n)
		{
			line[i * 2] = m[r][i] + '0';
			line[i * 2 + 1] = ' ';
			i++;
		}
		line[n * 2 - 1] = '\n';
		write(1, line, n * 2);
		r++;
	}
}
