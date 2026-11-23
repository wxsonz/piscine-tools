#include "rush01.h"

char	*ft_perm(int i)
{
	static char	*list[24] = {"1234", "1243", "1324", "1342", "1423", "1432",
		"2134", "2143", "2314", "2341", "2413", "2431",
		"3124", "3142", "3214", "3241", "3412", "3421",
		"4123", "4132", "4213", "4231", "4312", "4321"};

	return (list[i]);
}

void	ft_load(int grid[4][4], int *pick)
{
	int	r;
	int	c;

	r = 0;
	while (r < 4)
	{
		c = 0;
		while (c < 4)
		{
			grid[r][c] = ft_perm(pick[r])[c] - '0';
			c++;
		}
		r++;
	}
}
