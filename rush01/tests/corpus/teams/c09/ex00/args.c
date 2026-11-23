#include "rush01.h"

void	ft_get_clues(char *s, int *clue)
{
	int	i;
	int	n;

	i = 0;
	n = 0;
	while (s[i] && n < 16)
	{
		if (s[i] != ' ')
		{
			clue[n] = s[i] - '0';
			n++;
		}
		i++;
	}
	while (n < 16)
	{
		clue[n] = 0;
		n++;
	}
}
