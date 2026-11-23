/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   solve.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: sgarcia <sgarcia@student.42.fr>            +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/11/20 10:00:00 by sgarcia           #+#    #+#             */
/*   Updated: 2026/11/20 10:00:00 by sgarcia          ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "rush01.h"

static int	ft_free(t_game *g, int pos, int v)
{
	int	i;

	i = 0;
	while (i < 4)
	{
		if (g->grid[pos / 4 * 4 + i] == v)
			return (0);
		if (g->grid[i * 4 + pos % 4] == v)
			return (0);
		i++;
	}
	return (1);
}

int	ft_solve(t_game *g, int pos)
{
	int	v;

	if (pos == 16)
		return (1);
	v = 1;
	while (v <= 4)
	{
		if (ft_free(g, pos, v))
		{
			g->grid[pos] = v;
			if (ft_lines(g, pos) && ft_solve(g, pos + 1))
				return (1);
			g->grid[pos] = 0;
		}
		v++;
	}
	return (0);
}
