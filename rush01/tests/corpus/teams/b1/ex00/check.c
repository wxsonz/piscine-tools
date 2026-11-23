/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   check.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: sgarcia <sgarcia@student.42.fr>            +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/11/20 10:00:00 by sgarcia           #+#    #+#             */
/*   Updated: 2026/11/20 10:00:00 by sgarcia          ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "rush01.h"

int	ft_look(t_game *g, int start, int step)
{
	int	i;
	int	max;
	int	count;

	i = 0;
	max = 0;
	count = 0;
	while (i < 4)
	{
		if (g->grid[start + i * step] > max)
		{
			max = g->grid[start + i * step];
			count++;
		}
		i++;
	}
	return (count);
}

static int	ft_row_ok(t_game *g, int r)
{
	if (ft_look(g, r * 4, 1) != g->clue[2][r])
		return (0);
	if (ft_look(g, r * 4 + 3, -1) != g->clue[3][r])
		return (0);
	return (1);
}

static int	ft_col_ok(t_game *g, int c)
{
	if (ft_look(g, c, 4) != g->clue[0][c])
		return (0);
	if (ft_look(g, 12 + c, -4) != g->clue[1][c])
		return (0);
	return (1);
}

int	ft_lines(t_game *g, int pos)
{
	if (pos % 4 == 3 && !ft_row_ok(g, pos / 4))
		return (0);
	if (pos / 4 == 3 && !ft_col_ok(g, pos % 4))
		return (0);
	return (1);
}
