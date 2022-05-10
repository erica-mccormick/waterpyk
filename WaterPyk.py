
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
from scipy import stats
import sys


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
            gp_site = pd.DataFrame({'longitude': [long], 'latitude': [lat]})
            site_geometry = gpd.points_from_xy(gp_site.longitude, gp_site.latitude, crs="EPSG:4326")
            flowlines = None

        elif self.kind == 'watershed':
            watershed = self.coords[0]
            url = 'https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/basin?f=json'%watershed
            site_geometry = gpd.read_file(url)    
            request = urllib.request.urlopen("https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/?f=json"%watershed)
            site_name = [json.load(request)['features'][0]['properties']['name'].title()]
            flowlines = gpd.read_file('https://labs.waterdata.usgs.gov/api/nldi/linked-data/nwissite/USGS-%s/navigation/UM/flowlines?f=json&distance=1000'%watershed)
            description = 'USGS Basin (' +str(watershed)+ ') imported at ' + str(site_name[0]) + 'CRS: ' + str(site_geometry.crs)
            poly_coords = [item for item in site_geometry.geometry[0].exterior.coords]
            feature = ee.Feature(ee.Geometry.Polygon(coords=poly_coords), {'Name': str(site_name[0]), 'Gage':int(watershed)})
            lat = site_geometry.to_crs('epsg:4326').geometry[0].centroid.y
        self.site_feature = feature
        self.url = url
        self.latitude = lat
        self.description = description
        self.site_geometry = site_geometry
        self.flowlines = flowlines
        return self, feature

    def get_streamflow(self, **kwargs):
        if self.kind == 'watershed':
            watershed = self.coords[0]
            basin = gpd.read_file(self.url)
            # url of flow data (usgs)
            start_date = kwargs['flow_startdate']
            end_date = kwargs['flow_enddate']
            url_flow = 'https://waterdata.usgs.gov/nwis/dv?cb_00060=on&format=rdb&site_no=' + str(watershed) + '&referred_module=sw&period=&begin_date='+ start_date +'&end_date='+ end_date
            print('\nStreamflow data is being retrieved from:', url_flow, '\n')
            # get df
            df = pd.read_csv(url_flow, header=31, delim_whitespace=True)
            df.columns = ['usgs', 'site_number', 'datetime', 'Q_cfs', 'a'] 
            df['date'] = pd.to_datetime(df.datetime)
            df = df[['Q_cfs','date']]
            df['Q_cfs'] = df['Q_cfs'].astype(float, errors='ignore')  #this is needed because sometimes there are non-numeric entries and we want to ignore them
            df['Q_m3day']= (86400*df['Q_cfs'])/(35.31) #m3/day
            # Calculate drainage area in m^2
            drainage_area_m2=basin.to_crs('epsg:26910').geometry.area 
            df['Q_m'] = df['Q_m3day'] / float(drainage_area_m2)
            df['Q_mm'] = df['Q_m3day'] / float(drainage_area_m2) * 1000
            #df.set_index('date',inplace=True)  
        else: df = pd.DataFrame()
        self.streamflow = df
        return self, df
    
 
    
    def make_long_df(self, layers, **kwargs):
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
            single_asset = extract_asset(self.site_feature, self.kind, asset_id = row.asset_id, start_date = pd.to_datetime(row.start_date), end_date = pd.to_datetime(row.end_date), scale = row.scale, bands = bands, bands_to_scale = row.bands_to_scale, scaling_factor = row.scaling_factor)#, row.file_path, row.file_name)
            single_asset['asset_name'] = row.name
            single_asset_propogate = single_asset[['asset_name', 'value','date','band']]
            df = df.append(single_asset_propogate)   
            
        if kwargs['combine_ET_bands'] == True:
            df = combine_bands(df, **kwargs)
 
        self.daily_data_long = df
        self.available_data = df.band.unique()
        self.start_date = layers.start_date[0]
        self.end_date = layers.end_date[0]
        return self, df

    def make_wide_df(self, layers, **kwargs):
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
            df = self.daily_data_long
        except:
            print('\nmake_wide_df() is extracting daily data specified in "layers"...')
            StudyArea.make_long_df(self, layers, **kwargs)
            df = self.daily_data_long
        
        # Isolate ET and P datasetes
        et_df = df[df['asset_name'] == kwargs['et_asset']]
        et_df = et_df[et_df['band'] == kwargs['et_band']]
        et_df['ET'] = et_df['value']
        ppt_df = df[df['asset_name'] == kwargs['ppt_asset']]
        ppt_df = ppt_df[ppt_df['band'] == kwargs['ppt_band']]
        ppt_df['P'] = ppt_df['value']
        df_wide = et_df.merge(ppt_df, how = 'inner', on = 'date')[['date', 'ET', 'P']]
        if self.kind == 'watershed': df_wide = df_wide.merge(self.streamflow, how = 'left', on = 'date')[['date', 'ET', 'P', 'Q_mm']]
        df_wide['original_index'] = df_wide.index

        # Add Hargreaves PET if bands are present
        if 'tmax' and 'tmin' in df['band'].unique():
            pet_df = calculate_PET(df, self.latitude)
            self.pet_daily = pet_df
            df_wide = df_wide.merge(pet_df[['PET', 'date']], how = 'left', on = 'date')
        else: print('PET was not included because PRISM tmax and tmin bands were not extracted.')
   
        # Add wateryear column
        df_wide = df_wide.set_index(pd.to_datetime(df_wide['date']))
        df_wide['wateryear'] = np.where(~df_wide.index.month.isin([10,11,12]),df_wide.index.year,df_wide.index.year+1)
        
        df_wide = df_wide.reset_index(drop=True)
        self.daily_data_wide = df_wide
        return self, df_wide

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
        try:
            df_def = self.daily_data_wide
            df = self.daily_data_long
        except:
            print('\ncalculate_deficit() is extracting layers...This may not work...')
            df_def = StudyArea.make_wide_df(self, layers, **kwargs)
            df = StudyArea.make_long_df(self, layers, **kwargs)
        if kwargs['snow_correction'] == True:
            snow_df = df[df['asset_name'] == 'modis_snow']
            snow_df = snow_df[snow_df['band'] == 'Cover']
            snow_df['Snow'] = snow_df['value']
            df_def = df_def.merge(snow_df, how = 'inner', on = 'date')[['date','ET','P','Snow','wateryear']]
            df_def.loc[df_def['Snow'] > kwargs['snow_frac'], 'ET'] = 0
        # Calculate A and D
        df_def['A'] = df_def['ET'] - df_def['P']
        df_def['D'] = 0
        for _i in range(df_def.shape[0]-1):
            df_def.loc[_i+1, 'D'] = max((df_def.loc[_i+1, 'A'] + df_def.loc[_i, 'D']), 0)
        
        
        ## Calculate wateryear deficit (D(t)_wy))
        df_wy = pd.DataFrame()
        for wy in df_def.wateryear.unique():
            temp = df_def[df_def['wateryear'] == wy][['date','ET','P']]
            temp['A'] = temp['ET'] - temp['P']
            temp['D_wy'] = 0
            temp = temp.reset_index()
            for _i in range(temp.shape[0]-1):
                temp.loc[_i+1, 'D_wy'] = max((temp.loc[_i+1, 'A'] + temp.loc[_i, 'D_wy']), 0)
            df_wy = df_wy.append(temp)
        df_wy = df_wy[['date','D_wy']]
        df_def = df_def.merge(df_wy, how = 'left', on = 'date')
        self.deficit_timeseries = df_def
        self.smax = round(df_def.D.max())
        self.maxdmax = round(df_def.D_wy.max())
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
        try:
            df_wide = self.daily_data_wide
        except:
            print('\nwateryear() is extracting layers...')
            df_wide = StudyArea.make_wide_df(self, layers, **kwargs)

        # Get a df of just summer ET
        df_wide = df_wide.set_index(df_wide['date'])
        df_wide['season'] = np.where(~df_wide.index.month.isin([6,7,8,9]),'summer','other')
        df_summer = df_wide[df_wide['season'] == 'summer']
        del df_wide['season']
        
        df_wide['ET_cumulative'] = df_wide.groupby(['wateryear'])['ET'].cumsum()
        df_wide['P_cumulative'] = df_wide.groupby(['wateryear'])['P'].cumsum()
        df_wide['PET_cumulative'] = df_wide.groupby(['wateryear'])['PET'].cumsum()
        if self.kind == 'watershed': df_wide['Q_cumulative'] = df_wide.groupby(['wateryear'])['Q_mm'].cumsum()

        df_total = pd.DataFrame()
        df_total['ET'] = df_wide.groupby(['wateryear'])['ET'].sum()
        df_total['P'] = df_wide.groupby(['wateryear'])['P'].sum()
        df_total['PET'] = df_wide.groupby(['wateryear'])['PET'].sum()
        df_total['ET_summer'] = df_summer.groupby(['wateryear'])['ET'].sum()
        if self.kind == 'watershed': df_total['Q'] = df_wide.groupby(['wateryear'])['Q_mm'].sum()
        df_total['wateryear'] = df_wide.groupby(['wateryear'])['wateryear'].first()
        df_wide = df_wide.reset_index(drop=True)
        df_total = df_total.reset_index(drop=True)
        self.wateryear_timeseries = df_wide
        self.wateryear_total = df_total
        self.map = df_total['P'].mean()
    
        return self, df_wide, df_total
    
    
    ########################## PLOTS ##########################
    def plot(self, kind = 'timeseries', title = '', **plot_kwargs):
        default_plotting_kwargs = {
            'plot_PET': False,
            'plot_Q': False,
            'plot_P': True,
            'plot_D': True,
            'plot_Dwy': True,
            'plot_ET': False,
            'plot_ET_dry': False,
            'color_PET': 'red',
            'color_Q': 'blue',
            'color_P': '#b1d6f0',
            'color_D': 'black',
            'color_Dwy':'black',
            'color_ET': 'purple',
            'markeredgecolor': 'black',
            'linestyle_PET':'-',
            'linestyle_Q':'-',
            'linestyle_P':'-',
            'linestyle_D': '-',
            'linestyle_Dwy':'--',
            'linestyle_ET': '-',
            'lw': 1.5, 
            'xmin': '2003-10-01',
            'xmax': '2020-10-01',
            'legend': True,
            'dpi': 300,
            'figsize': (6,4),
            'xlabel': 'Date',
            'ylabel': '[mm]',
            'twinx': False,
            'title': None
            }
        plot_kwargs = {**default_plotting_kwargs, **plot_kwargs}

        fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
        if title is not None: ax.set_title(title) 
        if kind == 'timeseries':
            df_wy = self.wateryear_timeseries
            df_d = self.deficit_timeseries
            df_wy['date'] = pd.to_datetime(df_wy['date'])
            df_d['date'] = pd.to_datetime(df_d['date'])

            if plot_kwargs['plot_Q']:
                if self.kind == 'watershed':
                    ax.plot(df_wy['date'], df_wy['Q_cumulative'], plot_kwargs['linestyle_Q'], color=plot_kwargs['color_Q'], lw = plot_kwargs['lw'], label= 'Q (mm)')
            if plot_kwargs['plot_PET']:
                ax.plot(df_wy['date'], df_wy['PET_cumulative'], plot_kwargs['linestyle_PET'], color=plot_kwargs['color_PET'], lw = plot_kwargs['lw'], label= 'PET (mm)') 
            if plot_kwargs['plot_P']:
                ax.fill_between(df_wy['date'], 0, df_wy['P_cumulative'],color='#b1d6f0', label='P (mm)', alpha = 0.7)
            if plot_kwargs['plot_ET']:
                ax.plot(df_wy['date'], df_wy['ET_cumulative'], plot_kwargs['linestyle_ET'], color=plot_kwargs['color_ET'], lw = plot_kwargs['lw'], label= 'ET (mm)')
            if plot_kwargs['plot_D']:
                ax.plot(df_d['date'], df_d['D'], plot_kwargs['linestyle_D'], color=plot_kwargs['color_D'], lw = plot_kwargs['lw'], label=r'$\mathrm{D(t)}\/\mathrm{(mm)}$')
            if plot_kwargs['plot_Dwy']:
                ax.plot(df_d['date'], df_d['D_wy'], plot_kwargs['linestyle_Dwy'], color=plot_kwargs['color_Dwy'], lw = plot_kwargs['lw'], label=r'$\mathrm{D}_{wy}\/\mathrm{(mm)}$')
            ax.set_xlim(pd.to_datetime(plot_kwargs['xmin'], exact = False), pd.to_datetime(plot_kwargs['xmax'], exact = False))
            if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])

        elif kind == 'wateryear':
            df = self.wateryear_total
            if plot_kwargs['plot_PET']:
                ax.plot(df['wateryear'], df['PET'], plot_kwargs['linestyle_PET'], color = plot_kwargs['color_PET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{PET}_{wy}\/\mathrm{(mm)}$')
            if plot_kwargs['plot_P']:
                ax.plot(df['wateryear'], df['P'], plot_kwargs['linestyle_P'], color = plot_kwargs['color_P'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{P}_{wy}\/\mathrm{(mm)}$')
            if plot_kwargs['plot_Q']:
                if self.kind == 'watershed':
                    ax.plot(df['wateryear'], df['Q'], plot_kwargs['linestyle_Q'], color = plot_kwargs['color_Q'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{Q}_{wy}\/\mathrm{(mm)}$')
            if plot_kwargs['twinx']:
                ax2 = ax.twinx()
                ax2.set_ylabel('ET (mm)', color = plot_kwargs['color_ET'])
            else: ax2 = ax
            if plot_kwargs['plot_ET']:
                ax2.plot(df['wateryear'], df['ET'], plot_kwargs['linestyle_ET'], color = plot_kwargs['color_ET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{ET}_{wy}\/\mathrm{(mm)}$')
            if plot_kwargs['plot_ET_dry']:
                ax2.plot(df['wateryear'], df['ET_summer'], ':o', color = plot_kwargs['color_ET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{ET}_{dry}\/\mathrm{(mm)}$')
            ax.set_xlim(plot_kwargs['xmin'], plot_kwargs['xmax'])
            if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])
        elif kind == 'spearman':
            df = self.wateryear_total
            ax.plot(df['P'], df['ET_summer'], 'o', color = '#a4a5ab', markersize = 12, lw = plot_kwargs['lw'],  markeredgecolor = plot_kwargs['markeredgecolor'], label = '')
            plot_kwargs['xlabel'] = r'$\mathrm{P}_{wy}\/\mathrm{(mm)}$'
            plot_kwargs['ylabel'] = r'$\mathrm{ET}_{dry}\/\mathrm{(mm)}$'
            plot_kwargs['legend'] = False
            ax.set_ylim(0,600)
            corr, p = stats.spearmanr(df[['P','ET_summer']])
            ax.annotate(r'$\rho$' + ' = ' + str(round(corr,2)) + '\n p-val = ' + str(round(p,4)),
                        xy=(.88, .85), xycoords='figure fraction',
                        horizontalalignment='right', verticalalignment='top',
                        fontsize=10)
            ax.set_xlim(plot_kwargs['xmin'], plot_kwargs['xmax'])

        ax.set_xlabel(plot_kwargs['xlabel'])
        ax.set_ylabel(plot_kwargs['ylabel'])
        if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])

        if plot_kwargs['legend']: ax.legend(loc = 'best')
        
       # elif kind == 'location':
       #     self.site_geometry.plot(ax = ax, crs = self.site_geometry.crs.to_string())
       #     #bbox_gdf.boundary.plot(ax = ax)
       #     self.flowlines.plot(ax = ax, crs = self.site_geometry.crs.to_string())
       #     ctx.add_basemap(ax = ax, crs = self.site_geometry.crs.to_string())
       #     plt.title(self.description)
            
        elif kind == 'RWS':
            df_d = self.deficit_timeseries
            df_d['RWS'] = df_d['D'] - self.smax
            df_d['RWS'] = df_d['RWS'] * -1
            df_d['date'] = pd.to_datetime(df_d['date'])
            ax.plot(df_d['date'], df_d['RWS'], plot_kwargs['linestyle_D'], color=plot_kwargs['color_D'], lw = plot_kwargs['lw'], label=r'$\mathrm{RWS(t)}\/\mathrm{(mm)}$')
            ax.set_xlim(pd.to_datetime(plot_kwargs['xmin'], exact = False), pd.to_datetime(plot_kwargs['xmax'], exact = False))
            if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])

        return fig, ax
            
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
            'snow_frac': 10,
            'flow_startdate':'1980-10-01',
            'flow_enddate':'2021-10-01'
            }
        kwargs = {**default_kwargs, **kwargs}
        
        self.coords = coords
        self.get_kind()
        self.get_feature()
        self.get_streamflow(**kwargs)
        
        if layers is not None:
            self.make_long_df(layers, **kwargs)
            self.make_wide_df(layers, **kwargs)
            self.calculate_deficit(layers, **kwargs)
            self.wateryear(layers, **kwargs)
            # Keep track of which ET product and bands were combined for deficit
            self.et_asset = kwargs['et_asset']
            if kwargs['combine_ET_bands'] == True: self.et_bands = kwargs['bands_to_combine']
            else: self.et_bands = 'Not combined'
        

