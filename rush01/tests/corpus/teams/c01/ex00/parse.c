#include "rush.h"

static int	ft_strlen(char *s)
{
	int	i;

	i = 0;
	while (s[i])
		i++;
	return (i);
}

int	ft_parse(char *str, int *clue)
{
	int	i;

	if (ft_strlen(str) != 31)
		return (0);
	i = 0;
	while (i < 31)
	{
		if (i % 2 == 0)
		{
			if (str[i] < '1' || str[i] > '4')
				return (0);
			clue[i / 2] = str[i] - '0';
		}
		else if (str[i] != ' ')
			return (0);
		i++;
	}
	return (1);
}
