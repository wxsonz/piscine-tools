#include "skyscraper.h"

void	ft_print_rows(int grid[4][4])
{
	char	line[8];
	int		row;
	int		i;

	row = 0;
	while (row < 4)
	{
		i = 0;
		while (i < 4)
		{
			line[i * 2] = grid[row][i] + '0';
			line[i * 2 + 1] = ' ';
			i++;
		}
		line[7] = '\n';
		write(1, line, 8);
		row++;
	}
}
