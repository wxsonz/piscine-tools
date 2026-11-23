#ifndef SKYLINE_H
# define SKYLINE_H

# include <unistd.h>

int		ft_get_clues(char *str, int *clue);
void	ft_init_cand(int cand[4][4][4]);
void	ft_copy_cand(int dst[4][4][4], int src[4][4][4]);
void	ft_remove(int cand[4][4][4], int r, int c, int v);
int		ft_check(int grid[4][4], int *clue);
int		ft_cands(int grid[4][4], int cand[4][4][4], int *clue, int pos);
void	ft_print_all(int grid[4][4]);

#endif
