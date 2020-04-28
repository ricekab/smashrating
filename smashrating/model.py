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
    sgg_id = Column(Integer, nullable=True, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=True)

    won_sets = relationship('Set',
                            foreign_keys="Set.winning_player_id",
                            back_populates="winning_player")

    lost_sets = relationship('Set',
                             foreign_keys="Set.losing_player_id",
                             back_populates="losing_player")

    @property
    def sets(self):
        """
        Retrieves both winning and losing sets.

        Note that this collection is read-only! Additions to this collection
        will not be persisted (unless of course it has the necessary references
        already).
        """
        return self.won_sets + self.lost_sets

    @property
    def is_anonymous(self):
        """
        If the user has no external IDs at all.

        Since there is no way to be sure, a lot of duplicate names may exist
        under different anonymous user (1 per tournament). This does NOT mean
        they don't have an account, but merely the tournament the results are
        from did not have him/her as a verified attendee.

        Unfortunately, because of the large data set there are bound to many
        name clashes that we cannot resolve automatically.
        """
        return not any([self.sgg_id])  # Add challonge, etc if we add them later


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
    winning_player = relationship("Player", foreign_keys=[winning_player_id],
                                  back_populates="won_sets")
    winning_score = Column(Integer, nullable=False)

    losing_player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    losing_player = relationship("Player", foreign_keys=[losing_player_id],
                                 back_populates="lost_sets")
    losing_score = Column(Integer, nullable=False)

    # State of the set. These are the following expected values:
    # 1 - VERIFIED: Both players in the set are verified participants.
    # -1 - UNVERIFIED: One or more participant is unverified, but both are
    #                 linked to proper accounts.
    # -2 - ANONYMOUS: One or more players is not linked to an account. These
    #                  are manual entries by TOs and cannot automatically be
    #                  linked to a player.
    state = Column(Integer, nullable=False)

    # State "static" values
    VERIFIED = 1
    UNVERIFIED = -1
    ANONYMOUS = -2


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
