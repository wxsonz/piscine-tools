#ifndef RUSH_H
# define RUSH_H

# include <unistd.h>

int		parse_clues(char *str, int *clues, int *n);
int		solve(int grid[9][9], int *clues, int n, int pos);
int		row_ok(int grid[9][9], int *clues, int n, int row);
int		col_ok(int grid[9][9], int *clues, int n, int col);
void	print_grid(int grid[9][9], int n);

#endif
