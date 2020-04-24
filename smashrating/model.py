from collections import OrderedDict

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, \
    DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import ColumnProperty, relationship


class _Base(object):
    """
    Implements common functionality for all model classes.

    1) __repr__ is implemented generically using __mapper__ column lookup.
       Note that this is intended to assist with debugging and may cause
       database calls as a result!

    2) The table name is generated based on the class name and follows the
       standard SQL naming convention. More specifically, an '_' character is
       inserted before every capital letter (except for the first) and it is
       then converted to lowercase.

       Class names are expected to follow the Python class naming convention
       (PascalCase), otherwise this may misbehave.

       Examples:
           - Car -> car
           - CarEngine -> car_engine
           - Bad_Python_Convention -> bad__python__convention  # Incorrect
           - _ImplementationClass -> __implementation_class    # Also incorrect

    See:
        http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/mixins.html#augmenting-the-base
    """
    __column_keys_cache__ = dict()
    """ Cache for the column attribute keys by class. Used by __repr__ """

    @declared_attr
    def __tablename__(cls):
        """ Table name generation. """
        cls_name = cls.__name__
        table_name = cls_name[0]
        for c in cls_name[1:]:
            if c.isupper():
                table_name += '_'
            table_name += c
        return table_name.lower()

    def __repr__(self):
        """
        Representative string generated from column definitions (and values).

        Only column properties (not relations) are included in the string.

        Column names are cached after the first call.

        Note that this may cause additional calls to the database and should
        only be used for debugging!
        """
        if self.__class__ not in self.__column_keys_cache__:
            keys = [_prop.key
                    for _prop in self.__mapper__.iterate_properties
                    if isinstance(_prop, ColumnProperty)]
            self.__column_keys_cache__[self.__class__] = keys
        keys = sorted(self.__column_keys_cache__[self.__class__])
        values = [getattr(self, k) for k in keys]
        prop_values = OrderedDict(zip(keys, values))
        prop_strings = [f"{k}='{v}'" for k, v in prop_values.items()]
        props = ", ".join(prop_strings)
        return f"<{self.__class__.__name__}({props})>"


Base = declarative_base(cls=_Base)


class Tournament(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    sgg_id = Column(Integer, nullable=True, index=True)  # tournament_id
    sgg_event_id = Column(Integer, nullable=True, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=True)
    end_date = Column(DateTime, nullable=False)
    num_entrants = Column(Integer, nullable=False)
    is_valid = Column(Boolean, nullable=True)  # If valid for ranking
    # null / None means it hasn't been checked yet.

    sets = relationship("Set", back_populates="tournament")

    @property
    def is_populated(self):
        """ Whether the sets from this tournament have been retrieved. """
        return len(self.sets) > 0


class Player(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    sgg_id = Column(Integer, nullable=True, index=True)  # TODO: Anon have ID?
    name = Column(String, nullable=False)
    country = Column(String, nullable=True)


class Set(Base):
    """
    A set between two players in a Tournament.

    The round specified the order in which sets must be processed.

    For double elimination, these are all winner side matches followed by all
    loser side matches and finalized with grand finals.

    For round robin or swiss, these are ???

    TODO: Process at the same time (batch change) or figure out some order?

    A negative score indicates a DQ.
    """
    id = Column(Integer, primary_key=True)
    order = Column(Integer, nullable=False)  # Order index

    tournament_id = Column(Integer, ForeignKey('tournament.id'), nullable=False)
    tournament = relationship("Tournament", back_populates="sets")

    winning_player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    winning_player = relationship("Player", foreign_keys=[winning_player_id])
    winning_score = Column(Integer, nullable=False)

    losing_player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    losing_player = relationship("Player", foreign_keys=[losing_player_id])
    losing_score = Column(Integer, nullable=False)

    # If one or more participants are not verified for the tournament, the sets
    # must manually be flagged as valid.
    verified = Column(Boolean, nullable=False)


class Ranking(Base):
    """
    Ranking at a specific point in time.

    These serve both historical views and as a cache of intermediate results.
    """
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # Display name for a ranking
    type = Column(String, nullable=False)  # Eg.: elo, placings, ...
    date = Column(DateTime, nullable=True)
    prev_ranking_id = Column(Integer, ForeignKey('ranking.id'), nullable=True)
    previous_ranking = relationship("Ranking")


class PlayerRanking(Base):
    """
    A player's score and metadata at a given ranking's time.

    Because different algorithms may require different forms of metadata, it is
    exposed a JSONB field.
    """
    id = Column(Integer, primary_key=True, autoincrement=True)
    score = Column(Float, nullable=False)
    # Algorithm-specific metadata. Eg. K-values for ELO.
    meta = Column(JSONB, default=dict)  # Non-mutable. Must assign to field.
