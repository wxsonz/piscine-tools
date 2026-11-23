#include "skyscraper.h"

int	ft_parser(char *s, int *clues)
{
	int	i;
	int	n;

	i = 0;
	n = 0;
	while (s[i])
	{
		if (s[i] >= '1' && s[i] <= '4' && (i == 0 || s[i - 1] == ' '))
		{
			if (n == 16)
				return (0);
			clues[n] = s[i] - '0';
			n++;
		}
		else if (s[i] != ' ' || i == 0 || s[i - 1] == ' ' || !s[i + 1])
			return (0);
		i++;
	}
	return (n == 16);
}
