#ifndef SKY_H
# define SKY_H

# include <unistd.h>

void	ft_putchar(char c);
void	ft_putnbr(int n);
int		ft_scan(char *str, int *clue);
int		ft_look(int *grid, int start, int step);
int		ft_valid(int *grid, int *clue);
int		ft_fill(int *grid, int *clue, int pos);
void	ft_show(int *grid);

#endif
