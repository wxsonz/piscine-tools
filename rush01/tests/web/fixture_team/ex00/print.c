#include "rush.h"

static void	ft_putchar(char c)
{
	write(1, &c, 1);
}

void	print_grid(int grid[9][9], int n)
{
	int	r;
	int	c;

	r = 0;
	while (r < n)
	{
		c = 0;
		while (c < n)
		{
			ft_putchar(grid[r][c] + '0');
			if (c < n - 1)
				ft_putchar(' ');
			c++;
		}
		ft_putchar('\n');
		r++;
	}
}
