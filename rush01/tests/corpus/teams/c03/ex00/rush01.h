#ifndef RUSH01_H
# define RUSH01_H

# include <stdlib.h>
# include <unistd.h>

char	**ft_split(char *str, char sep);
void	ft_free_tab(char **tab);
int		ft_parse_clues(char *str, int *clue);
int		ft_strlen(char *s);
int		**ft_new_grid(void);
void	ft_free_grid(int **g);
int		ft_bt(int **g, int *clue, int row, int col);
int		ft_cols_ok(int **g, int *clue);
int		ft_row_end_ok(int **g, int *clue, int row, int col);
void	ft_show(int **g);

#endif
