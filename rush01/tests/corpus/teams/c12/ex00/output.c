#include "skyscraper.h"

void	ft_putchar(char c)
{
	write(1, &c, 1);
}

void	ft_error(void)
{
	write(2, "Error\n", 6);
}

void	ft_print_grid(int *grid)
{
	int	i;

	i = 0;
	while (i < 16)
	{
		ft_putchar(grid[i] + '0');
		if (i % 4 == 3)
			ft_putchar('\n');
		else
			ft_putchar(' ');
		i++;
	}
}
