""" Module documentation """
from __future__ import absolute_import, print_function

import functools
import json
import logging
from collections import defaultdict

from sqlalchemy.orm import subqueryload

from smashrating import elo
from smashrating.db import get_session
from smashrating.model import Player, Set

root_logger = logging.getLogger("smashrating")
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logging.StreamHandler())  # cout

db_kwargs = dict(db_user='vagrant',
                 db_pass='vagrant',
                 db_url='localhost:5432',
                 db_schema='vagrant')

session = get_session(**db_kwargs)

CACHE_FILE = 'cache_elo.json'


def set_sort_key(set_):
    """

    :param set_:
    :type set_: Set
    :return:
    """
    return set_.tournament.end_date, set_.order


all_sets = session.query(Set) \
    .options(subqueryload('winning_player')) \
    .options(subqueryload('losing_player')) \
    .all()
print(f'Num of total sets: {len(all_sets)}')
filtered_sets = (s for s in all_sets
                 if s.state == Set.VERIFIED or s.state == Set.UNVERIFIED)
# filtered_sets = (s for s in all_sets if s)
sorted_sets = list(sorted(filtered_sets, key=set_sort_key))
print(f'Num of included sets: {len(sorted_sets)}')
initial_rank = 1200
# k_val = 32  # Chess "standard"
k_val = 35
rankings = defaultdict(functools.partial(int, initial_rank))

print("Processing rankings...")
for s in sorted_sets:  # type: Set
    wr_before = rankings[s.winning_player]
    lr_before = rankings[s.losing_player]
    wr_after, lr_after = elo.update_ranking(wr_before, lr_before,
                                            w_k=k_val, l_k=k_val)
    rankings[s.winning_player] = wr_after
    rankings[s.losing_player] = lr_after
print("Rankings complete!")

all_players = session.query(Player) \
    .options(subqueryload('won_sets')) \
    .options(subqueryload('lost_sets')) \
    .all()
print(f'Total number of players: {len(all_players)}')
filtered_players = [p for p in all_players
                    if len(p.won_sets) + len(p.lost_sets) >= 10]
print(f'Number of ranked players: {len(filtered_players)}')

# Write out results to file
with open(CACHE_FILE, 'wt') as of:
    out_dict = {p.id: dict(name=p.name, score=score, country=p.country)
                for p, score in rankings.items()
                if p in filtered_players}
    json.dump(out_dict, of)

player_ranks = [(score, p) for p, score in rankings.items()
                if p in filtered_players]
rank_pos = 1
limit = 100
for player_tuple in sorted(player_ranks,
                           key=lambda pt: pt[0],
                           reverse=True):
    _score, p = player_tuple
    print(f"[{rank_pos:3d}] {p.name:25s} : {_score:.02f}")
    rank_pos += 1
    if rank_pos > limit:
        break

# ----- READ FROM cache.json -----

with open(CACHE_FILE, 'rt') as rf:
    data = json.load(rf)
    player_data = data.values()

rank_pos = 0
print_count = 0
limit = 100  # Set to none or zero to get all of it
# p_filter = lambda _pd: _pd["country"] == "Belgium"
p_filter = None
for pdata in sorted(player_data,
                    key=lambda _pd: _pd['score'],
                    reverse=True):
    rank_pos += 1
    if p_filter and not p_filter(pdata):
        continue
    print(f"[{rank_pos:4d}] "
          f"({pdata['country'] if pdata['country'] else '???':.3s}) "
          f"{pdata['name']:25s} : "
          f"{pdata['score']:.02f}")
    print_count += 1
    if limit and print_count == limit:
        break
