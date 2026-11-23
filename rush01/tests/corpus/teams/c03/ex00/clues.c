#include "rush01.h"

int	ft_strlen(char *s)
{
	int	i;

	i = 0;
	while (s[i])
		i++;
	return (i);
}

int	ft_parse_clues(char *str, int *clue)
{
	char	**words;
	int		i;

	if (ft_strlen(str) != 31)
		return (0);
	words = ft_split(str, ' ');
	if (words == NULL)
		return (0);
	i = 0;
	while (words[i])
	{
		if (i >= 16 || ft_strlen(words[i]) != 1
			|| words[i][0] < '1' || words[i][0] > '4')
		{
			ft_free_tab(words);
			return (0);
		}
		clue[i] = words[i][0] - '0';
		i++;
	}
	ft_free_tab(words);
	return (i == 16);
}
