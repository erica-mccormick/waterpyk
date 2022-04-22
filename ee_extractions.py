
import sys
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

        
    def extract_asset(self, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, file_path = '/content/drive/MyDrive', file_name = None, reducer_type = ee.Reducer.first(), **reducer_kwargs):
        ft = StudyArea.get_feature(self)
        ft.getInfo()
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date)
        if bands is not None: asset = asset.select(bands)
        assetband = asset.toBands()
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = ft.geometry(), scale = scale, **reducer_kwargs)
        print(reducer_dict.getInfo())
        # Make df from reducer output, format, and apply scaling factor to specified columns
        df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
        df['date'] = [pd.to_datetime(item.split('_')[0]) for item in df['variable'].values]
        df['band'] = [item.split('_')[1] for item in df['variable'].values]
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


    def extract_asset(self, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, file_path = '/content/drive/MyDrive', file_name = None, reducer_type = ee.Reducer.first(), **reducer_kwargs):
            ft = Watershed.get_feature(self)
            ft.getInfo()
            asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date)
            if bands is not None: asset = asset.select(bands)
            assetband = asset.toBands()
            reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = ft.geometry(), scale = scale, **reducer_kwargs)
            print(reducer_dict.getInfo())
            # Make df from reducer output, format, and apply scaling factor to specified columns
            df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
            df['date'] = [pd.to_datetime(item.split('_')[0]) for item in df['variable'].values]
            df['band'] = [item.split('_')[1] for item in df['variable'].values]
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
        

    
    
# TO DO      
# Get a bounding box for faster extraction.

# Test
coords1 = [11475560]
coords2 = [39.7273, -123.6433]
rivendell = StudyArea(coords2)
elder = Watershed(coords1)
#feat = rivendell.get_feature()

asset_id = 'projects/pml_evapotranspiration/PML/OUTPUT/PML_V2_8day_v016'
start_date = '2005-05-31'
end_date = '2005-10-01'
bands = ['Es', 'Ec', 'Ei']
scale = 500
bands_to_scale = ['Es', 'Ec']
scaling_factor = 0.01
file_name = 'test_elder_pml'
file_path = ''
reducer_type = ee.Reducer.mean()

df = elder.extract_asset(asset_id = asset_id, start_date = start_date, end_date = end_date,
                        scale = scale, bands = bands, bands_to_scale = bands_to_scale, scaling_factor = scaling_factor, file_path = file_path, file_name = file_name)

df.head()