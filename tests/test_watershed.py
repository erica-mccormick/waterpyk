import warnings

import geopandas as gpd
import pytest
from waterpyk import errors, watershed

# python3 -m pytest tests -v --disable-warnings


def test_should_always_pass():
    assert 2 + 2 == 4, "This is just a dummy test"


def test_should_always_fail():
    assert 2 + 2 == 6, "This is just a dummy test"

############### TESTING EXTRACT_URLS() ###############


@pytest.fixture
def usgs_gauge():
    gage = 11475560  # Elder Creek
    return gage


def test_that_default_kwargs_have_not_changed():
    urls = watershed.extract_urls(11475560)
    assert '1980-10-01' in urls[3], "flow_start_date default_kwarg has changed"
    assert '2021-10-01' in urls[3], "flow_end_date default_kwarg has changed"


def test_should_find_four_urls_for_str_or_int_gaugeid():
    urls = watershed.extract_urls(11475560)
    urls_str = watershed.extract_urls('11475560')
    assert len(urls) == 4, "four urls were not returned using int gauge ID"
    assert len(urls_str) == 4, "four urls were not returned using str gauge ID"


def test_checks_urls_in_expected_order():
    urls = watershed.extract_urls(11475560)
    assert 'basin' in urls[0], "the first url does not include the str 'basin'"
    assert 'flowlines' in urls[1], "the second url does not include the str 'flowline'"
    assert '/?f=json' in urls[2], "the third url does not have the json identifier immediately after the slash"
    assert 'begin_date' in urls[3], "the fourth url does not have the str 'begin_date'"


def test_checks_geometry_col_exists_in_basin_and_flow_gdfs():
    urls = watershed.extract_urls(11475560)
    basin_geometry = gpd.read_file(urls[0])
    flow_geometry = gpd.read_file(urls[1])
    assert 'geometry' in list(basin_geometry.columns)
    assert 'geometry' in list(flow_geometry.columns)


def test_should_raise_error_if_gauge_id_too_long():
    with pytest.raises(errors.GageTooLongError) as exception_info:
        urls = watershed.extract_urls(gage=1111111111)
    assert exception_info.value.args[0] == 'Gage ID length is 10 and cannot be greater than 8.'


def test_preceding_zeros_added_for_gaugeid_too_short():
    urls_int_gauge = watershed.extract_urls(gage=1234)
    urls_str_gauge = watershed.extract_urls(gage='1234')
    expected_gauge_id = '00001234'
    assert expected_gauge_id in urls_int_gauge[0]
    assert expected_gauge_id in urls_str_gauge[0]


def test_if_kwargs_changes_work():
    begin_date = '1985-10-01'
    end_date = '2015-10-01'
    urls = watershed.extract_urls(11475560,
                                  flow_start_date=begin_date,
                                  flow_end_date=end_date)
    assert begin_date in urls[3]
    assert end_date in urls[3]
