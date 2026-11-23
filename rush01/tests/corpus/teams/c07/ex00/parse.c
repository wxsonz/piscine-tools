#include "rush01.h"

int	ft_parse(char *s, int *clue)
{
	int	i;
	int	n;

	i = 0;
	n = 0;
	while (s[i])
	{
		if (s[i] >= '1' && s[i] <= '4' && n < 16)
		{
			clue[n] = s[i] - '0';
			n++;
			if (s[i + 1] != ' ' && s[i + 1] != '\0')
				return (0);
		}
		else if (s[i] == ' ')
		{
			if (i == 0 || s[i + 1] == '\0' || s[i + 1] == ' ')
				return (0);
		}
		else
			return (0);
		i++;
	}
	return (n == 16);
}
