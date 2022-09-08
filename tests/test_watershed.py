import geopandas as gpd
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from waterpyk import errors, watershed

# python3 -m pytest tests -v --disable-warnings


def test_should_always_pass():
    assert 2 + 2 == 4, "This is just a dummy test"

# def test_should_always_fail():
#    assert 2 + 2 == 6, "This is just a dummy test"

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


def test_if_kwargs_changes_work_throughout():
    begin_date = '1985-10-01'
    end_date = '1986-10-01'
    urls = watershed.extract_urls(11475560,
                                  flow_start_date=begin_date,
                                  flow_end_date=end_date)
    # Check that begin_date is in the urls
    assert begin_date in urls[3], "begin date is not in flow URL"
    assert end_date in urls[3], "end date is not in flow URL"
    df = watershed.extract_streamflow(11475560,
                                      flow_start_date=begin_date,
                                      flow_end_date=end_date)
    assert df.iloc[0]['date'].strftime(
        '%Y-%m-%d') >= begin_date, "data exists before begin_date"
    assert df.iloc[-1]['date'].strftime(
        '%Y-%m-%d') <= end_date, "data exists after end_date"


def test_checks_if_usgs_api_streamflow_has_changed():
    # Get new discharge csv using the same (default) dates
    kwargs = {'flow_start_date': '1980-10-01',
              'flow_end_date': '2021-10-01'}
    df_new = watershed.extract_streamflow(11475560, **kwargs)
    df_new.to_csv('new_gauge.csv')
    # Pull in csv of old version
    df_old = pd.read_csv('tests/testing_data/flow_11475560.csv')
    df_new = df_new[['Q_cfs', 'Q_mm']]
    df_old = df_old[['Q_cfs', 'Q_mm']]
    assert_frame_equal(
        df_old, df_new, check_dtype=False), "expected Elder Q has changed or other error has occured"


def test_checks_if_latitude_changed():
    lat = watershed.extract_latitude(11475560)
    assert round(lat, 5) == 39.71395
