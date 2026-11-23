#include "skyline.h"

void	ft_init_cand(int cand[4][4][4])
{
	int	i;

	i = 0;
	while (i < 64)
	{
		cand[i / 16][(i / 4) % 4][i % 4] = 1;
		i++;
	}
}

void	ft_copy_cand(int dst[4][4][4], int src[4][4][4])
{
	int	i;

	i = 0;
	while (i < 64)
	{
		dst[i / 16][(i / 4) % 4][i % 4] = src[i / 16][(i / 4) % 4][i % 4];
		i++;
	}
}

void	ft_remove(int cand[4][4][4], int r, int c, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		cand[r][i][v] = 0;
		cand[i][c][v] = 0;
		i++;
	}
}
