import json
import urllib

import ee
import geopandas as gpd
import numpy as np
import pandas as pd

from waterpyk import errors as err
from waterpyk import load_data
from waterpyk.calcs import combine_bands, interp_daily

ee.Initialize()


def gdf_to_feat(gdf, target_epsg='4326'):
    """
    Convert geodataframe with multipolygon geometry to GEE feature.
    This has been tested with simple shapefiles of government lands, etc,
    but it may not work for all places.

    Args:
      gdf (geopandas geodataframe)
      target_epsg (str, optional): target reprojection. defaults to EPSG4326.

    Returns:
      GEE feature

    """
    # Reproject
    gdf = gdf.to_crs(epsg=target_epsg)

    # Get lists of x, y coordinates
    all_coords = []
    for i in gdf.explode(index_parts=True).geometry:
        x, y = i.exterior.coords.xy
        coords = np.dstack((x, y)).tolist()
        all_coords.append(coords)
    # Convert to feature collection
    gee_feat = ee.Feature(ee.Geometry.MultiPolygon(coords=all_coords))
    return gee_feat


def extract_basic(gee_feature, kind, asset_id, scale, bands, start_date=None, end_date=None, relative_date=None, bands_to_scale=None, scaling_factor=1, reducer_type=None, new_bandnames=None):
    """
    Extract data from a single asset. For timeseries, specify start_date  and end_date for an asset_id.
    For an image or to get an image from an imagecollection (ie one date), specify relative_date as either 'first', 'most_recent', or 'image'.
    Either start_date and end_date must be specified or relative_date must be specified or error will be raised.

    Args:
        gee_feature (:obj:`gee feature`): GEE feature for region geometry
        kind (str): 'point' or 'watershed'
        asset_id (str): GEE asset identification string
        start_date (str, optional): format mm/dd/yyy or similiar date format
        end_date (str, optional): format mm/dd/yyyy or similiar date format
        relative_date (str, optional): If not using start and end date, specify 'first', 'most_recent', or 'image' to extract a single date from an ImageCollection or to extract datea from an Image.
        scale (str): scale in meters for GEE reducer function
        bands (list of str): bands of GEE asset to extract
        new_bandnames (list of str, optional): rename bands. Default is to not rename bands, where final band name is the original band name before underscore, for example pml stays pml but LC_Type1 becomes LC by default. This param must be the same length as **bands or exception will be thrown.
        bands_to_scale (list of str, optional): (default = None) bands for which each value will be multiplied by scaling_factor.
        scaling_factor (float, optional): (default = 1) scaling factor to apply to all values in bands_to_scale
        reducer_type (:obj:`gee reducer function`, optional): reducer_type defaults to first() for points and mean() for watersheds. See available gee ReduceRegion options online for other possible inputs.

    Returns:
        :obj:`df`: dataframe of all extracted data
    """
    # Set reducer type based on kind (watershed or point)
    if reducer_type is None:
        if kind == 'point':
            reducer_type = ee.Reducer.first()
        elif kind == 'watershed':
            reducer_type = ee.Reducer.mean()
        elif kind == 'shape':
            reducer_type = ee.Reducer.mean()
        else:
            reducer_type = ee.Reducer.mean()
    else:
        pass

    # Get asset
    if relative_date == 'image':
        asset = ee.Image(asset_id).select(bands)
    elif relative_date is None:
        asset = ee.ImageCollection(asset_id).filterDate(pd.to_datetime(
            start_date), pd.to_datetime(end_date)).select(bands).toBands()
    elif relative_date == 'most_recent':
        asset = ee.ImageCollection(asset_id).sort(
            'system:time_start', False).first().select(bands)
    elif relative_date == 'first':
        asset = ee.ImageCollection(asset_id).first().select(bands)
    else:
        raise err.NoDateSpecifiedError(
            "Specify start and end date or set relative_date argument to be 'most_recent' or 'first'. relative_date was: {}".format(relative_date))

    # Perform reduceRegion
    reducer_dict = asset.reduceRegion(reducer=reducer_type, geometry=gee_feature.geometry(
    ), scale=scale, maxPixels=1e12).getInfo()

    if len(reducer_dict) > len(bands):
        # Make df from reducer output and clean up
        df = pd.DataFrame(list(reducer_dict.items()),
                          columns=['variable', 'value'])
        df['date'] = [item.replace('-', '_').split('_')[:-1]
                      for item in df['variable'].values]
        df['date'] = [pd.to_datetime('-'.join(item[0:3]))
                      for item in df['date'].values]
        df['band'] = [item.split('_')[-1] for item in df['variable'].values]
        df['value_raw'] = df['value']
        # save for renaming bands
        old_bandnames = [item.split('_')[-1]
                         for item in df['variable'].values][0:len(bands)]

        # Calculate temporal gaps between data and interpolate
        date0 = df[df['band'] == df.band.unique()[0]]['date'][0]
        date1 = df[df['band'] == df.band.unique(
        )[0]]['date'][len(df.band.unique())]
        date_range = date1-date0
        df = interp_daily(df)
        print('\tOriginal timestep of ' + str(date_range.days) +
              ' day(s) was interpolated to daily.')

    else:
        df = pd.DataFrame(list(reducer_dict.items()),
                          columns=['variable', 'value'])
        df['band'] = df['variable']
        df['value_raw'] = df['value']
        df['date'] = pd.to_datetime(
            asset.get('system:time_start').getInfo(), unit='ms')
        old_bandnames = bands  # save for renaming bands

    if new_bandnames is not None:
        if len(old_bandnames) == len(new_bandnames):
            name_dict = {k: v for k, v in zip(old_bandnames, new_bandnames)}
            df['band'] = df['band'].map(name_dict)
        else:
            raise err.MissingBandsError(
                "Make sure bands and new_bandnames are same length or leave new_bandnames as None. bands:{},  new_bandnames:{}".format(bands, new_bandnames))

    # Apply scaling factor to specified bands
    if bands_to_scale is not None:
        df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1)
                       for value, band_value in zip(df.value.values, df.band.values)]
        print('\t' + bands_to_scale +
              ' bands were scaled by ' + str(scaling_factor))

    return df


