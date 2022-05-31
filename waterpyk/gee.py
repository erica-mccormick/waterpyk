import geopandas as gpd
import urllib
import json
import ee
ee.Initialize()
import pandas as pd
import numpy as np
from waterpyk.calcs import interp_daily, combine_bands

def extract_basic(gee_feature, kind, asset_id, scale, bands, start_date = None, end_date = None, relative_date = None, bands_to_scale = None, scaling_factor = 1, reducer_type = None, new_bandnames = None):
        """
        (Formerly extract_single_asset_at_site) Extract data from start_date to end_date for an asset_id.

        Args:
            gee_feature: GEE feature for region geometry
            kind (str): 'point' or 'watershed'
            asset_id (str): GEE asset identification string
            start_date (str): format mm/dd/yyy or similiar date format
            end_date (str): format mm/dd/yyyy or similiar date format
            scale (int): scale in meters for GEE reducer function
            bands (list of str): bands of GEE asset to extract
            bands_to_scale (list of str, optional): bands for which each value will be multiplied by scaling_factor.
            scaling_factor (float, optional): scaling factor to apply to all values in bands_to_scale
            reducer_type (function, optional): reducer_type defaults to first() for points and mean() for watersheds. See available gee ReduceRegion options online for other possible inputs.
        Returns:
            df: pandas dataframe of all extracted data
        """
        # Set reducer type based on kind (watershed or point)
        if reducer_type is None:
            if kind == 'point':
                reducer_type = ee.Reducer.first()
            elif kind == 'watershed':
                reducer_type = ee.Reducer.mean()
        else: pass

        # Get asset
        if relative_date == 'image':
          asset = ee.Image(asset_id).select(bands)
        elif relative_date is None:
            asset = ee.ImageCollection(asset_id).filterDate(pd.to_datetime(start_date), pd.to_datetime(end_date)).select(bands).toBands()
        elif relative_date == 'most_recent':
          asset = ee.ImageCollection(asset_id).sort('system:time_start', False).first().select(bands)
        elif relative_date == 'first':
          asset = ee.ImageCollection(asset_id).first().select(bands)
        else: 
            raise Exception("Specify start and end date or set relative_date argument to be 'most_recent' or 'first'. relative_date was: {}".format(relative_date))
  
        # Perform reduceRegion
        reducer_dict = asset.reduceRegion(reducer = reducer_type, geometry = gee_feature.geometry(), scale = scale).getInfo()

        if len(reducer_dict) > len(bands):
          # Make df from reducer output and clean up
          df = pd.DataFrame(list(reducer_dict.items()), columns = ['variable', 'value'])
          df['date'] = [item.replace('-', '_').split('_')[:-1] for item in df['variable'].values]
          df['date'] = [pd.to_datetime('-'.join(item[0:3])) for item in df['date'].values]
          df['band'] = [item.split('_')[-1] for item in df['variable'].values]
          df['value_raw'] = df['value']
          old_bandnames = [item.split('_')[-1] for item in df['variable'].values][0:len(bands)] #save for renaming bands

          # Calculate temporal gaps between data and interpolate
          date0 = df[df['band'] == df.band.unique()[0]]['date'][0]
          date1 = df[df['band'] == df.band.unique()[0]]['date'][len(df.band.unique())]
          date_range = date1-date0
          df = interp_daily(df)
          print('\tOriginal timestep of ' + str(date_range.days) + ' day(s) was interpolated to daily.')
        
        else:
          df = pd.DataFrame(list(reducer_dict.items()), columns = ['variable', 'value'])
          df['band'] = df['variable']
          df['value_raw'] = df['value']
          df['date'] = pd.to_datetime(asset.get('system:time_start').getInfo(),unit='ms')
          old_bandnames = bands #save for renaming bands
        
        if new_bandnames is not None:
          if len(old_bandnames) == len(new_bandnames):
            name_dict = {k: v for k, v in zip(old_bandnames, new_bandnames)}
            df['band'] = df['band'].map(name_dict) 
          else:
            raise Exception("Make sure bands and new_bandnames are same length or leave new_bandnames as None. bands:{},  new_bandnames:{}".format(bands, new_bandnames))

        # Apply scaling factor to specified bands
        if bands_to_scale is not None:
            df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1) for value, band_value in zip(df.value.values, df.band.values)]            
            print('\t' + bands_to_scale + ' bands were scaled by ' + str(scaling_factor))

        return df
    
    