## HELPER FUNCTIONS ##

def extract_asset(feature_geometry, kind, asset_id, start_date, end_date, scale, bands = None, bands_to_scale = None, scaling_factor = 1, reducer_type = None):
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
        
        asset = ee.ImageCollection(asset_id).filterDate(start_date, end_date)
        if bands is not None: asset = asset.select(bands)
        assetband = asset.toBands()
        if kind == 'point':
            reducer_type = ee.Reducer.first()
        elif kind == 'watershed':
            reducer_type = ee.Reducer.mean()
       # else:
       #     reducer_type = reducer_type
        reducer_dict = assetband.reduceRegion(reducer = reducer_type, geometry = feature_geometry.geometry(), scale = scale)
        
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


def getRA(site_lat_decimal):
  ## J (julian day)
  J = (np.linspace(1,365,365))
  ## Gsc (solar constant)  [MJ m-2 day -1] 
  Gsc = 0.0820
  ## inverse relative distance Earth-Sun
  dr = 1+0.033*np.cos(((2*np.pi)/365)*J) 
  ## delta = solar declination [rad]
  delta = 0.409*np.sin(((2*np.pi)/365)*J-1.39)  
  ## psi [rad] = convert decimal latitude to radians
  psi = (np.pi/180)*(32.3863) 
  ## omega_s (ws)= solar time angle at beginning of period [rad]
  omega_s = np.arccos(-np.tan(psi)*np.tan(delta)) 
  ## [ws * sin(psi) * sin(delta) + cos(psi) * cos(delta) * sin(ws)]
  angles = omega_s * np.sin(psi) * np.sin(delta) + np.cos(psi) * np.cos(delta) * np.sin(omega_s)
  RA = ((24*60)/np.pi) * Gsc * dr * angles

  df = pd.DataFrame()
  df['RA'] = RA
  df['J'] = J
  df['J']= df['J'].astype(int)
  return df


