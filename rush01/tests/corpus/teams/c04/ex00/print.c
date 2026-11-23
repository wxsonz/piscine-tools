#include "board.h"

void	ft_putstr(char *s)
{
	int	len;

	len = 0;
	while (s[len])
		len++;
	write(1, s, len);
}

static char	*ft_row_str(t_board *b, int r)
{
	char	*s;
	int		i;

	s = malloc(9);
	if (s == NULL)
		return (NULL);
	i = 0;
	while (i < 4)
	{
		s[i * 2] = b->grid[r][i] + '0';
		s[i * 2 + 1] = ' ';
		i++;
	}
	s[7] = '\n';
	s[8] = '\0';
	return (s);
}

void	ft_print_board(t_board *b)
{
	char	*s;
	int		r;

	r = 0;
	while (r < 4)
	{
		s = ft_row_str(b, r);
		if (s == NULL)
			return ;
		ft_putstr(s);
		free(s);
		r++;
	}
}
