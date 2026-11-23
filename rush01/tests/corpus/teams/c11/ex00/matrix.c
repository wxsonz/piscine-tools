#include "rush01.h"

int	**ft_new_matrix(int n)
{
	int	**m;
	int	i;
	int	j;

	m = malloc(sizeof(int *) * n);
	if (m == NULL)
		return (NULL);
	i = 0;
	while (i < n)
	{
		m[i] = malloc(sizeof(int) * n);
		if (m[i] == NULL)
			return (NULL);
		j = 0;
		while (j < n)
		{
			m[i][j] = 0;
			j++;
		}
		i++;
	}
	return (m);
}

void	ft_free_matrix(int **m, int n)
{
	int	i;

	i = 0;
	while (i < n)
	{
		free(m[i]);
		i++;
	}
	free(m);
}
