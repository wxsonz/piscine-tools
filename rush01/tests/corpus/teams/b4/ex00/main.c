/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: jlambert <jlambert@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/11/20 10:00:00 by jlambert          #+#    #+#             */
/*   Updated: 2026/11/20 10:00:00 by jlambert         ###   ########.fr       */
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

static char	*ft_strdup(char *src)
{
	int		n;
	char	*dst;

	n = 0;
	while (src[n])
		n++;
	dst = malloc(n + 1);
	if (dst == NULL)
		return (NULL);
	n = 0;
	while (src[n])
	{
		dst[n] = src[n];
		n++;
	}
	dst[n] = '\0';
	return (dst);
}

int	main(int argc, char **argv)
{
	t_game	g;
	char	*s;

	s = NULL;
	if (argc == 2)
		s = ft_strdup(argv[1]);
	if (s == NULL || !ft_parse(s, &g))
	{
		free(s);
		return (ft_error());
	}
	free(s);
	ft_clear(&g);
	if (!ft_solve(&g, 0))
		return (ft_error());
	ft_print(&g);
	return (0);
}
