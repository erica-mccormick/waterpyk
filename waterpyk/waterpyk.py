
import geopandas as gpd
import urllib
import json
import ee
import pandas as pd
import numpy as np
import datetime
import warnings
from time import time
warnings.filterwarnings("ignore")
ee.Initialize()
import matplotlib
import matplotlib.pyplot as plt
from scipy import stats
import sys
import os

from waterpyk import analyses, extract_gee, extract_watershed, plots
from waterpyk import default_saving_dir, in_colab_shell

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
        return self
    
    def get_location(self, **kwargs):
        """
        Convert coordinates to GEE feature. For a USGS watershed,
        coordinates are extracted from website using gage ID.

        Args:
            self
            site_name (str): (optional) (for lat/long sites; default is blank and watersheds are already named)
       
        Returns:
            self
            gee_feature
        """
        # Make sure the self.kind exists
        StudyArea.get_kind(self)
        
        # Get the GEE and geopandas geometries and metadata for a point
        if self.kind == 'point':
            lat = self.coords[0]
            long = self.coords[1]
            site_name = kwargs['site_name']
            description = 'Site at coordinates ' + str(lat) + ', ' + str(long) + '. Name = ' + site_name + '. CRS = EPSG:4326.'
            gee_feature = ee.Feature(ee.Geometry.Point(long, lat))
            gp_site = pd.DataFrame({'longitude': [long], 'latitude': [lat]})
            gpd_geometry = gpd.points_from_xy(gp_site.longitude, gp_site.latitude, crs="EPSG:4326")

        # Use the watershed package to get the geometries and metadata for a USGS gauged watershed
        elif self.kind == 'watershed':
            gage = str(self.coords[0])
            site_name, description = extract_watershed.metadata(gage)
            gee_feature, gpd_geometry = extract_watershed.geometry(gage)
        
        self.site_name = site_name
        self.description = description
        self.gee_feature = gee_feature
        self.gpd_geometry = gpd_geometry
    
        return self, gee_feature
    
            
    def get_data(self, layers, **kwargs):
        if in_colab_shell(): path_format = '_'
        else: path_format = '/'
        
        ### If data already exists, just pull it in:
        if os.path.exists(self.saving_path):
            print('\nRetrieving site data from ' + os.path.abspath(self.saving_path))
            self.daily_df_long = pd.read_csv(self.saving_path + path_format + 'daily_df_long.csv')
            self.daily_df_wide = pd.read_csv(self.saving_path + path_format + 'daily_df_wide.csv')
            self.streamflow = pd.read_csv(self.saving_path + path_format + 'streamflow.csv')
            self.deficit_timeseries = pd.read_csv(self.saving_path + path_format + 'deficit_timeseries.csv')
            self.wateryear_totals = pd.read_csv(self.saving_path + path_format + 'wateryear_totals.csv')         
            self.smax = round(self.deficit_timeseries.D.max())
            self.maxdmax = round(self.deficit_timeseries.D_wy.max())
            self.deficit_timerange = (self.deficit_timeseries.date.min(), self.deficit_timeseries.date.max())
        
        ### Otherwise, use layers.csv to download new data and save it:
        else:
            if layers is None:
                print('No layers were specified for extraction and data is not already available.')
            try:
                df_long = extract_gee.extract_assets_at_site(layers, self.gee_feature, self.kind, **kwargs)
            except AttributeError:
                StudyArea.get_location(self, **kwargs)
                df_long = extract_gee.extract_assets_at_site(layers, self.gee_feature, self.kind, **kwargs)
        
            ### Convert dataframe to wide format using **kwargs
            df_wide = analyses.make_wide_df(df_long, **kwargs)
            
            ### If deficit data types are given, merge deficit data
            df_deficit = analyses.calculate_deficit(df_long, df_wide, **kwargs)
            df_deficit_min = df_deficit.date.min()
            df_deficit_max = df_deficit.date.max()
            
            df_wide = analyses.merge_wide_deficit(df_wide, df_deficit)
            
            ### If kind = watershed, get and merge streamflow data
            if self.kind == 'watershed':
                gage = self.coords[0]
                df_streamflow = extract_watershed.streamflow(gage, **kwargs)
                df_wide = analyses.merge_wide_streamflow(df_wide, df_streamflow, q_column_name = 'Q_mm')

            else: df_streamflow = pd.DataFrame()
            
            ### Create wateryear cumulative and total dataframes
            df_wide, df_total = analyses.wateryear(df_wide)

            ### Save data (just long df for GoogleColab and all data otherwise)
            print("\nSaving all dataframes at:\n\t% s" % os.path.abspath(self.saving_path))
            if in_colab_shell() == False: os.mkdir(self.saving_path)
            with open(self.saving_path + path_format + 'daily_df_long.csv', 'w') as f:
                df_long.to_csv(f)
            with open(self.saving_path + path_format + 'daily_df_wide.csv', 'w') as f:
                df_wide.to_csv(f)
            with open(self.saving_path + path_format + 'streamflow.csv', 'w') as f:
                df_streamflow.to_csv(f)
            with open(self.saving_path + path_format + 'deficit_timeseries.csv', 'w') as f:
                df_deficit.to_csv(f)    
            with open(self.saving_path + path_format + 'wateryear_totals.csv', 'w') as f:
                df_total.to_csv(f)    
                    
            ### Add all attributes to self
            self.daily_df_long = df_long
            self.daily_df_wide = df_wide
            self.streamflow = df_streamflow
            self.deficit_timeseries = df_deficit
            self.wateryear_totals = df_total
            self.smax = round(df_deficit.D.max())
            self.maxdmax = round(df_deficit.D_wy.max())
            self.deficit_timerange = (df_deficit_min, df_deficit_max)
            
        
    def describe(self):
        """
        Print statements describing StudyArea attributes and deficit parameters, if deficit was calculated.

        Args:
            self
        Returns:
            printed statement
        """
        
        print('\n'+ str(self.description))
        print('Geometry kind:', self.kind)
        print('Data extracted from GEE:', self.daily_df_long.band.unique())
        print('GEE reducer used: MEAN() for watersheds and FIRST() for points')
        print('Data available for wateryear totals:', list(self.wateryear_totals))
        print('Deficit results:\n\tSmax = ' + str(self.smax) + ' mm')
        print('\tmax(Dmax) = ' + str(self.maxdmax) + ' mm')
        print('Deficit calculation parameters:\n\tDataset: ' + str(self.et_asset) + '\n\tBands: ' + str(self.et_bands))
        print('\tStart date: ' + str(self.deficit_timerange[0]) + '\n\tEnd date: ' + str(self.deficit_timerange[1]))
        print('Kwargs set to:', self.settings)
        
    def plot(self, kind, **kwargs):
        if kind == 'timeseries':
            fig = plots.plot_timeseries(self, **kwargs)
        elif kind == 'spearman':
            fig = plots.plot_spearman(self, **kwargs)
        elif kind == 'wateryear':
            fig = plots.plot_wateryear_totals(self, **kwargs)
        elif kind == 'RWS':
            fig = plots.plot_RWS(self, **kwargs)
        return fig
            
    def _path(self):
        if self.kind == 'watershed':
            folder_name = str(self.coords[0])
        elif self.kind == 'point':
            folder_name = str(self.coords[0]) + '_' + str(self.coords[1])
        saving_path = os.path.abspath(os.path.join(self.saving_dir, folder_name))
        self.saving_path = saving_path
        return saving_path   
        
    def __init__(self, coords, layers = None, saving_dir = default_saving_dir, **kwargs):
        default_kwargs = {
            'site_name':'',
            'interp': True,
            'combine_ET_bands': True,
            'bands_to_combine': ['Es', 'Ec'],
            'band_name_final': 'ET',
            'et_asset': 'pml',
            'et_band': 'ET',
            'ppt_asset': 'prism',
            'ppt_band': 'ppt',
            'snow_asset':'modis_snow',
            'snow_band':'Cover',
            'snow_correction': True,
            'snow_frac': 10,
            'flow_start_date':'1980-10-01',
            'flow_end_date':'2021-10-01'
            }
        kwargs = {**default_kwargs, **kwargs}
        self.settings = kwargs
        self.coords = coords
        self.layers = layers
        self.saving_dir = saving_dir
        self.get_kind()
        self._path()
        self.get_location(**kwargs)
        t1 = time()
        self.get_data(layers, **kwargs)
        t2 = time()
        print('\nTime to access data: ' + str(round(t2-t1,3)) + ' seconds')