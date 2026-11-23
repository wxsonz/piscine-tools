#include "rush01.h"

static int	ft_atoi_tok(char *s, int *i)
{
	int	res;

	res = 0;
	if (s[*i] < '1' || s[*i] > '9')
		return (-1);
	while (s[*i] >= '0' && s[*i] <= '9' && res <= 9)
	{
		res = res * 10 + (s[*i] - '0');
		(*i)++;
	}
	if (res > 9)
		return (-1);
	return (res);
}

static int	ft_sep(char *s, int *i)
{
	if (s[*i] == ' ')
	{
		(*i)++;
		return (s[*i] != '\0');
	}
	return (s[*i] == '\0');
}

int	ft_args(char *s, int *clue)
{
	int	i;
	int	count;
	int	max;

	i = 0;
	count = 0;
	max = 0;
	while (count < 36 && s[i] != '\0')
	{
		clue[count] = ft_atoi_tok(s, &i);
		if (clue[count] < 0 || !ft_sep(s, &i))
			return (0);
		if (clue[count] > max)
			max = clue[count];
		count++;
	}
	if (s[i] != '\0' || count % 4 != 0 || max > count / 4)
		return (0);
	return (count / 4);
}
