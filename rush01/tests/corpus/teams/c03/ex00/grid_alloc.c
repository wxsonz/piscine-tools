#include "rush01.h"

void	ft_free_grid(int **g)
{
	int	i;

	i = 0;
	while (i < 4 && g[i])
	{
		free(g[i]);
		i++;
	}
	free(g);
}

int	**ft_new_grid(void)
{
	int	**g;
	int	i;
	int	j;

	g = malloc(sizeof(int *) * 4);
	if (g == NULL)
		return (NULL);
	i = 0;
	while (i < 4)
	{
		g[i] = malloc(sizeof(int) * 4);
		if (g[i] == NULL)
		{
			while (i < 4)
				g[i++] = NULL;
			ft_free_grid(g);
			return (NULL);
		}
		j = 0;
		while (j < 4)
			g[i][j++] = 0;
		i++;
	}
	return (g);
}
