import geopandas as gpd
import urllib
import json
import ee
ee.Initialize()
import pandas as pd
import numpy as np
from waterpyk.calcs import interp_daily, combine_bands

####### USGS API #######
def watershed_urls(gage, **kwargs):
    """
    Return relevant urls for a USGS gage.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
        **kwargs: flow_start_date (default: '1980-10-01') and flow_end_date (default: '2021-10-01').

    Returns:
        str: 4 URLS, (1) to access basin lat/long geometry. (2) to access geometry of flowline (i.e. rivers) lat/long geometry. (3) to access basin metadata. (4) to access basin discharge timeseries (between the dates of **kwargs).
    """
    # Default start_date and end_date kwargs
    default_kwargs = {
        'flow_start_date':'1980-10-01',
        'flow_end_date':'2021-10-01',
    }
    kwargs = {**default_kwargs, **kwargs}

    # Make sure gage ID is in correct format without missing starting 0s
    gage = str(gage)
    if (len(gage) < 8):
        num = 8 - len(gage)
        gage = '0' * num + gage

    # Data URLs
    url_basin_geometry = 'https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/basin?f=json'%gage
    url_flow_geometry = 'https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/navigation/UM/flowlines?f=json&distance=1000'%gage
    url_metadata = "https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/?f=json"%gage
    url_flow = 'https://waterdata.usgs.gov/nwis/dv?cb_00060=on&format=rdb&site_no=' + gage + '&referred_module=sw&period=&begin_date='+ kwargs['flow_start_date'] +'&end_date='+ kwargs['flow_end_date']
    
    return url_basin_geometry, url_flow_geometry, url_metadata, url_flow

def watershed_geometry(gage):
    """
    Get the geometry of a USGS gage in Google Earth Engine (GEE) form and as a geopandas dataframe.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
    
    Returns:
        :obj:`feature` and  :obj:`gdf`: GEE feature containing the basin's exterior polygon coordinates and geopandas dataframe containing the basin's coordinates.
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = watershed_urls(gage)
    # Access site geometry
    basin_geometry = gpd.read_file(url_basin_geometry)   
    poly_coords = [item for item in basin_geometry.geometry[0].exterior.coords]
    gee_feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords))#, {'Name': str(site_name[0]), 'Gage':int(watershed)})

    return gee_feature, basin_geometry



def watershed_metadata(gage):
    """
    Get metadata for a USGS gage.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
    
    Returns:
        str: 2 strings: (1) USGS long-name of gage. (2) description of the form 'USGS Basin + gage ID + imported at + site_name + CRS: + coordinate system
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = watershed_urls(gage)
    request_metadata = urllib.request.urlopen(url_metadata)
    basin_geometry = gpd.read_file(url_basin_geometry) # for CRS 
    site_name = [json.load(request_metadata)['features'][0]['properties']['name'].title()]
    description = 'USGS Basin (' +str(gage)+ ') imported at ' + str(site_name[0]) + 'CRS: ' + str(basin_geometry.crs)
    
    return site_name, description

def watershed_streamflow(gage, **kwargs):
    """
    Get a dataframe with streamflow (i.e. discharge) for a USGS gage. Units are converted to mm using the area of the basin, calculated from the exterior geometry.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
        **kwargs: flow_start_date (default: '1980-10-01') and flow_end_date (default: '2021-10-01').

    Returns:
        :obj:`df`: dataframe with daiy discharge (Q) in units of cfs, m3/day, m, and mm.
    """
    # get URLs and basin geometry
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = watershed_urls(gage)
    print('\nStreamflow data is being retrieved from:', url_flow_geometry, '\n') 
    basin_geometry = gpd.read_file(url_basin_geometry) # for drainage area
    drainage_area_m2 = basin_geometry.to_crs('epsg:26910').geometry.area 

    # read streamflow data and clean csv
    df = pd.read_csv(url_flow, header=31, delim_whitespace=True)
    df.columns = ['usgs', 'site_number', 'datetime', 'Q_cfs', 'a'] 
    df['date'] = pd.to_datetime(df.datetime)
    df = df[['Q_cfs','date']]
    
    # Convert Q to m^2 using drainage area
    df['Q_cfs'] = df['Q_cfs'].astype(float, errors='ignore')  #this is needed because sometimes there are non-numeric entries and we want to ignore them
    df['Q_m3day']= (86400*df['Q_cfs'])/(35.31) #m3/day
    df['Q_m'] = df['Q_m3day'] / float(drainage_area_m2)
    df['Q_mm'] = df['Q_m3day'] / float(drainage_area_m2) * 1000
    
    return df

def watershed_geometry_flowline(gage):
    """
    Get geopandas dataframe of USGS basin flowline geometry for plotting.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.

    Returns:
        :obj:`df`: geopandas dataframe with geometry of flowlines (rivers) for plotting.
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = watershed_urls(gage)
    geometry_df = gpd.read_file(url_flow_geometry)
    
    return geometry_df

def watershed_latitude(gage):
    """
    Get the latitude of the centroid of the USGS gage for calculating PET.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.

    Returns:
        float: latitude
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = watershed_urls(gage)
    basin_geometry = gpd.read_file(url_basin_geometry) 
    latitude = basin_geometry.to_crs('epsg:4326').geometry[0].centroid.y
    
    return latitude


##### GEE API ######
def gee_extract_basic(gee_feature, kind, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, reducer_type = None):
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

        df = interp_daily(df)
        print('\tTimestep of', date_range.days, 'days was interpolated to daily.')
        return df
    

def gee_extract(layers, gee_feature, kind, reducer_type = None, **kwargs):
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
        single_asset = gee_extract_basic(gee_feature, kind, asset_id = row.asset_id, start_date = pd.to_datetime(row.start_date), end_date = pd.to_datetime(row.end_date), scale = row.scale, bands = bands, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor, reducer_type = reducer_type)#, row.file_path, row.file_name)
        single_asset['asset_name'] = row.name
        single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
        df = df.append(single_asset_propogate)   
        
    if kwargs['combine_ET_bands'] == True:
        df = combine_bands(df, kwargs['bands_to_combine'], kwargs['band_name_final'])

    return df

"""
def extract_longterm_p(gee_feature, kind):
    asset_id = "OREGONSTATE/PRISM/AN81m"
    start_date = '1980-10-01'
    end_date = '2020-10-01'
    scale = 500
    bands = 'ppt'
    df = extract_single_asset_at_site(gee_feature, kind, asset_id, start_date, end_date, bands, scale)
    return df
"""
