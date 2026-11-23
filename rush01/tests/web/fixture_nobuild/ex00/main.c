#include "rush.h"

int	read_clues(t_board *b, char *str)
{
	int	i;
	int	k;

	i = 0;
	k = 0;
	while (str[i] && k < 16)
	{
		b->clue[k] = atoi(str + i);
		if (b->clue[k] < 1 || b->clue[k] > 4)
			return (0);
		while (str[i] && str[i] != ' ')
			i++;
		while (str[i] == ' ')
			i++;
		k++;
	}
	return (k == 16)
}

int	prefill(t_board *b)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (b->clue[i] == 4)
			b->cell[0][i] = 1;
		if (b->clue[i] == 1)
			b->cell[0][i] = 4;
		i++;
	}
	return (1);
}

int	search(t_board *b, int pos)
{
	int	v;

	if (pos == 16)
		return (1);
	if (b->cell[pos / 4][pos % 4])
		return (search(b, pos + 1));
	v = 0;
	while (++v <= 4)
	{
		b->cell[pos / 4][pos % 4] = v;
		if (search(b, pos + 1))
			return (1);
	}
	b->cell[pos / 4][pos % 4] = 0;
	return (0);
}

void	show(t_board *b)
{
	int	r;

	r = 0;
	while (r < 4)
	{
		printf("%d %d %d %d\n", b->cell[r][0], b->cell[r][1],
			b->cell[r][2], b->cell[r][3]);
		r++;
	}
}

int	main(int argc, char **argv)
{
	t_board	b;

	if (argc != 2 || !read_clues(&b, argv[1]) || !prefill(&b)
		|| !search(&b, 0))
	{
		printf("Error\n");
		return (1);
	}
	show(&b);
	return (0);
}
