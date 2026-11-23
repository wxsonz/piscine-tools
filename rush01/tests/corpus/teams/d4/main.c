/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: ydubois <ydubois@student.42.fr>            +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/11/20 10:00:00 by ydubois           #+#    #+#             */
/*   Updated: 2026/11/20 10:00:00 by ydubois          ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "rush01.h"

int	ft_error(void)
{
	write(1, "Error\n", 6);
	return (1);
}

void	ft_clear(t_game *g)
{
	int	i;

	i = 0;
	while (i < 16)
	{
		g->grid[i] = 0;
		i++;
	}
}

int	main(int argc, char **argv)
{
	t_game	g;

	if (argc != 2 || !ft_parse(argv[1], &g))
		return (ft_error());
	ft_clear(&g);
	if (!ft_solve(&g, 0))
		return (ft_error());
	ft_print(&g);
	return (0);
}
