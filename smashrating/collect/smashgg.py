"""
smash.gg data scraper. Required an API key.
"""
import json
import logging
import time
from datetime import datetime
from pprint import pprint as pp
from smashrating.model import Tournament, Player, Set
from graphqlclient import GraphQLClient
from smashrating.collect import smashgg_queries as queries

_logger = logging.getLogger(__name__)

API_ENDPOINT = "https://api.smash.gg/gql/alpha"
# Constants used to filter relevant data
SSBU_GAME_ID = 1386  # Videogame ID for SSBU
EVENT_TYPE_SINGLES = 1  # Event type ID for 1v1


def filter_event(event_dict):
    return event_dict['isOnline'] is False \
           and event_dict['numEntrants'] \
           and event_dict['numEntrants'] > 30 \
           and event_dict['videogame']['id'] == SSBU_GAME_ID \
           and event_dict['type'] == EVENT_TYPE_SINGLES \
           and event_dict['state'] == 'COMPLETED'


def filter_tournament_dict(tournament_dict):
    """
    Check a tournament data dict if it fits the required criteria.

    This does NOT mean it should be used. Squad strike and other 1v1 SSBU events
    will pass this test as well.

    New tournament entries will have to manually be verified.

    :param tournament_dict:
    :type tournament_dict: dict

    :return: True if the tournament contains at least one eligible event. False
        otherwise.
    :rtype: bool
    """
    valid_events = list(filter(filter_event, tournament_dict['events']))
    return len(valid_events) > 0


