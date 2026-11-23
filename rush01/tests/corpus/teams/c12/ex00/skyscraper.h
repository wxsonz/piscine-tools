#ifndef SKYSCRAPER_H
# define SKYSCRAPER_H

# include <unistd.h>

int		ft_parser(char *s, int *clues);
int		ft_row_col_ok(int *grid, int pos, int v);
int		ft_clues_ok(int *grid, int *clues);
int		ft_backtrack(int *grid, int *clues, int pos);
void	ft_putchar(char c);
void	ft_print_grid(int *grid);
void	ft_error(void);

#endif
