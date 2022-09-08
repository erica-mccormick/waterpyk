import ee
import geopandas as gdp
from waterpyk import gee

ee.Initialize()


def test_checks_if_gdf_to_feat_returns_feat():
    gdf = gdp.read_file('tests/testing_data/test_json_sanbern.json')
    gee_feat = gee.gdf_to_feat(gdf)
    assert type(gee_feat) is ee.Feature


def test_confirms_target_epsg_for_gdf_to_feat():
    gdf = gdp.read_file('tests/testing_data/test_json_sanbern.json')
    gee_feat = gee.gdf_to_feat(gdf)
    gee_feat.projection().getInfo()


def test_extract_basic_prism_for_all_reducers():
    gdf = gdp.read_file('tests/testing_data/test_json_sanbern.json')
    gee_feature = gee.gdf_to_feat(gdf)
    kind = 'watershed'
    asset_id = "OREGONSTATE/PRISM/AN81m"
    scale = 500
    bands = 'ppt'
    relative_date = None
    bands_to_scale = None
    scaling_factor = 1
    reducer_type = None
    new_bandnames = None
    interp = False

    start_date = '2005-10'
    end_date = '2005-12'
    df = gee.extract_basic(gee_feature, kind, asset_id, scale, bands, start_date, end_date,
                           relative_date, bands_to_scale, scaling_factor, reducer_type, new_bandnames, interp)
    assert round(df['value'].sum(
    ), 3) == 48.035, "PRISM summed for 2 months without interpolation changed"

    start_date = '2005-10'
    end_date = '2006-10'
    interp = True
    df = gee.extract_basic(gee_feature, kind, asset_id, scale, bands, start_date, end_date,
                           relative_date, bands_to_scale, scaling_factor, reducer_type, new_bandnames, interp)
    assert round(df['value'].sum(
    ), 3) == 175343.377, "PRISM summed for 1 year with interpolation changed"
    assert str(df['date'][0]) == '2001-06-20 00:00:00'

    interp = False
    df = gee.extract_basic(gee_feature, kind, asset_id, scale, bands, start_date, end_date,
                           relative_date, bands_to_scale, scaling_factor, reducer_type, new_bandnames, interp)
    assert str(df['date'][0]) == '2001-05'
