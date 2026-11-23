#include "rush.h"

int	parse_clues(char *str, int *clues, int *n)
{
	int	i;
	int	count;

	i = 0;
	count = 0;
	while (str[i])
	{
		if (str[i] >= '1' && str[i] <= '9')
		{
			if (count == 36)
				return (0);
			clues[count] = str[i] - '0';
			count++;
		}
		else if (str[i] != ' ')
			return (0);
		i++;
	}
	*n = count / 4;
	return (count % 4 == 0 && *n >= 1);
}

static void	clear_grid(int grid[9][9])
{
	int	i;

	i = 0;
	while (i < 81)
	{
		grid[i / 9][i % 9] = 0;
		i++;
	}
}

int	main(int argc, char **argv)
{
	int	clues[36];
	int	grid[9][9];
	int	n;

	if (argc != 2 || !parse_clues(argv[1], clues, &n))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	clear_grid(grid);
	if (!solve(grid, clues, n, 0))
	{
		write(1, "Error\n", 6);
		return (1);
	}
	print_grid(grid, n);
	return (0);
}
