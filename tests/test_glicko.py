import pytest
from smashrating import glicko

def test_glicko_rating_algorithm():
    """ Based on example given in https://www.glicko.net/glicko/glicko.pdf ."""
    player_ratings = {
        1: glicko.Rating(rating=1500, deviation=200),
        2: glicko.Rating(rating=1400, deviation=30),
        3: glicko.Rating(rating=1550, deviation=100),
        4: glicko.Rating(rating=1700, deviation=300),
    }
    sets = [(1,2,),
            (3,1,),
            (4,1,),
            ]
    new_ratings = glicko.update_ranking(sets=sets, player_ratings=player_ratings)
    p1_rating = new_ratings[1]
    # 1464 according to paper
    assert 1463.49 < p1_rating.r < 1464.50
    # 151.4 according to paper
    assert 151.349 < p1_rating.rd < 151.450

def test_deviation_update_algorithm():
    player_ratings = {
        1: glicko.Rating(rating=1500, deviation=200),
        2: glicko.Rating(rating=1400, deviation=30),
        3: glicko.Rating(rating=1550, deviation=100),
        4: glicko.Rating(rating=1700, deviation=300),
    }
    new_ratings_c100 = glicko.update_deviation(player_ratings=player_ratings, c_factor=100.0)
    # TODO: Assert values are within correct range
    new_ratings_c50 = glicko.update_deviation(player_ratings=player_ratings, c_factor=50.0)
    # TODO: Assert values are within correct range
    new_ratings_c60 = glicko.update_deviation(player_ratings=player_ratings, c_factor=60.0)
    # TODO: Assert values are within correct range
    raise NotImplementedError()

def test_negative_c_factor_is_invalid():
    player_ratings = {
        1: glicko.Rating(rating=1500, deviation=200),
    }
    with pytest.raises(ValueError):
        glicko.update_deviation(player_ratings=player_ratings, c_factor=-123)
    with pytest.raises(ValueError):
        glicko.update_deviation(player_ratings=player_ratings, c_factor=0)

def test_invalid_deviation_factor():
    raise NotImplementedError()

def test_invalid_parameters():
    # TODO: may need to be broken into multiple parts
    raise NotImplementedError()

def test_deviation_update_does_not_exceed_maximum():
    # TODO: Test with multiple maximums
    raise NotImplementedError()

def test_deviation_update_ensures_minimum():
    # TODO: Test with multiple minimums
    raise NotImplementedError()

def test_rating_update_does_not_mutate_arguments():
    player_ratings = {
        1: glicko.Rating(rating=1500, deviation=200),
        2: glicko.Rating(rating=1400, deviation=30),
        3: glicko.Rating(rating=1550, deviation=100),
        4: glicko.Rating(rating=1700, deviation=300),
    }
    sets = [(1,2,),
            (3,1,),
            (4,1,),
            ]
    new_ratings = glicko.update_ranking(sets=sets, player_ratings=player_ratings)
    assert player_ratings[1] != new_ratings[1]
    assert player_ratings[1].r == 1500
    assert player_ratings[1].rd == 200

def test_deviation_update_does_not_mutate_arguments():
    player_ratings = {
        1: glicko.Rating(rating=1500, deviation=200),
        2: glicko.Rating(rating=1400, deviation=30),
        3: glicko.Rating(rating=1550, deviation=100),
        4: glicko.Rating(rating=1700, deviation=300),
    }
    new_ratings = glicko.update_deviation(player_ratings=player_ratings)
    assert player_ratings[1] != new_ratings[1]
    assert player_ratings[1].r == 1500
    assert player_ratings[1].rd == 200
