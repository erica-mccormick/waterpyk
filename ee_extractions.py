
import geopandas as gpd
import urllib
import json
import ee
import pandas as pd
import numpy as np
ee.Initialize()

class StudyArea:
    def __init__(self, coords, kind):
        """Coords = [lat/long] for Site or [gage] for Watershed."""
        self.coords = coords
        self.kind = kind
        
    def adding_new_attr(self, attr):
        """Function to add a new attribute to the class."""
        setattr(self, attr, attr)
        
    #def _set_kind(self):
    #    self._kind = np.where(len(self.coords)>1, 'point', 'watershed')
        
    def get_feature(self):
        """Convert coords to GEE feature.
        For a point, use lat/long. For a watershed, supply one coord equivelant
        to the USGS gage ID.
        """
        if self.kind == 'point':
            lat = self.coords[0]
            long = self.coords[1]
            feature = ee.Feature(ee.Geometry.Point(long, lat))
        elif self.kind == 'watershed':
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
        setattr(self, "site_feature", feature)
        return feature

    def extract_asset(self, asset_id, start_date, end_date, scale, bands, bands_to_scale = None, scaling_factor = 1, file_path = '/content/drive/MyDrive', file_name = None, interp = True, reducer_type = ee.Reducer.first(), **reducer_kwargs):
        StudyArea.get_feature(self)
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date).select(bands)
        assetband = asset.toBands()
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = self.site_feature.geometry(), scale = scale, **reducer_kwargs)
        # Make df from reducer output, format, and apply scaling factor to specified columns
        df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
        print(df.head())
        df['date'] = [item.replace('-', '_').split('_')[:-1] for item in df['variable'].values]
        df['date'] = [pd.to_datetime('-'.join(item[0:3])) for item in df['date'].values]
        df['band'] = [item.split('_')[-1] for item in df['variable'].values]
        df['value_raw'] = df['value']
        if bands_to_scale is not None:
            df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1) for value, band_value in zip(df.value.values, df.band.values)]            
        
       # if interp:
       #     if df['date'][1] - df['date'][0]
            
        #df['value'] = df['value'].interpolate()
        if file_name is not None:
            save_path = file_path + file_name + '.csv'
            with open(save_path, 'w') as f:
                df.to_csv(f)
            print('Extraction saved to', save_path)
        return df
    

    def make_combined_df(self, import_assets, export_csv_path = None):
        """import_asset requires EITHER the path to a csv or a df.
        The columns need headings: name, asset_id, start_date, end_date,
        scale, bands_to_scale, scaling_factor.
        """
       # if type(import_assets) == str:
       #     layers = pd.read_csv(import_assets)
       #     layers = layers.replace({np.nan: None})
       # else: layers = import_assets.copy()
        layers = pd.read_csv(import_assets)
        layers = layers.replace({np.nan: None})
        df = pd.DataFrame(columns = ['date'])
        for row in layers.itertuples():
            print('Extracting', row.name)
            bands = [i.split(',') for i in [row.bands]][0] # Make list of strings from string
            bands = [i.replace(" ", "") for i in bands] # Remove any spaces
            single_asset = StudyArea.extract_asset(self, asset_id = row.asset_id, start_date = pd.to_datetime(row.start_date), end_date = pd.to_datetime(row.end_date), scale = row.scale,bands = bands, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor)#, row.file_path, row.file_name)
            single_asset['asset_name'] = row.name
            single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
            df = df.append(single_asset_propogate)            
        if export_csv_path is not None:
            with open(export_csv_path, 'w') as f:
                df.to_csv(f)
            print('Extraction saved to', export_csv_path)             
        return df

