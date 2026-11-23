#ifndef RUSH_H
# define RUSH_H

# include <unistd.h>

int		ft_parse(char *s, int *clue);
int		ft_strcmp(char *a, char *b);
int		ft_solve(char *arg, int grid[4][4]);
void	ft_putchar(char c);
void	ft_print(int grid[4][4]);

#endif
