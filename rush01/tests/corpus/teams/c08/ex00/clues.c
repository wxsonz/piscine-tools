#include "skyline.h"

int	ft_get_clues(char *str, int *clue)
{
	int	i;
	int	n;

	i = 0;
	n = 0;
	while (str[i] != '\0')
	{
		if (str[i] >= '1' && str[i] <= '4' && n < 16)
		{
			clue[n] = str[i] - '0';
			n++;
			if (str[i + 1] != ' ' && str[i + 1] != '\0')
				return (0);
		}
		else if (str[i] == ' ')
		{
			if (i == 0 || str[i + 1] == '\0' || str[i + 1] == ' ')
				return (0);
		}
		else
			return (0);
		i++;
	}
	return (n == 16);
}