def extract(layers, gee_feature, kind, reducer_type = None, **kwargs):
    """
    Extract data at site for several assets at once. Uses extract_single_asset_for_site().

    Args:
        
        layers: pandas df with the following columns, which are the same as the arguments for extract_single_asset_for_site():
            asset_id: GEE asset identification string
            start_date: format mm/dd/yyy or similiar date format
            end_date: format mm/dd/yyyy or similiar date format
            scale (int): scale in meters for GEE reducer function
            bands (list of str): bands of GEE asset to extract
            bands_to_scale (list of str, optional): bands for which each value will be multiplied by scaling_factor.
            scaling_factor (float, optional): scaling factor to apply to all values in bands_to_scale
        gee_feature: GEE feature for region geometry
        kind (str): 'point' or 'watershed'
        reducer_type: defaults to None, in which case GEE reduceRegion reducer function is first() and mean() for points and watersheds, respectively. See GEE documentation for more available types.
        
        **kwargs (optional): 
            interp (bool): (default: True), currently no option to change to False.
            combine_ET_bands (bool): (default True) add ET bands to make one ET band.
            bands_to_combine (list of str): (default [Es, Ec]) ET bands to combine
            band_names_combined (str): (default 'ET') name of combined ET band
    Returns:
        self: with added attribute self.extracted_data (i.e. df), self.available_data, self.layers_info, self.start_date, self.end_date
        df: long-style pandas df of extracted df.
    """
    # Read in existing csv for typical inputs
    if layers == 'all' or layers == 'minimal':
        layers = pd.read_csv('data/input/' + layers + '.csv')
  
    # Otherewise take in dataframe as layers and continue cleaning
    layers = layers.replace({np.nan: None})

    # Turn df entries into suitable formats
    def process_bandnames(row):
      bands = [i.split(',') for i in [row.bands]][0] # Make list of strings from string
      bands = [i.replace(" ", "") for i in bands] # Remove any spaces
      if row.new_bandnames is not None:
        new_bandnames = [i.split(',') for i in [row.new_bandnames]][0] # Make list of strings from string
        new_bandnames = [i.replace(" ", "") for i in new_bandnames] # Remove any spaces
        message = '\tBands {} renamed to {}.'.format(row.bands, row.new_bandnames)
        print(message)
      else: new_bandnames = None
      return bands, new_bandnames

    # Initialize return dfs
    df = pd.DataFrame(columns = ['date']) 
    df_image = pd.DataFrame()
    for row in layers.itertuples():
      print('Extracting', row.name)
      bands, new_bandnames = process_bandnames(row)
      single_asset = extract_basic(gee_feature, kind, asset_id = row.asset_id, scale = row.scale, bands = bands, start_date = row.start_date, end_date = row.end_date, relative_date = row.relative_date, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor, reducer_type = reducer_type, new_bandnames = new_bandnames)
      single_asset['asset_name'] = row.name
      single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
      
      # Append to correct df (daily or single asset)
      if row.relative_date is None:
          df = pd.concat([df, single_asset_propogate], ignore_index=True)
      else:
          df_image = pd.concat([df_image, single_asset_propogate], ignore_index=True)

    # Combine ET bands if specified
    if kwargs['combine_ET_bands']:
        df = combine_bands(df, kwargs['bands_to_combine'], kwargs['band_name_final'])
    return df, df_image