def calculate_PET(daily_data_df, latitude):#gage, p, tmin = 'tmin', tmax = 'tmax', tmean = 'tmean'):
    if 'tmax' and 'tmin' not in daily_data_df['band'].unique():
        sys.exit("'PET cannot be calsculated because PRISM temperature was not extracted.'")  
    else:
        # Get temperatures from prism
        prism_df = daily_data_df[daily_data_df['asset_name'] == 'prism']
        pet_df = pd.DataFrame()
        pet_df['tmax'] = prism_df[prism_df['band'] == 'tmax']['value'].values
        pet_df['tmin'] = prism_df[prism_df['band'] == 'tmin']['value'].values
        pet_df['date'] = pd.to_datetime(prism_df[prism_df['band'] == 'tmin']['date']).values

        # get RA (extraterrestrial radiation) with julian day column
        RA_df = getRA(latitude)
        pet_df['J'] = pd.to_datetime(pet_df['date']).dt.strftime('%j')
        pet_df['J'] = pet_df['J'].astype(int)
        
        # merge prism df with RA
        pet_df = pet_df.merge(RA_df, how='left', on=['J'])

        # calculate PET (Hargreave and Semani 1985)
        # Ep = 0.0023 · (Tmean + 17.8)·(Tmax − Tmin)^0.5 · 0.408 · Rext
        Krs = 0.0023 # Erica changed this from 0.00023 on Oct 15, 2021
        pet_df['PET'] = Krs * pet_df['RA'] * np.sqrt(pet_df['tmax'] - pet_df['tmin']) * (((pet_df['tmin']+pet_df['tmax'])/2) + 17.8)
    
        return pet_df
        