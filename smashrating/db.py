import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_logger = logging.getLogger(__name__)


def get_engine(db_user=None, db_pass=None, db_url=None, db_schema=None,
               db_connector="postgresql"):
    db_kwargs = {
        "db_user": db_user or os.environ.get("SMASHRATING_DB_USER"),
        "db_pass": db_pass or os.environ.get("SMASHRATING_DB_PASS"),
        "db_url": db_url or os.environ.get("SMASHRATING_DB_URL"),
        "db_schema": db_schema or os.environ.get("SMASHRATING_DB_SCHEMA"),
        "db_connector": os.environ.get("SMASHRATING_DB_CONNECTOR", db_connector)
    }
    conn_str = "{db_connector}://{db_user}:{db_pass}@{db_url}/{db_schema}" \
        .format(**db_kwargs)
    _logger.debug(f"Creating engine with: '{conn_str}'")
    return create_engine(conn_str)


def get_session(**engine_kwargs):
    """

    :param engine_kwargs:

    :return:
    :rtype: sqlalchemy.orm.Session
    """
    engine = get_engine(**engine_kwargs)
    _session_factory = sessionmaker(bind=engine)
    return _session_factory()
