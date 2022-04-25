
import geopandas as gpd
import urllib
import json
import ee
import pandas as pd
import numpy as np
import datetime
import warnings
warnings.filterwarnings("ignore")
ee.Initialize()

class StudyArea:

    def get_kind(self):
        self.kind = np.where(len(self.coords)>1, 'point', 'watershed')
        return self

    def get_feature(self):
        """Convert coords to GEE feature.
        For a point, use lat/long. For a watershed, supply one coord equivelant
        to the USGS gage ID.
        """
        if self.kind == 'point':
            lat = self.coords[0]
            long = self.coords[1]
            feature = ee.Feature(ee.Geometry.Point(long, lat))
            url = 'No url for points'
            #description = 'Site at coordinates ' + str(lat) + ', ' + str(long) + '.'
            description = 'Site'
        elif self.kind == 'watershed':
            watershed = self.coords[0]
            url = 'https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/basin?f=json'%watershed
            sites = gpd.read_file(url)    
            request = urllib.request.urlopen("https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/?f=json"%watershed)
            site_name = [json.load(request)['features'][0]['properties']['name'].title()]
            flowlines = gpd.read_file('https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/navigation/UM/flowlines?f=json&distance=1000'%watershed)
            description = 'USGS Basin (' +str(watershed)+ ') imported at ' + site_name[0] + 'CRS: ' + str(sites.crs)
            #print('\nGeometry extracted from:\n', url)
            poly_coords = [item for item in sites.geometry[0].exterior.coords]
            feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords), {'Name': str(site_name[0]), 'Gage':int(watershed)})
            #flowline_coords = [item for item in flowlines.geometry[0].exterior.coords]
            #flowine_feature = ee.Feature(ee.Geometry.Polygon(coords = flowline_coords))
        self.site_feature = feature
        self.url = url
        self.description = description
        return self, feature

    def extract_asset(self, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, reducer_type = None):
        """Extract data from start_date to end_date for an asset_id."""
        StudyArea.get_feature(self)
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date)
        if bands is not None: asset = asset.select(bands)
        assetband = asset.toBands()
        if self.kind == 'point':
            reducer_type = ee.Reducer.first()
        elif self.kind == 'watershed':
            reducer_type = ee.Reducer.mean()
       # else:
       #     reducer_type = reducer_type
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = self.site_feature.geometry(), scale = scale)
        
        # Make df from reducer output, format, and apply scaling factor to specified columns
        df = pd.DataFrame(list(reducer_dict.getInfo().items()), columns = ['variable', 'value'])
        df['date'] = [item.replace('-', '_').split('_')[:-1] for item in df['variable'].values]
        df['date'] = [pd.to_datetime('-'.join(item[0:3])) for item in df['date'].values]
        df['band'] = [item.split('_')[-1] for item in df['variable'].values]
        df['value_raw'] = df['value']
        if bands_to_scale is not None:
            df['value'] = [value * np.where(band_value in bands_to_scale, scaling_factor, 1) for value, band_value in zip(df.value.values, df.band.values)]            
        
        # Calculate gaps between data and interpolate
        date0 = df[df['band'] == df.band.unique()[0]]['date'][0]
        date1 = df[df['band'] == df.band.unique()[0]]['date'][len(df.band.unique())]
        date_range = date1-date0
        #if interp == None:
        df = interp_columns_daily(df)
        print('\tTimestep of', date_range.days, 'days was interpolated to daily.')
        #else: print('Timestep of', date_range, 'was not interpolated.')
        return df
    

    def make_combined_df(self, layers, **kwargs):
        """import_asset requires EITHER the path to a csv or a df.
        The columns need headings: name, asset_id, start_date, end_date,
        scale, bands_to_scale, scaling_factor.
        """
        
        layers = layers.replace({np.nan: None})
        df = pd.DataFrame(columns = ['date'])
        for row in layers.itertuples():
            print('Extracting', row.name)
            bands = [i.split(',') for i in [row.bands]][0] # Make list of strings from string
            bands = [i.replace(" ", "") for i in bands] # Remove any spaces
            single_asset = StudyArea.extract_asset(self, asset_id = row.asset_id, start_date = pd.to_datetime(row.start_date), end_date = pd.to_datetime(row.end_date), scale = row.scale, bands = bands, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor)#, row.file_path, row.file_name)
            single_asset['asset_name'] = row.name
            single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
            df = df.append(single_asset_propogate)   
            
        if kwargs['combine_ET_bands'] == True:
            df = combine_bands(df, **kwargs)
 
        self.extracted_data = df
        self.available_data = df.band.unique()
        self.layers_info = layers
        self.start_date = layers.start_date[0]
        self.end_date = layers.end_date[0]
        return self, df


    def calculate_deficit(self, layers, **kwargs):
        """Calculate D(t) after McCormick et al., 2021 and Dralle et al., 2020."""
        
        StudyArea.make_combined_df(self, layers, **kwargs)
        df = self.extracted_data
        
        # Re-organize df
        et_df = df[df['asset_name'] == kwargs['et_asset']]
        et_df = et_df[et_df['band'] == kwargs['et_band']]
        et_df['ET'] = et_df['value']
        ppt_df = df[df['asset_name'] == kwargs['ppt_asset']]
        ppt_df = ppt_df[ppt_df['band'] == kwargs['ppt_band']]
        ppt_df['P'] = ppt_df['value']
        df_def = et_df.merge(ppt_df, how = 'inner', on = 'date')[['date', 'ET', 'P']]
        if kwargs['snow_correction'] == True:
            snow_df = df[df['asset_name'] == 'modis_snow']
            snow_df = snow_df[snow_df['band'] == 'Cover']
            snow_df['Snow'] = snow_df['value']
            df_def = df_def.merge(snow_df, how = 'inner', on = 'date')[['date','ET','P','Snow']]
            df_def.loc[df_def['Snow'] > kwargs['snow_frac'], 'ET'] = 0
        # Calculate A and D
        df_def['A'] = df_def['ET'] - df_def['P']
        df_def['D'] = 0
        for _i in range(df_def.shape[0]-1):
            df_def.loc[_i+1, 'D'] = max((df_def.loc[_i+1, 'A'] + df_def.loc[_i, 'D']), 0)
        
        self.deficit_timeseries = df_def
        self.smax = df_def.D.max()
        return self, df_def
    
    def describe(self):
        print('\n'+self.description)
        try:
            print('Available data for this site:', self.available_data)
            print('Smax = ' + str(round(self.smax)) + ' mm')
            print('Deficit calculation parameters:\n\tDataset: ' + str(self.et_asset) + '\n\tBands: ' + str(self.et_bands))
            print('\tStart date: ' + self.start_date + '\n\tEnd date: ' + self.end_date)
        except:
            print('Data has not been extracted for this site.')

    def __init__(self, coords, layers = None, **kwargs):
        """Coords = [lat/long] for Site or [gage] for Watershed."""
        self.coords = coords
        self.get_kind()
        self.get_feature()
        if layers is not None:
            default_kwargs = {
                'interp': True,
                'combine_ET_bands': True,
                'bands_to_combine': ['Es', 'Ec'],
                'band_names_combined': 'ET',
                'et_asset': 'pml',
                'et_band': 'ET',
                'ppt_asset': 'prism',
                'ppt_band': 'ppt',
                'snow_correction': True,
                'snow_frac': 10
                }
            kwargs = { **default_kwargs, **kwargs}
            self.make_combined_df(layers, **kwargs)
            self.calculate_deficit(layers, **kwargs)
            self.et_asset = kwargs['et_asset']
            if kwargs['combine_ET_bands'] == True:
                self.et_bands = kwargs['bands_to_combine']
            else: self.et_bands = 'Not combined'
        
        
        


## HELPER FUNCTIONS ##
def interp_columns_daily(df):
    """Interpolate all data to daily."""
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

def combine_bands(df, **kwargs) :
    """Defaults to add together soil and vegetation ET bands (Es and Ec) for PML to create ET band.
    Can be customized to add any bands together to create a new band.
    """
    to_store = pd.DataFrame()
    for i in kwargs['bands_to_combine']:
        if i == kwargs['bands_to_combine'][0]:
            to_store = df[df['band'] == i]
            to_store['value_raw'] = np.nan
        else:
            subset = df[df['band']==i][['date', 'value']]
            to_store = to_store.merge(subset, how = 'inner', on = 'date')
    val_cols = to_store.loc[:,to_store.columns.str.startswith("value")]
    to_store['value'] = val_cols.sum(axis=1)
    to_store['band'] = kwargs['band_names_combined']
    to_store = to_store[['date', 'asset_name', 'value', 'band', 'value_raw']]
    df = df.append(to_store)
    df = df.reset_index(drop=True)
    return df
