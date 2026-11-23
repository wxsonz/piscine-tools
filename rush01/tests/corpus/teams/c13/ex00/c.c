#include "h.h"

void	f5(char c)
{
	write(1, &c, 1);
}

void	f6(void)
{
	int	i;

	i = 0;
	while (i < 16)
	{
		f5(g_grid[i / 4][i % 4] + '0');
		if (i % 4 == 3)
			f5('\n');
		else
			f5(' ');
		i++;
	}
}
