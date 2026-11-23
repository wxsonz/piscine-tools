#ifndef RUSH01_H
# define RUSH01_H

# include <unistd.h>

extern const int	g_perm[24][4];

int		ft_parse(char *s, int *clue);
int		ft_vis(int *v, int rev);
int		ft_rows(int grid[4][4], int *clue, int r);
void	ft_putchar(char c);
void	ft_display(int grid[4][4]);

#endif
