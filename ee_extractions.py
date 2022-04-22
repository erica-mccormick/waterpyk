
import sys
from unicodedata import name
from xxlimited import Xxo
import geopandas as gpd
import urllib
import json
import ee
import pandas as pd
import numpy as np
ee.Initialize()

class StudyArea:
    def __init__(self, coords):
        """Coords = [lat/long] for Site or [gage] for Watershed."""
        self.coords = coords
        
    def get_feature(self):
        """Convert coords to GEE feature."""
        lat = self.coords[0]
        long = self.coords[1]
        feature = ee.Feature(ee.Geometry.Point(long, lat))
        #fc = ee.FeatureCollection([feature])
        return feature

        
    def extract_asset(self, asset_id, start_date, end_date, scale, bands, bands_to_scale = None, scaling_factor = 1, file_path = '/content/drive/MyDrive', file_name = None, reducer_type = ee.Reducer.first(), **reducer_kwargs):
        ft = StudyArea.get_feature(self)
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date).select(bands)
        assetband = asset.toBands()
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = ft.geometry(), scale = scale, **reducer_kwargs)
        # Make df from reducer output, format, and apply scaling factor to specified columns
        df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
        df['date'] = [item.replace('-', '_').split('_')[:-1] for item in df['variable'].values]
        df['date'] = [pd.to_datetime('-'.join(item[0:3])) for item in df['date'].values]
        df['band'] = [item.split('_')[-1] for item in df['variable'].values]
        df['value_raw'] = df['value']

        if bands_to_scale is not None:
            df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1) for value, band_value in zip(df.value.values, df.band.values)]            
        
        df['value'] = df['value'].interpolate()
        
        if file_name is not None:
            save_path = file_path + file_name + '.csv'
            with open(save_path, 'w') as f:
                df.to_csv(f)
            print('Extraction saved to', save_path)
            
        return df
    
class Site(StudyArea):
    pass

class Watershed(StudyArea):

    def get_feature(self):
        """Convert coords to GEE feature.
        Urllib.request is used to access
        the exterior coordinates of the watershed on the USGS website.
        """
        watershed = self.coords[0]
        url = 'https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/basin?f=json'%watershed
        sites = gpd.read_file(url)    
        request = urllib.request.urlopen("https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/?f=json"%watershed)
        site_name = [json.load(request)['features'][0]['properties']['name'].title()]
        flowlines = gpd.read_file('https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/navigation/UM/flowlines?f=json&distance=1000'%watershed)
        print('USGS Basin imported at ' + site_name[0] + 'CRS: ' + str(sites.crs))
        #print('\nGeometry extracted from:\n', url)
        poly_coords = [item for item in sites.geometry[0].exterior.coords]
        feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords), {'Name': str(site_name[0]), 'Gage':int(watershed)})
        #fc = ee.FeatureCollection([feature])
        return feature

    def extract_asset(self, asset_id, start_date, end_date, scale, bands, bands_to_scale = None, scaling_factor = 1, file_path = '/content/drive/MyDrive', file_name = None, reducer_type = ee.Reducer.first(), **reducer_kwargs):
        ft = Watershed.get_feature(self)
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date).select(bands)
        assetband = asset.toBands()
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = ft.geometry(), scale = scale, **reducer_kwargs)
        # Make df from reducer output, format, and apply scaling factor to specified columns
        df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
        df['date'] = [item.replace('-', '_').split('_')[:-1] for item in df['variable'].values]
        print(df['date'])
        df['date'] = [pd.to_datetime('-'.join(item[0:3])) for item in df['date'].values]
        print(df['date'])
        df['band'] = [item.split('_')[-1] for item in df['variable'].values]
        df['value_raw'] = df['value']

        if bands_to_scale is not None:
            df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1) for value, band_value in zip(df.value.values, df.band.values)]            
        
        df['value'] = df['value'].interpolate()
        
        if file_name is not None:
            save_path = file_path + file_name + '.csv'
            with open(save_path, 'w') as f:
                df.to_csv(f)
            print('Extraction saved to', save_path)
            
        return df

    
 
# Test
coords1 = [11475560]
coords2 = [39.7273, -123.6433]
rivendell = StudyArea(coords2)
elder = Watershed(coords1)
#feat = rivendell.get_feature()

#asset_id = 'projects/pml_evapotranspiration/PML/OUTPUT/PML_V2_8day_v016'
#start_date = '2005-05-31'
#end_date = '2005-10-01'
#bands = ['Es', 'Ec', 'Ei']
#scale = 500
#bands_to_scale = ['Es', 'Ec']
#scaling_factor = 0.01
#file_name = 'test_elder_pml'
#file_path = ''




def make_combined_df(study_area, layers_csv_path, export_csv_path = None):
    """Import a csv with assets to export a df with all extracted values for a StudyArea.
    The csv needs headings: name, asset_id, start_date, end_date, scale, bands_to_scale, scaling_factor.
    """
    layers = pd.read_csv(layers_csv_path)
    layers = layers.replace({np.nan: None})
    df = pd.DataFrame(columns = ['date'])
    for row in layers.itertuples():
        print('Extracting', row.name)
        bands = [i.split(',') for i in [row.bands]][0] # Make list of strings from string
        bands = [i.replace(" ", "") for i in bands] # Remove any spaces
        single_asset = study_area.extract_asset(row.asset_id, pd.to_datetime(row.start_date), pd.to_datetime(row.end_date), row.scale, bands, row.bands_to_scale, row.scaling_factor)#, row.file_path, row.file_name)
        single_asset['asset_name'] = row.name
        single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
        df = df.append(single_asset_propogate)
    if export_csv_path is not None:
        with open(export_csv_path, 'w') as f:
            df.to_csv(f)
        print('Extraction saved to', export_csv_path)             
    return df


layers_csv_path = 'layers_short_contemporary_2021.csv'
export_csv_path = 'test_merged_rivendell.csv'

df = make_combined_df(rivendell, layers_csv_path, export_csv_path)
print(df.head())
print(df.tail())
#reducer_type = ee.Reducer.mean()

#df = elder.extract_asset(asset_id = asset_id, start_date = start_date, end_date = end_date,
#                       scale = scale, bands = bands, bands_to_scale = bands_to_scale, scaling_factor = scaling_factor, file_path = file_path, file_name = file_name)

#df = elder.extract_asset(asset_id, start_date, end_date, scale, bands, bands_to_scale, scaling_factor, file_path, file_name)
#df.head()