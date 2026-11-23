#include "sky.h"

void	ft_putchar(char c)
{
	write(1, &c, 1);
}

void	ft_putnbr(int n)
{
	if (n >= 10)
		ft_putnbr(n / 10);
	ft_putchar(n % 10 + '0');
}

void	ft_show(int *grid)
{
	int	i;

	i = 0;
	while (i < 16)
	{
		ft_putnbr(grid[i]);
		if (i % 4 == 3)
			ft_putchar('\n');
		else
			ft_putchar(' ');
		i++;
	}
}
