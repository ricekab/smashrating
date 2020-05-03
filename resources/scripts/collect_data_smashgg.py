""" Module documentation """
import logging
from datetime import datetime, timezone

from smashrating.collect.smashgg import SmashGGScraper
from smashrating.db import get_session
from smashrating.model import Tournament

root_logger = logging.getLogger("smashrating")
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logging.StreamHandler())  # cout

db_kwargs = dict(db_user='vagrant',
                 db_pass='vagrant',
                 db_url='localhost:5432',
                 db_schema='vagrant')


session = get_session(**db_kwargs)

scraper = SmashGGScraper(session=session,
                         api_key="bd6ff6319866fd79fe85cbfec74f6f7c")

# ----- RETRIEVE TOURNAMENTS -----

# See: https://ec.europa.eu/eurostat/statistics-explained/index.php/Glossary:Country_codes
EURO_CODES = dict(BE="Belgium", EL="Greece", LT="Lithuania", PT="Portugal",
                  BG="Bulgaria", ES="Spain", LU="Luxembourg", RO="Romania",
                  CZ="Czechia", FR="France", HU="Hungary", SI="Slovenia",
                  DK="Denmark", HR="Croatia", MT="Malta", SK="Slovakia",
                  DE="Germany", IT="Italy", NL="Netherlands", FI="Finland",
                  EE="Estonia", CY="Cyprus", AT="Austria", SE="Sweden",
                  IE="Ireland", LV="Latvia", PL="Poland",
                  IS="Iceland", NO="Norway",
                  LI="Liechtenstein", CH="Switzerland", ME="Montenegro",
                  MK="North Macedonia", AL="Albania", RS="Serbia",
                  TR="Turkey", XK="Kosovo", BA="Bosnia Herzegovina",
                  AM="Armenia", BY="Belarus", GE="Georgia",
                  AZ="Azerbaijan", MD="Moldova", UA="Ukraine",
                  RU="Russia", UK="United Kingdom",
                  )

start_date = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
start_timestamp = int(start_date.timestamp())  # sgg can't take float
for cc in EURO_CODES.keys():
    result = scraper.get_tournaments_by_country(cc,
                                                after_date=start_timestamp)
    print(f'Collected {len(result)} tournaments from {EURO_CODES[cc]} ({cc}).')

YEAR = 2020
for month in range(1, 13):
    start_date = datetime(year=YEAR, month=month, day=1, tzinfo=timezone.utc)
    end_date = start_date.replace(month=month + 1) if month < 12 \
        else start_date.replace(year=YEAR + 1, month=1)
    result = scraper.get_all_tournaments(after_date=int(start_date.timestamp()),
                                         before_date=int(end_date.timestamp()))
    print(f'Processed {len(result)} tournaments from {start_date} to '
          f'{end_date}.')

# ----- MARK TOURNAMENT / EVENTS -----

all_t = session.query(Tournament) \
    .filter(Tournament.name.notilike('%-%squad%') &
            Tournament.name.notilike('%-%ladder%') &
            Tournament.name.notilike('%-%speedrun%')) \
    .all()
print(f"Marking {len(all_t)} tournaments as valid based on name match.")
for t in all_t:
    t.is_valid = True
session.commit()

# ----- RETRIEVE SETS -----

scraper.populate_empty_tournaments()

# # Only do a subset for quick testing:
# scraper.populate_tournament(
#     session.query(Tournament)
#         .filter(Tournament.name.contains('Antwerp 3'))
#         .one())
