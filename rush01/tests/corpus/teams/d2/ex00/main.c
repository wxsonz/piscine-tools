/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tbernard <tbernard@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/11/20 10:00:00 by tbernard          #+#    #+#             */
/*   Updated: 2026/11/20 10:00:00 by tbernard         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "rush01.h"

int	ft_error(void)
{
	write(1, "Error\n", 6);
	return (1);
}

int	main(int argc, char **argv)
{
	t_game	g = {0};

	if (argc != 2 || !ft_parse(argv[1], &g))
		return (ft_error());
	if (!ft_solve(&g, 0))
		return (ft_error());
	ft_print(&g);
	return (0);
}
