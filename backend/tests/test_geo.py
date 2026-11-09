from app.core.geo import bounding_box, distance_m


def test_one_thousandth_of_a_degree_of_latitude_is_about_111_metres():
    assert 108 < distance_m(31.500, 74.3, 31.501, 74.3) < 114


def test_same_point_has_zero_distance():
    assert distance_m(31.5, 74.3, 31.5, 74.3) == 0


def test_bounding_box_contains_points_inside_the_radius():
    box = bounding_box(31.5, 74.3, 100)
    assert box.min_latitude < 31.5 + 0.0008 < box.max_latitude
    assert box.min_longitude < 74.3 + 0.0009 < box.max_longitude
    assert not box.min_latitude < 31.5 + 0.002 < box.max_latitude
