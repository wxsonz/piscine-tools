#ifndef RUSH01_H
# define RUSH01_H

# include <stdlib.h>
# include <unistd.h>

int		ft_args(char *s, int *clue);
int		**ft_new_matrix(int n);
void	ft_free_matrix(int **m, int n);
int		ft_can_put(int **m, int n, int pos, int v);
int		ft_line_ok(int **m, int *clue, int n, int pos);
int		ft_place(int **m, int *clue, int n, int pos);
void	ft_show(int **m, int n);

#endif
