#ifndef RUSH_H
# define RUSH_H

# include <unistd.h>

int		ft_parse(char *str, int *clue);
int		ft_solve(int grid[4][4], int *clue, int pos);
int		ft_is_valid(int grid[4][4], int pos, int v);
int		ft_check_clues(int grid[4][4], int *clue);
void	ft_putchar(char c);
void	ft_print_grid(int grid[4][4]);
void	ft_error(void);

#endif
