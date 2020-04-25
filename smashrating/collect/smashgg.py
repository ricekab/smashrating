"""
smash.gg data scraper. Required an API key.
"""
import json
import logging
import time
from datetime import datetime
from pprint import pprint as pp
from urllib.error import HTTPError

from smashrating.model import Tournament, Player, Set
from graphqlclient import GraphQLClient
from smashrating.collect import smashgg_queries as queries

_logger = logging.getLogger(__name__)

API_ENDPOINT = "https://api.smash.gg/gql/alpha"
# Constants used to filter relevant data
SSBU_GAME_ID = 1386  # Videogame ID for SSBU
EVENT_TYPE_SINGLES = 1  # Event type ID for 1v1


def _filter_event(event_dict):
    return event_dict['isOnline'] is False \
           and event_dict['numEntrants'] \
           and event_dict['numEntrants'] > 30 \
           and event_dict['videogame']['id'] == SSBU_GAME_ID \
           and event_dict['type'] == EVENT_TYPE_SINGLES \
           and event_dict['state'] == 'COMPLETED'


# TODO: Include matchmaking events / phases?
_VALID_BRACKET_TYPES = ('SINGLE_ELIMINATION',
                        'DOUBLE_ELIMINATION',
                        'ROUND_ROBIN',
                        'SWISS',
                        )


