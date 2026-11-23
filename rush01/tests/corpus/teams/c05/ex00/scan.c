#include "sky.h"

int	ft_scan(char *str, int *clue)
{
	int	n;

	n = 0;
	while (*str)
	{
		if (*str < '1' || *str > '4' || n == 16)
			return (0);
		clue[n] = *str - '0';
		n++;
		str++;
		if (*str == ' ')
		{
			str++;
			if (*str == '\0')
				return (0);
		}
		else if (*str != '\0')
			return (0);
	}
	return (n == 16);
}
