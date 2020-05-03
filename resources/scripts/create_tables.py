import logging

from smashrating.db import get_engine
from smashrating.model import Base

root_logger = logging.getLogger("smashrating")
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(logging.StreamHandler())  # cout


engine = get_engine(db_user='vagrant',
                    db_pass='vagrant',
                    db_url='localhost:5432',
                    db_schema='vagrant')

# Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
