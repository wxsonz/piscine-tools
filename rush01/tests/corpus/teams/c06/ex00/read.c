#include "board.h"

void	ft_clear(int b[6][6])
{
	int	i;

	i = 0;
	while (i < 36)
	{
		b[i / 6][i % 6] = 0;
		i++;
	}
}

static void	ft_put_clue(int b[6][6], int i, int v)
{
	if (i < 4)
		b[0][i + 1] = v;
	else if (i < 8)
		b[5][i - 3] = v;
	else if (i < 12)
		b[i - 7][0] = v;
	else
		b[i - 11][5] = v;
}

int	ft_load(char *s, int b[6][6])
{
	int	i;

	i = 0;
	while (i < 31)
	{
		if (s[i] == '\0')
			return (0);
		if (i % 2 == 0 && (s[i] < '1' || s[i] > '4'))
			return (0);
		if (i % 2 == 1 && s[i] != ' ')
			return (0);
		if (i % 2 == 0)
			ft_put_clue(b, i / 2, s[i] - '0');
		i++;
	}
	return (s[31] == '\0');
}