class SmashGGScraper(object):
    def __init__(self, session, api_key, max_requests_per_min=80,
                 object_limit=1000):
        """

        :param session: SQLAlchemy session to cache data to.
        :type session: sqlalchemy.orm.Session

        :param api_key: smash.gg API key to authenticate requests.
        :type api_key: str

        :param max_requests_per_min: Maximum number of requests per second.
            Default: 80 .
        :type max_requests_per_min: int

        :param object_limit: Maximum number of objects per request.
            Default: 1000 .
        :type object_limit: int

        :see: https://smashgg-developer-portal.netlify.app/docs/rate-limits
        """
        self.session = session
        self._client = GraphQLClient(endpoint=API_ENDPOINT)
        self._client.inject_token(f"Bearer {api_key}")
        self._req_times = [0 for _ in range(max_requests_per_min)]
        self._req_idx = 0  # type: int
        self.object_limit = object_limit

    def submit_request(self, query, params):
        # Ensure we wait out any delay (1.0 extra second leeway)
        elapsed_time = time.time() - self._req_times[self._req_idx]
        if elapsed_time < 60.0:
            _logger.debug(f"Sleeping {60.0 - elapsed_time}")
            time.sleep(61.0 - elapsed_time)  # Extra second for inaccuracies
        self._req_times[self._req_idx] = time.time()
        self._req_idx = (self._req_idx + 1) % len(self._req_times)
        # TODO: Better as a try-catch --> May run multiple instances of scrapers
        # |-> Exponential back-off would resolve bottlenecks more gracefully.
        _logger.debug(f'> Executing query (page {params.get("page", 1)})')
        result = self._client.execute(query=query, variables=params)  # str
        result = json.loads(result)
        # Ignore metadata and just return the requested data.
        try:
            return result["data"]
        except KeyError:
            # TODO: Error handling here
            from pprint import pprint
            pprint(result)
            raise NotImplementedError("Handle error here")

    def _extract_tournaments(self, tournament_dicts):
        """
        Convert given tournament data dicts into Tournament instances.

        :param tournament_dicts:
        :type tournament_dicts: collections.Iterable[dict]

        :return:
        :rtype: list[Tournament]
        """
        tournaments = list()
        for td in tournament_dicts:
            for evt in filter(filter_event, td['events']):
                t = Tournament(sgg_id=td['id'],
                               sgg_event_id=evt['id'],
                               name=f"{td['name']} - {evt['name']}",
                               country=td['countryCode'],
                               end_date=datetime.utcfromtimestamp(td['endAt']),
                               num_entrants=evt['numEntrants'])
                tournaments.append(t)
        self._merge_tournaments(tournaments)
        return tournaments

    def _merge_tournaments(self, new_tournaments):
        """
        Merges the given tournaments into the database.

        New entries are added as-is. If an external ID match is found, the data
        is merged (updated) on the existing entry.

        :param new_tournaments:
        :type new_tournaments: list[Tournament]
        """
        tournaments = self.session.query(Tournament).all()
        id_map = {(t.sgg_id, t.sgg_event_id,): t.id for t in tournaments}
        for new_t in new_tournaments:
            # Use existing id if a match is found, otherwise let db generate it.
            id_match = id_map.get((new_t.sgg_id, new_t.sgg_event_id,))
            if id_match:
                _logger.debug(f"Existing Tournament found, merging entry "
                              f"(id={id_match}).")
                new_t.id = id_match
                self.session.merge(new_t)
            else:
                _logger.debug(f"Adding new Tournament: {new_t}'.")
                self.session.add(new_t)
        self.session.commit()

    def _merge_players(self, new_players):
        """
        Merges the given players into the database.

        New entries are added as-is. If an external ID match is found, the data
        is merged (updated) on the existing entry.

        :param new_players:
        :type new_players: collections.Iterable[Player]
        """
        players = self.session.query(Player).all()
        id_map = {p.sgg_id: p.id for p in players}
        for new_p in new_players:
            # Use existing id if a match is found, otherwise let db generate it.
            id_match = id_map.get(new_p.sgg_id)
            if id_match:
                _logger.debug(f"Existing Player found, merging entry "
                              f"(id={id_match}).")
                new_p.id = id_match
                self.session.merge(new_p)
            else:
                _logger.debug(f"Adding new Player: {new_p}'.")
                self.session.add(new_p)
        self.session.commit()

    def get_all_tournaments(self, after_date=1):
        """
        TODO: DOC

        :param after_date: Filter tournaments after the given UNIX timestamp.
            You can use datetime.timestamp() to get the UNIX timestamp when
            using datetime objects.

            By default uses timestamp 1 (1970/01/01) which practically
            queries all tournaments.
        :type after_date: int or float

        :return:
        """
        s_time = time.time()
        objects_per_page = 50
        paging = self.submit_request(
            query=queries.TOURNAMENTS_ALL_PAGING,
            params=dict(afterDate=after_date,
                        perPage=objects_per_page))['tournaments']['pageInfo']
        tournament_dicts = list()
        _logger.debug(f'Querying for {paging["totalPages"]} pages.')
        for page in range(1, paging['totalPages'] + 1):
            result = self.submit_request(
                query=queries.TOURNAMENTS_ALL,
                params=dict(afterDate=after_date,
                            page=page,
                            perPage=objects_per_page))
            # TODO: Sometimes nodes are empty?
            if result['tournaments']['nodes'] is None:
                print(f"Page {page} is empty?")
            tournament_dicts.extend(result['tournaments']['nodes'] or list())
        _logger.debug(f'Queries took {time.time() - s_time} seconds.')
        tournaments = self._extract_tournaments(tournament_dicts)
        return tournaments

    def get_tournaments_by_country(self, country_code, after_date=1):
        """
        Retrieves all tournaments for a given country code.

        :param country_code:
        :type country_code: str

        :param after_date: Filter tournaments after the given UNIX timestamp.
            You can use datetime.timestamp() to get the UNIX timestamp when
            using datetime objects.

            By default uses timestamp 1 (1970/01/01) which practically
            queries all tournaments.
        :type after_date: int or float

        :return:
        :rtype: list[Tournament]
        """
        objects_per_page = 100
        paging = self.submit_request(
            query=queries.TOURNAMENTS_BY_COUNTRY_PAGING,
            params=dict(countryCode=country_code,
                        afterDate=after_date,
                        perPage=objects_per_page))['tournaments']['pageInfo']
        tournament_dicts = list()
        for page in range(1, paging['totalPages'] + 1):
            result = self.submit_request(
                query=queries.TOURNAMENTS_BY_COUNTRY,
                params=dict(countryCode=country_code,
                            afterDate=after_date,
                            page=page,
                            perPage=objects_per_page))
            tournament_dicts.extend(result['tournaments']['nodes'])
        tournaments = self._extract_tournaments(tournament_dicts)
        return tournaments

    def get_tournaments_by_player_id(self, player_id, include_sets=True):
        """
        Retrieve all tournaments a given player has participated in.

        :param player_id:
        :type player_id: int

        :param include_sets: Whether to include sets for the tournaments as
            well. Default: True .
        :type include_sets: bool

        :return:
        :rtype: list[Tournament]
        """
        raise NotImplementedError()

    def populate_empty_tournaments(self):
        """
        Populates all empty (valid) tournaments.

        :return:
        """
        valid_tournaments = self.session.query(Tournament) \
            .filter_by(is_valid=True) \
            .all()
        empty_tournaments = [t for t in valid_tournaments if not t.is_populated]
        pp(empty_tournaments)
        raise NotImplementedError()

    def populate_tournament(self, tournament):
        """

        :param tournament:
        :type tournament: Tournament

        :return:
        """
        if tournament.is_populated and tournament.is_valid:
            return
        objects_per_page = 48
        paging = self.submit_request(
            query=queries.EVENT_SETS_PAGING,
            params=dict(eventId=tournament.sgg_event_id,
                        perPage=objects_per_page))['event']['sets']['pageInfo']
        set_dicts = list()
        for page in range(1, paging['totalPages'] + 1):
            result = self.submit_request(
                query=queries.EVENT_SETS,
                params=dict(eventId=tournament.sgg_event_id,
                            page=page,
                            perPage=objects_per_page))
            set_dicts.extend(result['event']['sets']['nodes'])
        set_dicts = list(sorted(filter(lambda sd_: sd_['startedAt'], set_dicts),
                                key=lambda sd_: sd_['startedAt']))
        sets = list()
        players = dict()
        pp(set_dicts)
        for idx, sd in enumerate(set_dicts):
            winner, loser = sorted(sd['slots'],
                                   key=lambda s: s['standing']['placement'])
            winner_sgg_id = winner['entrant']['participants'][0]['user']['id']
            winner_name = winner['entrant']['participants'][0]['gamerTag']
            winner_verified = winner['entrant']['participants'][0]['verified']
            winner_score = winner['standing']['stats']['score']['value']
            loser_sgg_id = loser['entrant']['participants'][0]['user']['id']
            loser_name = loser['entrant']['participants'][0]['gamerTag']
            loser_verified = loser['entrant']['participants'][0]['verified']
            loser_score = loser['standing']['stats']['score']['value']
            if loser_score < 0:  # Negative score is a DQ
                print("SHOULD NEVER HAPPEN NOW")
                continue
            if winner_sgg_id not in players:
                players[winner_sgg_id] = Player(sgg_id=winner_sgg_id,
                                                name=winner_name)
            if loser_sgg_id not in players:
                players[loser_sgg_id] = Player(sgg_id=loser_sgg_id,
                                               name=loser_name)
            player_w = players[winner_sgg_id]
            player_l = players[loser_sgg_id]
            set_ = Set(order=idx,
                       tournament=tournament,
                       winning_player=player_w,
                       winning_score=winner_score,
                       losing_player=player_l,
                       losing_score=loser_score,
                       verified=winner_verified and loser_verified)
            sets.append(set_)
        self._merge_players(players.values())
        self.session.add_all(sets)
        self.session.commit()

    # TODO: Continue here
    # - Parse set data
    # - Add / merge player instances
    # - Add set instances
