def merge_players(session, canonical_player, duplicate_players,
                  auto_commit=False):
    """
    Merges any references to duplicate players to the canonical player.

    The duplicate players are removed from the session at the end of this
    operation but does NOT commit the session unless auto_commit is True.

    :param session:
    :type session: sqlalchemy.orm.Session

    :param canonical_player:
    :type canonical_player: smashrating.model.Player

    :param duplicate_players:
    :type duplicate_players: list[smashrating.model.Player]

    :param auto_commit: Whether to commit at the end of the operation.
        Default: False.
    :type auto_commit: bool

    :return:
    """
    if canonical_player in duplicate_players:
        duplicate_players.remove(canonical_player)
    for duplicate in duplicate_players:
        _transfer_relations(canonical_player, duplicate)
        session.delete(duplicate)
    if auto_commit:
        session.commit()


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
