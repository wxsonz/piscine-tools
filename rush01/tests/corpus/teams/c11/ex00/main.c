#include "rush01.h"

static int	ft_oops(void)
{
	write(1, "Error\n", 6);
	return (1);
}

int	main(int argc, char **argv)
{
	int	clue[36];
	int	n;
	int	**m;

	if (argc != 2)
		return (ft_oops());
	n = ft_args(argv[1], clue);
	if (n == 0)
		return (ft_oops());
	m = ft_new_matrix(n);
	if (m == NULL)
		return (1);
	if (!ft_place(m, clue, n, 0))
	{
		ft_free_matrix(m, n);
		return (ft_oops());
	}
	ft_show(m, n);
	ft_free_matrix(m, n);
	return (0);
}
