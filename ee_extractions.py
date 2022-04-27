
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
import matplotlib
import matplotlib.pyplot as plt

class StudyArea:

    def get_kind(self):
        """
        Adds attribute of point or watershed to object.

        Args:
            self

        Returns:
            self: self with added attribute self.kind
        """
        if len(self.coords) >1:
            self.kind = 'point'
        else: self.kind = 'watershed'
        #self.kind = str(np.where(len(self.coords)>1, 'point', 'watershed'))
        return self

    def get_feature(self):
        """
        Convert coordinates to GEE feature. For a USGS watershed,
        coordinates are extracted from website using gage ID.

        Args:
            self

        Returns:
            self: self with added attributes self.kind, self.url, and self.description
            feature: GEE feature
        """
        StudyArea.get_kind(self)
        if self.kind == 'point':
            lat = self.coords[0]
            long = self.coords[1]
            feature = ee.Feature(ee.Geometry.Point(long, lat))
            url = 'No url for points'
            description = 'Site at coordinates ' + str(lat) + ', ' + str(long) + '.'
        elif self.kind == 'watershed':
            watershed = self.coords[0]
            url = 'https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/basin?f=json'%watershed
            sites = gpd.read_file(url)    
            request = urllib.request.urlopen("https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/?f=json"%watershed)
            site_name = [json.load(request)['features'][0]['properties']['name'].title()]
            flowlines = gpd.read_file('https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/navigation/UM/flowlines?f=json&distance=1000'%watershed)
            description = 'USGS Basin (' +str(watershed)+ ') imported at ' + str(site_name[0]) + 'CRS: ' + str(sites.crs)
            poly_coords = [item for item in sites.geometry[0].exterior.coords]
            feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords), {'Name': str(site_name[0]), 'Gage':int(watershed)})
        self.site_feature = feature
        self.url = url
        self.description = description
        return self, feature

    def extract_asset(self, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, reducer_type = None):
        """
        Extract data from start_date to end_date for an asset_id.

        Args:
            self
            asset_id: GEE asset identification string
            start_date: format mm/dd/yyy or similiar date format
            end_date: format mm/dd/yyyy or similiar date format
            scale (int): scale in meters for GEE reducer function
            bands (list of str): bands of GEE asset to extract
            bands_to_scale (list of str, optional): bands for which each value will be multiplied by scaling_factor.
            scaling_factor (float, optional): scaling factor to apply to all values in bands_to_scale
            reducer_type (optional): not used at this time. reducer_type defaults to first() for points and mean() for watersheds
        Returns:
            df: pandas df of all extracted data
        """
        
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
        """
        Extract data at site for several assets at once. Uses extract_asset().

        Args:
            self
            layers: pandas df with the following columns:
                asset_id: GEE asset identification string
                start_date: format mm/dd/yyy or similiar date format
                end_date: format mm/dd/yyyy or similiar date format
                scale (int): scale in meters for GEE reducer function
                bands (list of str): bands of GEE asset to extract
                bands_to_scale (list of str, optional): bands for which each value will be multiplied by scaling_factor.
                scaling_factor (float, optional): scaling factor to apply to all values in bands_to_scale
            **kwargs: 
                interp: (default: True), currently no option to change to False.
                combine_ET_bands: (default True) add ET bands to make one ET band.
                bands_to_combine: (default [Es, Ec]) ET bands to combine
                band_names_combined: (default 'ET') name of combined ET band
                et_asset: (default pml) ET dataset to use for deficit calculation, if multiple are given
                et_band: (default ET) band from ET dataset to use for deficit calculation, if multiple are given
                ppt_asset: (default prism) precipitation dataset to use for deficit calculation, if multiple are given
                ppt_band: (default ppt) precipitation dataset to use for deficit calculation, if multiple are given
                snow_correction: (default True) use snow correction factor when calculating deficit
                snow_frac: (default 10) set all ET when snow is greater than this (%) to 0 if snow_correction = True
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
            single_asset = StudyArea.extract_asset(self, asset_id = row.asset_id, start_date = pd.to_datetime(row.start_date), end_date = pd.to_datetime(row.end_date), scale = row.scale, bands = bands, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor)#, row.file_path, row.file_name)
            single_asset['asset_name'] = row.name
            single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
            df = df.append(single_asset_propogate)   
            
        if kwargs['combine_ET_bands'] == True:
            df = combine_bands(df, **kwargs)
 
        self.extracted_data = df
        self.available_data = df.band.unique()
        self.start_date = layers.start_date[0]
        self.end_date = layers.end_date[0]
        return self, df

    def long_to_wide(self, layers, **kwargs):
        """
        Uses ET and P (designated in **kwargs) to return a wide-form dataframe with columns
        date, ET, and P. Resulting df_wide is used in calculate_deficit() and wateryear().
        Self is not updated.
        
        Args:
            self
            layers
            **kwargs
        Returns:
            df_wide: df with columns date, ET and P.
        """
        try:
            df = self.extracted_data
        except:
            StudyArea.make_combined_df(self, layers, **kwargs)
            df = self.extracted_data
        et_df = df[df['asset_name'] == kwargs['et_asset']]
        et_df = et_df[et_df['band'] == kwargs['et_band']]
        et_df['ET'] = et_df['value']
        ppt_df = df[df['asset_name'] == kwargs['ppt_asset']]
        ppt_df = ppt_df[ppt_df['band'] == kwargs['ppt_band']]
        ppt_df['P'] = ppt_df['value']
        df_wide = et_df.merge(ppt_df, how = 'inner', on = 'date')[['date', 'ET', 'P']]
        #df_def = df_def.set_index(pd.to_datetime(df_def['date']))
        #df_def['wateryear'] = np.where(~df_def.index.month.isin([10,11,12]),df_def.index.year,df_def.index.year+1)
        return df_wide

    def calculate_deficit(self, layers, **kwargs):
        """
        Calculate D(t) after McCormick et al., 2021 and Dralle et al., 2020.
        Uses extract_asset() and make_combined_df().

        Args:
            self
            layers: pandas df with the following columns:
                asset_id: GEE asset identification string
                start_date: format mm/dd/yyy or similiar date format
                end_date: format mm/dd/yyyy or similiar date format
                scale (int): scale in meters for GEE reducer function
                bands (list of str): bands of GEE asset to extract
                bands_to_scale (list of str, optional): bands for which each value will be multiplied by scaling_factor.
                scaling_factor (float, optional): scaling factor to apply to all values in bands_to_scale
            **kwargs: 
                interp: (default: True), currently no option to change to False.
                combine_ET_bands: (default True) add ET bands to make one ET band.
                bands_to_combine: (default [Es, Ec]) ET bands to combine
                band_names_combined: (default ET) name of combined ET band
                et_asset: (default pml) ET dataset to use for deficit calculation, if multiple are given
                et_band: (default ET) band from ET dataset to use for deficit calculation, if multiple are given
                ppt_asset: (default prism) precipitation dataset to use for deficit calculation, if multiple are given
                ppt_band: (default ppt) precipitation dataset to use for deficit calculation, if multiple are given
                snow_correction: (default True) use snow correction factor when calculating deficit
                snow_frac: (default 10) set all ET when snow is greater than this (%) to 0 if snow_correction = True
        Returns:
            self: with added attribute self.smax (defined as max(D)) and self.deficit_timeseries (i.e. df).
            df: pandas df of deficit data where deficit is column 'D'.
        """
        df_def = StudyArea.long_to_wide(self, layers, **kwargs)
        df = self.extracted_data

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
    
    
    def wateryear(self, layers, **kwargs):
        """
        Calculate the cumulative wateryear ET and P timeseries and the wateryear totals for ET and P.
        ET and P datasets are designated in the **kwargs.

        Args:
            self
            layers
            **kwargs
        Returns:
            df_wide: df with columns date, wateryear, ET, P, ET_cumulative, P_cumulative
            df_total: df with columns wateryear, ET, and P with wateryear totals
            self: with added wateryear_timeseries and wateryear_total attributes, corresponding to df_wide and df_total
        """
        df_wide = StudyArea.long_to_wide(self, layers, **kwargs)
        df_wide = df_wide.set_index(pd.to_datetime(df_wide['date']))
        df_wide['wateryear'] = np.where(~df_wide.index.month.isin([10,11,12]),df_wide.index.year,df_wide.index.year+1)
        
        df_wide['ET_cumulative'] = df_wide.groupby(['wateryear'])['ET'].cumsum()
        df_wide['P_cumulative'] = df_wide.groupby(['wateryear'])['P'].cumsum()
        
        df_total = pd.DataFrame()
        df_total['ET'] = df_wide.groupby(['wateryear'])['ET'].sum()
        df_total['P'] = df_wide.groupby(['wateryear'])['P'].sum()
        df_total['wateryear'] = df_wide.groupby(['wateryear'])['wateryear'].first()
        self.wateryear_timeseries = df_wide
        self.wateryear_total = df_total
        self.map = df_total['P'].mean()
        
        return self, df_wide, df_total
    
    
    ########################## PLOTS ##########################
    def plot(self, kind = 'timeseries', title = '', **plot_kwargs):
        
        default_plotting_kwargs = {
            'plot_P': True,
            'plot_D': True,
            'plot_ET': False,
            'color_P': '#b1d6f0',
            'color_D': 'black',
            'color_ET': 'purple',
            'linestyle_D': '-',
            'linestyle_ET': '-',
            'xmin': '2003-10-01',
            'xmax': '2020-10-01',
            'legend': True,
            'dpi': 300,
            'figsize': (6,4),
            'xlabel': 'Date',
            'ylabel': '[mm]'

            }
        plot_kwargs = { **default_plotting_kwargs, **plot_kwargs}
        
        if kind == 'timeseries':
            fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
            if title is not None:
                ax.set_title(title)
            if plot_kwargs['plot_P']:
                df_wy = self.wateryear_timeseries
                df_wy['date'] = pd.to_datetime(df_wy['date'])
                ax.fill_between(df_wy['date'], 0, df_wy['P_cumulative'],color='#b1d6f0', label='P (mm)', alpha = 0.7)
            if plot_kwargs['plot_ET']:
                df_wy = self.wateryear_timeseries
                df_wy['date'] = pd.to_datetime(df_wy['date'])
                ax.plot(df_wy['date'], df_wy['ET_cumulative'], plot_kwargs['linestyle_ET'], color=plot_kwargs['color_ET'], label= 'ET (mm)')
            if plot_kwargs['plot_D']:
                df_d = self.deficit_timeseries
                df_d['date'] = pd.to_datetime(df_d['date'])
                ax.plot(df_d['date'], df_d['D'], plot_kwargs['linestyle_D'], color=plot_kwargs['color_D'], label='D(t) (mm)')

            ax.set_xlim(pd.to_datetime(plot_kwargs['xmin'], exact = False), pd.to_datetime(plot_kwargs['xmax'], exact = False))
            ax.set_xlabel(plot_kwargs['xlabel'])
            ax.set_ylabel(plot_kwargs['ylabel'])
            if plot_kwargs['legend']: ax.legend(loc = 'best')

            return fig
        
    
    def describe(self):
        """
        Print statements describing StudyArea attributes and deficit parameters, if deficit was calculated.

        Args:
            self
        Returns:
            printed statement
        """
        
        print('\n'+ str(self.description))
        try:
            print('Available data for this site:', self.available_data)
            print('Smax = ' + str(round(self.smax)) + ' mm')
            print('Deficit calculation parameters:\n\tDataset: ' + str(self.et_asset) + '\n\tBands: ' + str(self.et_bands))
            print('\tStart date: ' + str(self.start_date) + '\n\tEnd date: ' + str(self.end_date))
        except:
            print('Data has not been extracted for this site.')

    def __init__(self, coords, layers = None, **kwargs):
        self.coords = coords
        self.get_kind()
        self.get_feature()
        
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
        
        if layers is not None:

            self.make_combined_df(layers, **kwargs)
            self.calculate_deficit(layers, **kwargs)
            self.wateryear(layers, **kwargs)
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
    """
    Defaults to add together soil and vegetation ET bands (Es and Ec) for PML to create ET band.
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
