#include "skyline.h"

void	ft_print_all(int grid[4][4])
{
	char	buf[32];
	int		i;

	i = 0;
	while (i < 16)
	{
		buf[i * 2] = grid[i / 4][i % 4] + '0';
		if (i % 4 == 3)
			buf[i * 2 + 1] = '\n';
		else
			buf[i * 2 + 1] = ' ';
		i++;
	}
	write(1, buf, 32);
}
