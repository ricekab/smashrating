def update_ranking(w_rank, l_rank, w_k, l_k):
    """
    Calculates the update ranking for 2 players.
    
    :param w_rank: The winning player's previous ranking.
    :type w_rank: float

    :param l_rank: The losing player's previous ranking.
    :type l_rank: float

    :param w_k: The winning player's K value.
    :type w_k: int or float

    :param l_k: The losing player's K value.
    :type l_k: int or float

    :return: The new rank of the winner and loser (in that order).
    :rtype: tuple[float, float]
    """
    q1 = 10 ** (w_rank / 400)
    q2 = 10 ** (l_rank / 400)
    e1 = q1 / (q1 + q2)
    e2 = q2 / (q1 + q2)
    new_r1 = w_rank + w_k * (1 - e1)  # 1 = win
    new_r2 = l_rank + l_k * (0 - e2)  # 0 = loss
    return new_r1, new_r2
