def merge_players(canonical_player, duplicate_players):
    """
    Merges any references to duplicate players to the canonical player.

    This does NOT remove the duplicate player entries nor does it explicitly
    modify the session.

    :param canonical_player:
    :type canonical_player: smashrating.model.Player

    :param duplicate_players:
    :type duplicate_players: list[smashrating.model.Player]

    :return:
    """
    if canonical_player in duplicate_players:
        duplicate_players.remove(canonical_player)
    for duplicate in duplicate_players:
        _transfer_relations(canonical_player, duplicate)


def _transfer_relations(target, source):
    """

    :param target: The target player to move all references to.
    :type target: smashrating.model.Player

    :param source: The source player to move all references from.
    :type source: smashrating.model.Player
    """
    for ws in source.won_sets:
        ws.winning_player = target
    for ls in source.lost_sets:
        ls.losing_player = target