def extract(layers, gee_feature, kind, reducer_type=None, **kwargs):
    """
    Extract data at site for several assets at once. Uses extract_basic().

    Args:
        layers (str or :obj:`df`, optional): If str, specify 'minimal' or 'all' to extract default set of assets. If df, columns that must be present include: asset_id, start_date, end_date, relative_date, scale, bands, bands_to_scale, new_bandnames, scaling factor. These are the same parameters required for extract_basic(). 
        gee_feature (:obj:`gee feature`): GEE feature for region geometry
        kind (str): 'point' or 'watershed'
        reducer_type (:obj:`GEE reducer function`): defaults to None, in which case GEE reduceRegion reducer function is first() and mean() for points and watersheds, respectively. See GEE documentation for more available types.
        **interp (bool, optional): (default: True), currently no option to change to False.
        **combine_ET_bands (bool, optional): (default True) add ET bands to make one ET band.
        **bands_to_combine (list of str, optional): (default [Es, Ec]) ET bands to combine
        **band_names_combined (str, optional): (default 'ET') name of combined ET band

    Returns:
        :obj:`df`, :obj:`df`: 2 long-style pandas dataframes, the first containing all of the daily data and the second containing all of the non-daily data (i.e. extractions from images or from single-timestep ImageCollections).
    """
    # Read in existing csv for typical inputs
    if layers == 'all' or layers == 'minimal':
        print('Getting layers from load_data()...')
        layers = load_data(layers)

    # Otherewise take in dataframe as layers and continue cleaning
    layers = layers.replace({np.nan: None})

    # Turn df entries into suitable formats
    def process_bandnames(row):
        # Make list of strings from string
        bands = [i.split(',') for i in [row.bands]][0]
        bands = [i.replace(" ", "") for i in bands]  # Remove any spaces
        if row.new_bandnames is not None:
            # Make list of strings from string
            new_bandnames = [i.split(',') for i in [row.new_bandnames]][0]
            new_bandnames = [i.replace(" ", "")
                             for i in new_bandnames]  # Remove any spaces
            message = '\tBands {} renamed to {}.'.format(
                row.bands, row.new_bandnames)
            print(message)
        else:
            new_bandnames = None
        return bands, new_bandnames

    # Initialize return dfs
    df = pd.DataFrame(columns=['date'])
    df_image = pd.DataFrame()
    for row in layers.itertuples():
        print('Extracting', row.name)
        bands, new_bandnames = process_bandnames(row)
        single_asset = extract_basic(gee_feature, kind, asset_id=row.asset_id, scale=row.scale, bands=bands, start_date=row.start_date, end_date=row.end_date,
                                     relative_date=row.relative_date, bands_to_scale=row.bands_to_scale, scaling_factor=row.scaling_factor, reducer_type=reducer_type, new_bandnames=new_bandnames)
        single_asset['asset_name'] = row.name
        single_asset_propogate = single_asset[[
            'asset_name', 'value', 'date', 'band']]

        # Append to correct df (daily or single asset)
        if row.relative_date is None:
            df = pd.concat([df, single_asset_propogate], ignore_index=True)
        else:
            df_image = pd.concat(
                [df_image, single_asset_propogate], ignore_index=True)

    # Combine ET bands if specified
    if kwargs['combine_ET_bands']:
        df = combine_bands(
            df, kwargs['bands_to_combine'], kwargs['band_name_final'])
    return df, df_image
