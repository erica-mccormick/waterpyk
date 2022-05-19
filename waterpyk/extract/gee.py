import ee
ee.Initialize()
import pandas as pd
import numpy as np
import datetime

def extract_single_asset_at_site(gee_feature, kind, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, reducer_type = None):
        """
        Extract data from start_date to end_date for an asset_id.

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
        # Select asset with ID and start/end dates
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date)
        
        # Select bands of interest and convert ImageCollection to Image with bands for each timestep/band combination
        if bands is not None: asset = asset.select(bands)
        assetband = asset.toBands()
        
        # Set reducer type based on kind (watershed or point)
        if reducer_type is None:
            if kind == 'point':
                reducer_type = ee.Reducer.first()
            elif kind == 'watershed':
                reducer_type = ee.Reducer.mean()
    
        # Perform reduceRegion
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = gee_feature.geometry(), scale = scale)
        
        # Make df from reducer output and clean up
        df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
        df['date'] = [item.replace('-', '_').split('_')[:-1] for item in df['variable'].values]
        df['date'] = [pd.to_datetime('-'.join(item[0:3])) for item in df['date'].values]
        df['band'] = [item.split('_')[-1] for item in df['variable'].values]
        df['value_raw'] = df['value']
        
        # Apply scaling factor to specified bands
        if bands_to_scale is not None:
            df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1) for value, band_value in zip(df.value.values, df.band.values)]            
            print('\t' + bands_to_scale + ' bands were scaled by ' + str(scaling_factor))
        # Calculate temporal gaps between data and interpolate
        date0 = df[df['band'] == df.band.unique()[0]]['date'][0]
        date1 = df[df['band'] == df.band.unique()[0]]['date'][len(df.band.unique())]
        date_range = date1-date0

        df = interp_columns_daily(df)
        print('\tTimestep of', date_range.days, 'days was interpolated to daily.')
        return df
    
def extract_assets_at_site(layers, gee_feature, kind, reducer_type = None, **kwargs):
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
    layers = layers.replace({np.nan: None})
    df = pd.DataFrame(columns = ['date'])
    for row in layers.itertuples():
        print('Extracting', row.name)
        bands = [i.split(',') for i in [row.bands]][0] # Make list of strings from string
        bands = [i.replace(" ", "") for i in bands] # Remove any spaces
        single_asset = extract_single_asset_at_site(gee_feature, kind, asset_id = row.asset_id, start_date = pd.to_datetime(row.start_date), end_date = pd.to_datetime(row.end_date), scale = row.scale, bands = bands, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor, reducer_type = reducer_type)#, row.file_path, row.file_name)
        single_asset['asset_name'] = row.name
        single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
        df = df.append(single_asset_propogate)   
        
    if kwargs['combine_ET_bands'] == True:
        df = combine_bands(df, kwargs['bands_to_combine'], kwargs['band_name_final'])

    return df


######## CLEANING DATAFRAME ########

def interp_columns_daily(df):
    """Interpolate all data to daily.
        Args:
            df: initial long-form dataframe for a single asset (may contain multiple bands) with column 'value' for interpolating
        Returns:
            df_interp: pandas dataframe with 'value' column containing daily interpolated daily 
    """
    df_interp = pd.DataFrame()
    temp = pd.DataFrame()
    diff_days = (df.date.max() - df.date.min()).days
    temp['date'] = [df.date.min() + datetime.timedelta(days=x) for x in range(0, diff_days)]
    for i in df.band.unique():
        df_temp = df[df['band']==i]
        df_temp = df_temp.merge(temp, how = 'right', on = 'date')
        df_temp['value'] = df_temp['value'].interpolate(method = "linear")
        df_temp['band'] = i
        df_interp = df_interp.append(df_temp)
    return df_interp

def combine_bands(df, bands_to_combine, band_name_final):
    """
    Defaults to add together soil and vegetation ET bands (Es and Ec) for PML to create ET band.
    Can be customized to add any bands together to create a new band.
    
    Args:
        bands_to_combine (list of str): list of strings of band names (example: ['Es', 'Ec']) to combine into a single band
        band_name_final (str): the final band name to be stored in the 'band' column of the final dataframe, where the 'value' column will contain the added values from bands_to_combine
    
    Returns:
       df:  input long-form dataframe with appended section which contains date, asset_name, value, band, and value_raw (set to np.nan) columns with data from combined
    """
    to_store = pd.DataFrame()
    for i in bands_to_combine:
        if i == bands_to_combine[0]:
            to_store = df[df['band'] == i]
            to_store['value_raw'] = np.nan
        else:
            subset = df[df['band']==i][['date', 'value']]
            to_store = to_store.merge(subset, how = 'inner', on = 'date')
    val_cols = to_store.loc[:,to_store.columns.str.startswith("value")]
    to_store['value'] = val_cols.sum(axis=1)
    to_store['band'] = band_name_final
    to_store = to_store[['date', 'asset_name', 'value', 'band', 'value_raw']]
    df = df.append(to_store)
    df = df.reset_index(drop=True)
    return df

