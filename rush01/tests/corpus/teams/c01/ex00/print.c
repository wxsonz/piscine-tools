#include "rush.h"

void	ft_putchar(char c)
{
	write(1, &c, 1);
}

void	ft_error(void)
{
	write(1, "Error\n", 6);
}

void	ft_print_grid(int grid[4][4])
{
	int	r;
	int	c;

	r = 0;
	while (r < 4)
	{
		c = 0;
		while (c < 4)
		{
			ft_putchar(grid[r][c] + '0');
			if (c < 3)
				ft_putchar(' ');
			c++;
		}
		ft_putchar('\n');
		r++;
	}
}
