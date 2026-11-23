#ifndef BOARD_H
# define BOARD_H

# include <stdlib.h>
# include <unistd.h>

typedef struct s_board
{
	int	grid[4][4];
	int	clue[16];
}		t_board;

int		ft_parse(char *s, t_board *b);
int		ft_prefill(t_board *b);
int		ft_search(t_board *b, int pos);
int		ft_verify(t_board *b);
void	ft_putstr(char *s);
void	ft_print_board(t_board *b);

#endif
