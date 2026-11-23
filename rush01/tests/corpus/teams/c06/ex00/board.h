#ifndef BOARD_H
# define BOARD_H

# include <unistd.h>

void	ft_clear(int b[6][6]);
int		ft_load(char *s, int b[6][6]);
int		ft_free_to_put(int b[6][6], int r, int c, int v);
int		ft_clues_ok(int b[6][6]);
int		ft_walk(int b[6][6]);
void	ft_out(int b[6][6]);

#endif
