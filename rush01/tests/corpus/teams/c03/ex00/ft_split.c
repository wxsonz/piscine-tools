#include "rush01.h"

static int	count_words(char *s, char sep)
{
	int	n;
	int	i;

	n = 0;
	i = 0;
	while (s[i])
	{
		while (s[i] == sep)
			i++;
		if (s[i])
			n++;
		while (s[i] && s[i] != sep)
			i++;
	}
	return (n);
}

static char	*dup_word(char *s, int len)
{
	char	*w;
	int		i;

	w = malloc(len + 1);
	if (w == NULL)
		return (NULL);
	i = 0;
	while (i < len)
	{
		w[i] = s[i];
		i++;
	}
	w[i] = '\0';
	return (w);
}

void	ft_free_tab(char **tab)
{
	int	i;

	i = 0;
	while (tab[i])
	{
		free(tab[i]);
		i++;
	}
	free(tab);
}

static int	fill_tab(char **tab, char *s, char sep)
{
	int	n;
	int	len;

	n = 0;
	while (*s)
	{
		while (*s == sep)
			s++;
		len = 0;
		while (s[len] && s[len] != sep)
			len++;
		if (len > 0)
		{
			tab[n] = dup_word(s, len);
			if (tab[n++] == NULL)
				return (0);
		}
		s += len;
	}
	tab[n] = NULL;
	return (1);
}

char	**ft_split(char *str, char sep)
{
	char	**tab;
	int		i;

	tab = malloc(sizeof(char *) * (count_words(str, sep) + 1));
	if (tab == NULL)
		return (NULL);
	i = 0;
	while (i <= count_words(str, sep))
	{
		tab[i] = NULL;
		i++;
	}
	if (!fill_tab(tab, str, sep))
	{
		ft_free_tab(tab);
		return (NULL);
	}
	return (tab);
}
