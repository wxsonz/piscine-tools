#include "rush.h"

int	ft_parse(char *s, int *clue)
{
	int	i;

	i = 0;
	while (i < 31)
	{
		if (s[i] == '\0')
			return (0);
		if (i % 2 == 0)
		{
			if (s[i] < '1' || s[i] > '4')
				return (0);
			clue[i / 2] = s[i] - '0';
		}
		else if (s[i] != ' ')
			return (0);
		i++;
	}
	return (s[31] == '\0');
}

int	ft_strcmp(char *a, char *b)
{
	int	i;

	i = 0;
	while (a[i] && a[i] == b[i])
		i++;
	return (a[i] - b[i]);
}
