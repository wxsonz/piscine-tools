#ifndef SKYSCRAPER_H
# define SKYSCRAPER_H

# include <unistd.h>

int		ft_read_input(char *s, int views[4][4]);
int		ft_can_put(int grid[4][4], int row, int col, int v);
int		ft_lines_ok(int grid[4][4], int views[4][4], int row, int col);
int		ft_place(int grid[4][4], int views[4][4], int row, int col);
void	ft_print_rows(int grid[4][4]);

#endif
