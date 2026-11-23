#include "board.h"

void	ft_out(int b[6][6])
{
	char	line[8];
	int		r;
	int		i;

	r = 1;
	while (r <= 4)
	{
		i = 0;
		while (i < 4)
		{
			line[i * 2] = b[r][i + 1] + '0';
			line[i * 2 + 1] = ' ';
			i++;
		}
		line[7] = '\n';
		write(1, line, 8);
		r++;
	}
}
