""" Module documentation """
from __future__ import absolute_import, print_function

import itertools
import logging
from pprint import pprint as pp

from sqlalchemy.orm import subqueryload

from smashrating import glicko
from smashrating.db import get_session
from smashrating.model import Tournament, Set

root_logger = logging.getLogger("smashrating")
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logging.StreamHandler())  # cout

db_kwargs = dict(db_user='vagrant',
                 db_pass='vagrant',
                 db_url='localhost:5432',
                 db_schema='vagrant')

session = get_session(**db_kwargs)

CACHE_FILE = 'cache_glicko.json'

# # -- Glicko test --
example_sets = [(1, 2),  # (Winner ID, Loser ID)
                (1, 3),
                (1, 4),
                (2, 3),
                (4, 2),
                (4, 3),
                (1, 5),
                (5, 4),
                (4, 1),
                (4, 5),
                (1, 3),
                (2, 4),
                (1, 2),
                (1, 4),
                (1, 5),
                ]
# ratings = dict()
ratings = {
    1: glicko.Rating(1600, 50),
    2: glicko.Rating(1400, 30),
    3: glicko.Rating(1550, 100),
    4: glicko.Rating(1700, 300),
}
rankings = glicko.update_ranking(sets=example_sets, player_ratings=ratings)
print('Glicko test data ratings.')
pp(rankings)

# -- Glicko calculation
all_tournaments = session.query(Tournament) \
    .filter_by(country='BE') \
    .options(subqueryload('sets')) \
    .all()

period_start = None
period_end = None

# TODO: Filter to include only tournaments for the ranking period.

# Note: ordering of sets doesn't matter for glicko
all_sets = list(itertools.chain(t.sets for t in all_tournaments))
print(f'Num of total sets: {len(all_sets)}')
filtered_sets = list(s for s in all_sets
                     if s.state == Set.VERIFIED)
print(f'Num of included sets: {len(filtered_sets)}')

rankings = dict()

# TODO: Continue here
# -> Convert sets into simple (winner_id, loser_id)
# -> Run over intervals (cache at each interval?)
# -> initial values for country (or all?), startdate, etc...
