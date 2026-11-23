#include "board.h"

static int	ft_token(char *s, int *i, int *val)
{
	*val = 0;
	if (s[*i] < '1' || s[*i] > '9')
		return (0);
	while (s[*i] >= '0' && s[*i] <= '9' && *val <= 4)
	{
		*val = *val * 10 + (s[*i] - '0');
		(*i)++;
	}
	return (*val >= 1 && *val <= 4);
}

int	ft_parse(char *s, t_board *b)
{
	int	i;
	int	k;
	int	val;

	i = 0;
	k = 0;
	while (k < 16)
	{
		if (!ft_token(s, &i, &val))
			return (0);
		b->clue[k] = val;
		k++;
		if (k < 16)
		{
			if (s[i] != ' ')
				return (0);
			i++;
		}
	}
	return (s[i] == '\0');
}
