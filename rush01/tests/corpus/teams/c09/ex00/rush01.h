#ifndef RUSH01_H
# define RUSH01_H

# include <unistd.h>

void	ft_get_clues(char *s, int *clue);
char	*ft_perm(int i);
void	ft_load(int grid[4][4], int *pick);
int		ft_all_ok(int grid[4][4], int *clue);
int		ft_brute(int grid[4][4], int *clue);
void	ft_putchar(char c);
void	ft_put_grid(int grid[4][4]);

#endif
