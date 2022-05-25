import geopandas as gpd
import urllib
import json
import ee
ee.Initialize()
import pandas as pd

def urls(gage, **kwargs):
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

def geometry(gage):
    """
    Get the geometry of a USGS gage in Google Earth Engine (GEE) form and as a geopandas dataframe.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
    
    Returns:
        :obj:`feature` and  :obj:`gdf`: GEE feature containing the basin's exterior polygon coordinates and geopandas dataframe containing the basin's coordinates.
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = urls(gage)
    # Access site geometry
    basin_geometry = gpd.read_file(url_basin_geometry)   
    poly_coords = [item for item in basin_geometry.geometry[0].exterior.coords]
    gee_feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords))#, {'Name': str(site_name[0]), 'Gage':int(watershed)})

    return gee_feature, basin_geometry



def metadata(gage):
    """
    Get metadata for a USGS gage.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
    
    Returns:
        str: 2 strings: (1) USGS long-name of gage. (2) description of the form 'USGS Basin + gage ID + imported at + site_name + CRS: + coordinate system
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = urls(gage)
    request_metadata = urllib.request.urlopen(url_metadata)
    basin_geometry = gpd.read_file(url_basin_geometry) # for CRS 
    site_name = [json.load(request_metadata)['features'][0]['properties']['name'].title()]
    description = 'USGS Basin (' +str(gage)+ ') imported at ' + str(site_name[0]) + 'CRS: ' + str(basin_geometry.crs)
    
    return site_name, description

def streamflow(gage, **kwargs):
    """
    Get a dataframe with streamflow (i.e. discharge) for a USGS gage. Units are converted to mm using the area of the basin, calculated from the exterior geometry.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.
        **kwargs: flow_start_date (default: '1980-10-01') and flow_end_date (default: '2021-10-01').

    Returns:
        :obj:`df`: dataframe with daiy discharge (Q) in units of cfs, m3/day, m, and mm.
    """
    # get URLs and basin geometry
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = urls(gage)
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

def flowline_geometry(gage):
    """
    Get geopandas dataframe of USGS basin flowline geometry for plotting.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.

    Returns:
        :obj:`df`: geopandas dataframe with geometry of flowlines (rivers) for plotting.
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = urls(gage)
    geometry_df = gpd.read_file(url_flow_geometry)
    
    return geometry_df

def latitude(gage):
    """
    Get the latitude of the centroid of the USGS gage for calculating PET.
    
    Args:
        gage (str or int): USGS 8-number gage ID. If int, leading 0s will automatically be added.

    Returns:
        float: latitude
    """
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = urls(gage)
    basin_geometry = gpd.read_file(url_basin_geometry) 
    latitude = basin_geometry.to_crs('epsg:4326').geometry[0].centroid.y
    
    return latitude