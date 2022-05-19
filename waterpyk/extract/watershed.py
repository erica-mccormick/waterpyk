import geopandas as gpd
import urllib
import json
import ee
ee.Initialize()
import pandas as pd

def access_data(gage, **kwargs):
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
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = access_data(gage)
    # Access site geometry
    basin_geometry = gpd.read_file(url_basin_geometry)   
    poly_coords = [item for item in basin_geometry.geometry[0].exterior.coords]
    gee_feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords))#, {'Name': str(site_name[0]), 'Gage':int(watershed)})

    return gee_feature, basin_geometry



def metadata(gage):
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = access_data(gage)
    request_metadata = urllib.request.urlopen(url_metadata)
    basin_geometry = gpd.read_file(url_basin_geometry) # for CRS 
    site_name = [json.load(request_metadata)['features'][0]['properties']['name'].title()]
    description = 'USGS Basin (' +str(gage)+ ') imported at ' + str(site_name[0]) + 'CRS: ' + str(basin_geometry.crs)
    
    return site_name, description

def streamflow(gage, **kwargs):
    # get URLs and basin geometry
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = access_data(gage)
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
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = access_data(gage)
    flowling_geometry = gpd.read_file(url_flow_geometry)
    
    return flowline_geometry

def latitude(gage):
    url_basin_geometry, url_flow_geometry, url_metadata, url_flow = access_data(gage)
    basin_geometry = gpd.read_file(url_basin_geometry) 
    latitude = basin_geometry.to_crs('epsg:4326').geometry[0].centroid.y
    
    return latitude