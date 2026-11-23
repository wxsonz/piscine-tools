#include "skyscraper.h"

int	ft_read_input(char *s, int views[4][4])
{
	int	i;
	int	count;

	i = 0;
	count = 0;
	while (s[i])
	{
		if (s[i] >= '1' && s[i] <= '4' && (i == 0 || s[i - 1] == ' '))
		{
			if (count == 16)
				return (0);
			views[count / 4][count % 4] = s[i] - '0';
			count++;
		}
		else if (!(s[i] == ' ' && i > 0 && s[i - 1] != ' ' && s[i + 1]))
			return (0);
		i++;
	}
	return (count == 16);
}
