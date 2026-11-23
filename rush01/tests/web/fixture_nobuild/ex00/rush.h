#ifndef RUSH_H
# define RUSH_H

# include <stdio.h>
# include <stdlib.h>

typedef struct s_board
{
	int	n;
	int	cell[4][4];
	int	clue[16];
}	t_board;

int		read_clues(t_board *b, char *str);
int		prefill(t_board *b);
int		search(t_board *b, int pos);
void	show(t_board *b);

#endif
