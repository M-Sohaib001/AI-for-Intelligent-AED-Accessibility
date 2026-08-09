from nlp.location_flagger import flag_location


def test_missing_description():
    result = flag_location("", "Level 1")

    assert "missing_description" in result["flags"]
    assert "missing_floor_info" not in result["flags"]


def test_missing_floor_info():
    result = flag_location("AED near reception", "")

    assert "missing_floor_info" in result["flags"]


def test_floor_reference():
    result = flag_location("AED located on Level 2", "Level 2")

    assert "floor_reference" in result["flags"]


def test_relational_location():
    result = flag_location("Near the main entrance", "Ground")

    assert "relational_location" in result["flags"]


def test_indoor_access():
    result = flag_location("AED beside reception counter", "Level 1")

    assert "possible_indoor_access" in result["flags"]


def test_building_internal_location():
    result = flag_location("AED inside car park", "B1")

    assert "possible_building_internal_location" in result["flags"]


def test_multiple_location_flags():
    result = flag_location(
        "AED near reception on Level 2",
        "",
    )

    assert "missing_floor_info" in result["flags"]
    assert "floor_reference" in result["flags"]
    assert "relational_location" in result["flags"]
    assert "possible_indoor_access" in result["flags"]


def test_normal_location_without_flags():
    result = flag_location(
        "AED outside main entrance",
        "Ground",
    )

    assert result["flags"] == []

def test_location_matching_is_case_insensitive():
    result = flag_location(
        "AED NEAR RECEPTION ON LEVEL 2",
        "",
    )

    assert "missing_floor_info" in result["flags"]
    assert "floor_reference" in result["flags"]
    assert "relational_location" in result["flags"]
    assert "possible_indoor_access" in result["flags"]