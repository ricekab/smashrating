"""
Glicko ranking algorithm.

Implementation is done based on the paper found here:

http://www.glicko.net/glicko/glicko.pdf

Note that this IS Glicko-2, which adds a volatility factor (sigma).
"""
import math
from collections import defaultdict

BASE_R = 1500  # Initial rating
BASE_RD = 350  # Maximum (and Initial) rating deviation
MINIMUM_RD = 30.0

C = 100.0  # Deviation factor when inactive
# C is derived from the duration of a rating interval and number of intervals
# until a player's RD is maximized from an average RD (50 for our calculation).

# For 2-month periods, 24 month reset:
# C = 100.0
# For 1-month periods, 24 month reset:
# C = 70.71067811865476
# For 1-month periods, 18 month reset:
# C = 81.64965809277261

Q = math.log(10) / 400  # math.log without explicit base is ln


class Rating(object):
    def __init__(self, rating=BASE_R, deviation=BASE_RD):
        """

        :param rating:
        :type rating: int or float

        :param deviation:
        :type deviation: int or float

        """
        self.r = rating
        self.rd = deviation

    def update_deviation(self, factor=1.0):
        """
        The deviation is increased at the beginning of a rating period.

        :param factor: Inactivity factor. Value must be in range [0.0; 1.0],
            where 1.0 represents inactivity (no games played) and 0.0 represents
            enough activity to prevent any increase in deviation.
        :type factor: float
        """
        if not 0.0 <= factor <= 1.0:
            raise ValueError(f'Inactivity factor must be a value between 0.0 '
                             f'and 1.0. (Given: {factor} .')
        self.rd = min(math.sqrt(self.rd ** 2 + (C * factor) ** 2), BASE_RD)
        self.rd = max(self.rd, MINIMUM_RD)  # Ensure it is above the threshold.

    def clone(self):
        """ Returns a new Rating instance with the same values as this one. """
        return Rating(rating=self.r, deviation=self.rd)

    def __repr__(self):
        return f'<Rating(rating={self.r}, deviation={self.rd})>'


def update_deviation(player_ratings, deviation_factors):
    """

    :param player_ratings: The previous rating period's data. The key must
        be hashable and uniquely identify a player.

        The dictionary and its values are not modified by this function.
    :type player_ratings: dict[Any, Rating]

    :param deviation_factors: Each player's inactivity factor. The key must
        be hashable and uniquely identify a player.

        A player that is not present in this dictionary is considered to have a
        factor of 1.0 (completely inactive).

        The dictionary and its values are not modified by this function.
    :type deviation_factors: dict[Any, float]

    :return: A new rating dictionary with updated deviations.
    :rtype: dict[Any, Rating]
    """
    player_ratings = {p: r.clone() for p, r in player_ratings.items()}
    for player, rating in player_ratings.items():
        factor = deviation_factors.get(player, 1.0)
        rating.update_deviation(factor)
    return player_ratings


def update_ranking(sets, player_ratings=None):
    """
    Updates the rating and deviation for all players in the given sets.

    Players found in sets but not in player_ratings are considered new players
    to the system.

    Note that Step 1 of the glicko algorithm (Updating RD) is not handled by
    this function, you must use update_deviation prior to this function call.

    :param sets: An iterable collection of set data. A single set is expected
        to be a tuple with the winner and loser (in that order).

        The same hashable identification that is used for the player_ratings
        dictionary is expected.
    :type sets: collections.Iterable[tuple[Any, Any]]

    :param player_ratings: The previous rating period's data. The key must
        be hashable and uniquely identify a player.

        The dictionary and its values are not modified by this function.

        If None, this is assumed to be the first rating period.

        Default: None .
    :type player_ratings: dict[Any, Rating]

    :return:
    :rtype player_ratings: collections.Iterable[PlayerRating]
    """
    # NOTE: Step 1 of glicko (Update RD) must be done prior to this function!
    # Copy ratings for internal use (no mutation of parameters)
    player_ratings = player_ratings or dict()
    old_ratings = defaultdict(init_rating)  # Pre-period ratings
    old_ratings.update(player_ratings)
    # Post-period ratings, stays identical for players that haven't played.
    new_ratings = dict(old_ratings)
    # Step 2_A: Collect all players that are being rated this period.
    players = set(s[0] for s in sets).union(set(s[1] for s in sets))
    for p in players:
        p_old = old_ratings[p]
        won_sets = filter(lambda s: s[0] == p, sets)
        lost_sets = filter(lambda s: s[1] == p, sets)
        rating_sum = 0
        d_squared = 0
        for ws in won_sets:
            opp_old = old_ratings[ws[1]]
            g = _g(opp_old.rd)
            e = 1 + math.pow(10, -1 * g * (p_old.r - opp_old.r) / 400)
            e = 1 / e
            rating_sum = rating_sum + (g * (1 - e))  # 1 = win
            d_squared = d_squared + (g ** 2 * e * (1 - e))
        for ls in lost_sets:
            opp_old = old_ratings[ls[0]]
            g = _g(opp_old.rd)
            e = 1 + math.pow(10, -1 * g * (p_old.r - opp_old.r) / 400)
            e = 1 / e
            rating_sum = rating_sum + (g * (0 - e))  # 0 = loss
            d_squared = d_squared + (g ** 2 * e * (1 - e))
        d_squared = Q ** 2 * d_squared
        d_squared = d_squared ** -1
        r_change = Q / (1 / (p_old.rd ** 2) + (1 / d_squared)) * rating_sum
        new_r = p_old.r + r_change
        new_rd = math.sqrt((1 / p_old.rd ** 2 + 1 / d_squared) ** -1)
        new_rd = max(new_rd, MINIMUM_RD)  # Minimum RD value
        new_ratings[p] = Rating(rating=new_r, deviation=new_rd)
    return new_ratings


def init_rating():
    return Rating()


def _g(rd):
    return 1 / math.sqrt(1 + 3 * Q ** 2 * rd ** 2 / math.pi ** 2)