def _filter_phase(phase):
    return phase['bracketType'] in _VALID_BRACKET_TYPES


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
    valid_events = list(filter(_filter_event, tournament_dict['events']))
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

    def submit_request(self, query, params=None):
        """


        :param query: The graphQL query in string format.
        :type query: str

        :param params: Parameters for the request. If not provided, an empty
            dict is given.
        :type params: dict

        :return: The response data in dictionary format (parsed by json). The
            response metadata is NOT returned.
        :rtype: dict
        """
        params = params or dict()
        _logger.debug(f'> Executing query (page {params.get("page", 1)})')
        result = self._execute_request(query, params)  # str
        result = json.loads(result)
        # Ignore metadata and just return the requested data.
        try:
            return result["data"]
        except KeyError:
            pp(result)
            # TODO: Error handling here (no data?)
            raise NotImplementedError("Handle error here")

    def _execute_request(self, query, params=None, max_retries=5,
                         max_wait_time=60.0):
        """
        Executes the graphQL request with exponential back-off.

        :param query: The graphQL query in string format.
        :type query: str

        :param params: Parameters for the request. If not provided, an empty
            dict is given.
        :type params: dict

        :param max_retries: Maximum number of times to retry. Default: 5 .
        :type max_retries: int

        :param max_wait_time: Maximum amount of time, in seconds) to wait.
            Default: 60.0 .
        :type max_wait_time: int or float

        :return: The response string.
        :rtype: str
        """
        wait_time = 2.5
        for try_idx in range(1, max_retries):
            try:
                return self._client.execute(query=query,
                                            variables=params or dict())
            except HTTPError as http_err:
                if http_err.code != 429:  # Too Many Requests
                    raise http_err
                # Note: 400 (bad request) can be given to indicate too high
                # complexity for a request.
                if try_idx == max_retries - 1:  # Exhausted retries
                    raise http_err
                wait_time *= 2.0
                _logger.info(f"Too many requests (429). Waiting {wait_time:.1f}"
                             f" seconds before resuming.")
                time.sleep(min(wait_time, max_wait_time))
                continue

    # def _merge_players(self, new_players):
    #     """
    #     Merges the given players into the database.
    #
    #     New entries are added as-is. If an external ID match is found, the data
    #     is merged (updated) on the existing entry.
    #
    #     :param new_players:
    #     :type new_players: collections.Iterable[Player]
    #     """
    #     players = self.session.query(Player).all()
    #     id_map = {p.sgg_id: p.id for p in players}
    #     for new_p in new_players:
    #         # Use existing id if a match is found, otherwise let db generate it.
    #         id_match = id_map.get(new_p.sgg_id)
    #         if id_match:
    #             _logger.debug(f"Existing Player found, merging entry "
    #                           f"(id={id_match}).")
    #             new_p.id = id_match
    #             self.session.merge(new_p)
    #         else:
    #             _logger.debug(f"Adding new Player: {new_p}'.")
    #             self.session.add(new_p)
    #     self.session.commit()

    def get_all_tournaments(self, after_date=1, before_date=None):
        """
        TODO: DOC

        :param after_date: Filter tournaments after the given UNIX timestamp.
            You can use datetime.timestamp() to get the UNIX timestamp when
            using datetime objects.

            By default uses timestamp 1 (1970/01/01) which practically
            queries all tournaments.
        :type after_date: int or float

        :param before_date: Filter tournaments before the given UNIX timestamp.
            If not provided. The current datetime is used.
        :type before_date: int or float

        :return:
        """
        before_date = before_date or datetime.utcnow().timestamp()
        st = time.time()
        objects_per_page = 50
        paging = self.submit_request(
            query=queries.TOURNAMENTS_ALL_PAGING,
            params=dict(afterDate=after_date,
                        beforeDate=before_date,
                        perPage=objects_per_page))['tournaments']['pageInfo']
        tournament_dicts = list()
        _logger.info(f'Querying tournaments for {paging["totalPages"]} pages.')
        for page in range(1, paging['totalPages'] + 1):
            result = self.submit_request(
                query=queries.TOURNAMENTS_ALL,
                params=dict(afterDate=after_date,
                            beforeDate=before_date,
                            page=page,
                            perPage=objects_per_page))
            if result['tournaments']['nodes'] is None:
                raise IndexError(
                    f'Empty page when data is expected. This may have hit a '
                    f'SmashGG internal limitation where it cannot paginate '
                    f'results beyond 10000 .')
            tournament_dicts.extend(result['tournaments']['nodes'] or list())
        _logger.debug(f'Tournament retrieval took {time.time() - st} seconds.')
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

    def _extract_tournaments(self, tournament_dicts):
        """
        Convert given tournament data dicts into Tournament instances.

        :param tournament_dicts:
        :type tournament_dicts: collections.Iterable[dict]

        :return:
        :rtype: list[Tournament]
        """
        tournaments = dict()  # type: dict[tuple, Tournament]
        for td in tournament_dicts:
            if not td['events']:
                _logger.warning(f'Skipping tournaments "{td["name"]}", it does '
                                f'not have any events.')
                continue
            for evt in filter(_filter_event, td['events']):
                if tournaments.get((td['id'], evt['id'],)):
                    _logger.warning(
                        f'Duplicate tournament detected, skipping entry: '
                        f'({td["name"]} - {evt["name"]}.')
                t = Tournament(sgg_id=td['id'],
                               sgg_event_id=evt['id'],
                               name=f"{td['name']} - {evt['name']}",
                               country=td['countryCode'],
                               end_date=datetime.utcfromtimestamp(td['endAt']),
                               num_entrants=evt['numEntrants'])
                tournaments[(td['id'], evt['id'],)] = t
        self._merge_tournaments(list(tournaments.values()))
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

    def _extract_sets(self, set_dicts, tournament):
        """

        :param set_dicts:
        :type set_dicts: list[dict]

        :param tournament:
        :type tournament: Tournament

        :return:
        :rtype: list[Set]
        """
        sets = list()
        players = self.session.query(Player).all()
        p_sgg_map = {p.sgg_id: p for p in players}
        anon_name_map = dict()
        for idx, sd in enumerate(set_dicts):
            winner, loser = sorted(sd['slots'],
                                   key=lambda s: s['standing']['placement'])
            # Score can be None if no scores are given (just win/loss)
            w_score = winner['standing']['stats']['score']['value'] or 0
            l_score = loser['standing']['stats']['score']['value'] or 0
            if l_score < 0:  # Negative score is a DQ
                _logger.debug(f"Skipping set {sd['id']}. Reason: DQ .")
                continue
            w_data = _extract_player_data(winner)
            l_data = _extract_player_data(loser)
            # W player
            if w_data["sgg_id"]:
                if w_data['sgg_id'] not in p_sgg_map:
                    p_sgg_map[w_data['sgg_id']] = Player(
                        sgg_id=w_data['sgg_id'],
                        name=w_data['name'],
                        country=w_data['country'])
                w_player = p_sgg_map[w_data['sgg_id']]
            else:
                if w_data['name'] not in anon_name_map:
                    anon_name_map[w_data['name']] = Player(
                        sgg_id=w_data['sgg_id'],  # None
                        name=w_data['name'],
                        country=w_data['country'])
                w_player = anon_name_map[w_data['name']]
            # L player
            if l_data["sgg_id"]:
                if l_data['sgg_id'] not in p_sgg_map:
                    p_sgg_map[l_data['sgg_id']] = Player(
                        sgg_id=l_data['sgg_id'],
                        name=l_data['name'],
                        country=l_data['country'])
                l_player = p_sgg_map[l_data['sgg_id']]
            else:
                if l_data['name'] not in anon_name_map:
                    anon_name_map[l_data['name']] = Player(
                        sgg_id=l_data['sgg_id'],  # None
                        name=l_data['name'],
                        country=l_data['country'])
                l_player = anon_name_map[l_data['name']]
            set_ = Set(order=idx,
                       tournament=tournament,
                       winning_player=w_player,
                       winning_score=w_score,
                       losing_player=l_player,
                       losing_score=l_score,
                       verified=w_data['verified'] and l_data['verified'])
            sets.append(set_)
        return sets

    def populate_empty_tournaments(self):
        """
        Populates all empty (valid) tournaments.

        :return:
        """
        valid_tournaments = self.session.query(Tournament) \
            .filter_by(is_valid=True) \
            .all()
        empty_tournaments = [t for t in valid_tournaments if not t.is_populated]
        _logger.info(f'Populating {len(empty_tournaments)} tournaments.')
        for tournament in empty_tournaments:
            self.populate_tournament(tournament)

    def populate_tournament(self, tournament):
        """

        :param tournament:
        :type tournament: Tournament

        :return:
        """
        if tournament.is_populated and tournament.is_valid:
            _logger.info(f"Skipping tournament '{tournament.name}' "
                          f"({tournament.id}). It has already been processed "
                          f"or has not been flagged as valid.")
            return
        phases = self.submit_request(
            query=queries.EVENT_PHASES,
            params=dict(eventId=tournament.sgg_event_id))['event']['phases']
        for idx, ph in enumerate(phases):
            if idx == 0:
                continue
            prev_ph = phases[idx - 1]
            if ph['numSeeds'] >= prev_ph['numSeeds']:
                _logger.warning(
                    f'Phase "{ph["name"]}" contains more players than the '
                    f'preceding phase "{prev_ph["name"]}". This could be a '
                    f'matchmaking bracket after the main bracket?')
        for phase in (_ph for _ph in phases if _filter_phase(_ph)):
            self._extract_phase_sets(tournament, phase)

    def _extract_phase_sets(self, tournament, phase):
        """

        :param tournament:
        :type tournament: smashrating.model.Tournament

        :param phase:
        :type phase: dict

        :return:
        :rtype: list[Set]
        """
        objects_per_page = 40
        paging = self.submit_request(
            query=queries.PHASE_SETS_PAGING,
            params=dict(phaseId=phase['id'],
                        perPage=objects_per_page))['phase']['sets']['pageInfo']
        set_dicts = list()
        # Sets are in reverse order, so we go from last to first page and
        # last to first set on each page.
        for page in range(paging['totalPages'], 0, -1):
            result = self.submit_request(
                query=queries.PHASE_SETS,
                params=dict(phaseId=phase['id'],
                            page=page,
                            perPage=objects_per_page))
            # Sets are in reverse call order.
            set_dicts.extend(reversed(result['phase']['sets']['nodes']))
        # Note: StartedAt is not reliable, it's null for random sets.
        # set_dicts = list(sorted(filter(lambda sd_: sd_['startedAt'], set_dicts),
        #                         key=lambda sd_: sd_['startedAt']))
        sets = self._extract_sets(set_dicts, tournament)
        self.session.add_all(sets)  # Not required due to link with tournament
        self.session.commit()


def _extract_player_data(player_dict):
    participant = player_dict['entrant']['participants'][0]
    user = participant['user']
    sgg_id = user['id'] if user else None
    name = participant['gamerTag']
    verified = participant['verified']
    country = user['location']['country'] if user and user['location'] else None
    return dict(sgg_id=sgg_id,
                name=name,
                verified=verified,
                country=country)
