
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

# waterpyk modules
from waterpyk.extract import watershed
from waterpyk.extract import gee
from waterpyk.massbalance import massbalance

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
            site_name, description = watershed.metadata(gage)
            gee_feature, gpd_geometry = watershed.geometry(gage)
        
        self.site_name = site_name
        self.description = description
        self.gee_feature = gee_feature
        self.gpd_geometry = gpd_geometry
    
        return self, gee_feature
    
    def get_data(self, layers, **kwargs):
        
        ### Access data from GEE using "layers" csv
        try:
            df_long = gee.extract_assets_at_site(layers, self.gee_feature, self.kind, **kwargs)
        except AttributeError:
            StudyArea.get_location(self, **kwargs)
            df_long = gee.extract_assets_at_site(layers, self.gee_feature, self.kind, **kwargs)
    
        ### Convert dataframe to wide format using **kwargs
        df_wide = massbalance.make_wide_df(df_long, **kwargs)
        
        ### If deficit data types are given, merge deficit data
        df_deficit = massbalance.calculate_deficit(df_long, df_wide, **kwargs)
        df_deficit_min = df_deficit.date.min()
        df_deficit_max = df_deficit.date.max()
        
        df_wide = massbalance.merge_wide_deficit(df_wide, df_deficit)
        
        ### If kind = watershed, get and merge streamflow data
        if self.kind == 'watershed':
            gage = self.coords[0]
            df_streamflow = watershed.streamflow(gage, **kwargs)
            df_wide = massbalance.merge_wide_streamflow(df_wide, df_streamflow, q_column_name = 'Q_mm')

        else: df_streamflow = pd.DataFrame()
        
        ### Create wateryear cumulative and total dataframes
        df_wide, df_total = massbalance.wateryear(df_wide)

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
        print('Data available for wateryear totals:', list(self.wateryear_total))
        print('Deficit results:\n\tSmax = ' + str(self.smax) + ' mm')
        print('\tmax(Dmax) = ' + str(self.maxdmax) + ' mm')
        print('Deficit calculation parameters:\n\tDataset: ' + str(self.et_asset) + '\n\tBands: ' + str(self.et_bands))
        print('\tStart date: ' + str(self.deficit_timerange[0]) + '\n\tEnd date: ' + str(self.deficit_timerange[1]))

        
    def __init__(self, coords, layers = None, **kwargs):
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
        
        self.coords = coords
        self.get_kind()
        self.get_location(**kwargs)
        if layers is not None:
            self.get_data(layers, **kwargs)
        
