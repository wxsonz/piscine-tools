/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   rush01.h                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: cmartin <cmartin@student.42.fr>            +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/11/20 10:00:00 by cmartin           #+#    #+#             */
/*   Updated: 2026/11/20 10:00:00 by cmartin          ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef RUSH01_H
# define RUSH01_H

# include <unistd.h>
# include <stdlib.h>

typedef struct s_game
{
	int	clue[4][4];
	int	grid[16];
}	t_game;

int		ft_parse(char *s, t_game *g);
int		ft_look(t_game *g, int start, int step);
int		ft_lines(t_game *g, int pos);
int		ft_solve(t_game *g, int pos);
void	ft_clear(t_game *g);
void	ft_print(t_game *g);
int		ft_error(void);

#endif
