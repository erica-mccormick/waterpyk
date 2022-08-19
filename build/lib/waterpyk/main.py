import os
import random
import warnings
from time import time

import ee
import geopandas as gpd
import pandas as pd

from waterpyk import calcs  # Determine default saving behavior
from waterpyk import default_saving_dir, gee, in_colab_shell, plots, watershed

ee.Initialize()


warnings.filterwarnings("ignore")


class StudyArea:

    def get_layers(self, layers):
        """
        Return a df with the layers (ie asset list and metadata) being used.
        """
        if layers == 'all' or layers == 'minimal':
            layers = gee.load_data(layers)
        return layers

    def get_kind(self):
        """
        Adds attribute of point or watershed to object.

        """
        if type(self.coords) == list:
            if len(self.coords) > 1:
                self.kind = 'point'
            else:
                self.kind = 'watershed'
        else:
            self.kind = 'shape'
        return self

    def get_location(self, **kwargs):
        """
        Convert coordinates to GEE feature. For a USGS watershed, coordinates are extracted from USGS website using gage ID.

        Args:
            site_name (str, optional): Watersheds are already named. Default for lat/long sites is empty string.

        Returns:
            :obj:`feature`: gee feature with location geometry 
        """
        # Make sure the self.kind exists
        StudyArea.get_kind(self)

        # Get the GEE and geopandas geometries and metadata for a point
        if self.kind == 'point':
            lat = self.coords[0]
            long = self.coords[1]
            site_name = kwargs['site_name']
            description = 'Site at coordinates ' + \
                str(lat) + ', ' + str(long) + '. Name = ' + \
                site_name + '. CRS = EPSG:4326.'
            gee_feature = ee.Feature(ee.Geometry.Point(long, lat))
            gp_site = pd.DataFrame({'longitude': [long], 'latitude': [lat]})
            gpd_geometry = gpd.points_from_xy(
                gp_site.longitude, gp_site.latitude, crs="EPSG:4326")

        # Use the watershed package to get the geometries and metadata for a USGS gauged watershed
        elif self.kind == 'watershed':
            gage = str(self.coords[0])
            site_name, description = watershed.extract_metadata(gage)
            gee_feature, gpd_geometry = watershed.extract_geometry(gage)

        # Get the GEE and geopandas geometries and metadata for a point
        elif self.kind == 'shape':
            gpd_geometry = self.coords
            gee_feature = gee.gdf_to_feat(self.coords)
            site_name = kwargs['site_name']
            description = 'Geopandas geometry extracted at: Name = ' + \
                site_name + '. CRS = EPSG:4326.'

        else:
            raise ValueError(f'self.kind not recognized. Got {self.kind}.')

        self.site_name = site_name
        self.description = description
        self.gee_feature = gee_feature
        self.gpd_geometry = gpd_geometry

        return self, gee_feature

    def get_data(self, layers, **kwargs):
        """
        Updates self with attributes containing dataframes for the site.
        If data already exists in saving_dir, data is simply loaded.
        Otherwise, data from layers is extracted from GEE and the USGS.

        Args:
            layers (str or :obj:`df`, optional): If str, specify 'minimal' or 'all' to extract default set of assets. If df, columns that must be present include: asset_id, start_date, end_date, relative_date, scale, bands, bands_to_scale, new_bandnames, scaling factor. These are the same parameters required for extract_basic(). 
            **interp (bool, optional): (default: True), currently no option to change to False.
            **combine_ET_bands (bool, optional): (default True) add ET bands to make one ET band.
            **bands_to_combine (list of str, optional): (default [Es, Ec]) ET bands to combine
            **band_names_combined (str, optional): (default 'ET') name of combined ET band
            **et_asset (str, optional): asset to be used for creation of ET column (default 'pml').
            **et_band (str, optional): band name to be used for creation of ET column (default 'ET').
            **ppt_asset (str, optional): asset name for precipitation column (default 'prism').
            **ppt_band (str, optional): band name for precipitation colum (default 'ppt')
            **snow_asset (str, optional): defaults to 'modis_snow'
            **snow_band (str, optional): defaults to 'snow'. Note: You will need to change this if you don't specify to change the default name of this asset upon extraction.
            **snow_correction (bool, optional): (default True) use snow correction factor when calculating deficit
            **snow_frac (int, optional): (default 10) set all ET when snow is greater than this (%) to 0 if snow_correction = True

        """
        if in_colab_shell():
            path_format = '_'
        else:
            path_format = '/'

        # If data already exists, just pull it in:
        if os.path.exists(self.saving_path):
            print('\nRetrieving site data from ' +
                  os.path.abspath(self.saving_path))
            self.daily_df_long = pd.read_csv(
                self.saving_path + path_format + 'daily_df_long.csv')
            self.daily_df_wide = pd.read_csv(
                self.saving_path + path_format + 'daily_df_wide.csv')
            self.stats = pd.read_csv(
                self.saving_path + path_format + 'stats.csv')
            self.streamflow = pd.read_csv(
                self.saving_path + path_format + 'streamflow.csv')
            self.deficit_timeseries = pd.read_csv(
                self.saving_path + path_format + 'deficit_timeseries.csv')
            self.wateryear_totals = pd.read_csv(
                self.saving_path + path_format + 'wateryear_totals.csv')
            self.smax = round(self.deficit_timeseries.D.max())
            self.maxdmax = round(self.deficit_timeseries.D_wy.max())
            self.deficit_timerange = (
                self.deficit_timeseries.date.min(), self.deficit_timeseries.date.max())

        # Otherwise, use layers.csv to download new data and save it:
        else:
            if layers is None:
                print(
                    'No layers were specified for extraction and data is not already available.')
            try:
                df_long, df_image = gee.extract(
                    layers, self.gee_feature, self.kind, **kwargs)
            except AttributeError:
                StudyArea.get_location(self, **kwargs)
                df_long, df_image = gee.extract(
                    layers, self.gee_feature, self.kind, **kwargs)

            # Convert dataframe to wide format using **kwargs
            df_wide = calcs.make_wide_df(df_long, **kwargs)

            # If deficit data types are given, merge deficit data
            df_deficit = calcs.deficit(df_long, df_wide, **kwargs)
            df_deficit_min = df_deficit.date.min()
            df_deficit_max = df_deficit.date.max()
            df_wide = calcs.merge(df_wide, df_deficit, 'deficit')

            # If kind = watershed, get and merge streamflow data
            if self.kind == 'watershed':
                gage = self.coords[0]
                df_streamflow = watershed.extract_streamflow(gage, **kwargs)
                df_wide = calcs.merge(df_wide, df_streamflow, 'streamflow')
            else:
                df_streamflow = pd.DataFrame()

            # Create wateryear cumulative and total dataframes
            df_wide, df_total = calcs.wateryear(df_wide)

            # Save data (just long df for GoogleColab and all data otherwise)
            print("\nSaving all dataframes at:\n\t% s" %
                  os.path.abspath(self.saving_path))
            if in_colab_shell() == False:
                os.mkdir(self.saving_path)
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
            with open(self.saving_path + path_format + 'stats.csv', 'w') as f:
                df_image.to_csv(f)

            # Add all attributes to self
            self.daily_df_long = df_long
            self.daily_df_wide = df_wide
            self.stats = df_image
            self.streamflow = df_streamflow
            self.deficit_timeseries = df_deficit
            self.wateryear_totals = df_total
            self.smax = round(df_deficit.D.max())
            self.maxdmax = round(df_deficit.D_wy.max())
            self.deficit_timerange = (df_deficit_min, df_deficit_max)

    def describe(self):
        """
        Print statements describing StudyArea attributes and deficit parameters, if deficit was calculated.

        """
        print('\n' + str(self.description))
        print('Geometry kind:', self.kind)
        print('Data extracted from GEE:', self.daily_df_long.band.unique())
        print('GEE reducer used: MEAN() for watersheds and FIRST() for points')
        print('Data available for wateryear totals:',
              list(self.wateryear_totals))
        print('Deficit results:\n\tSmax = ' + str(self.smax) + ' mm')
        print('\tmax(Dmax) = ' + str(self.maxdmax) + ' mm')
        print('\tStart date: ' +
              str(self.deficit_timerange[0]) + '\n\tEnd date: ' + str(self.deficit_timerange[1]))
        print('Kwargs set to:', self.settings)

    def plot(self, kind, **kwargs):
        """ Make common plots of the data specifying what 'kind' of plot.
        Each kind of plot has defaults pre-set, which may differ from the arg defaults specified below.
        To see the full list of defaults, see the plots submodule.
        In general, updating kwargs should not be necessary except for small details like legend, title, or colors.

        Args:
            kind (str): The kind of plot you wanted. Not to be confused with the kind of site (ie watershed or point). Supported types are: 'timeseries', 'spearman', 'wateryear', 'RWS', and 'distribution'.
            **plot_PET (bool, optional)
            **plot_Q (bool, optional)
            **plot_D (bool, optional)
            **plot_Dwy (bool, optional):
            **plot_ET (bool, optional): include wateryear ET in plot
            **plot_ET_dry  (bool, optional): include dry season ET in plot
            **color_PET (str, optional): hex code string for color
            **color_Q (str, optional): hex code string for color
            **color_P (str, optional): hex code string for color
            **color_D (str, optional): hex code string for color
            **color_ET (str, optional): hex code string for color
            **color_WY (str, optional): hex code string for color
            **markeredgecolor (str, optional): default = black
            **linestyle_PET (str, optional)
            **linestyle_Q (str, optional)
            **linestyle_P (str, optional)
            **linestyle_D (str, optional)
            **linestyle_Dwy (str, optional)
            **linestyle_ET (str, optional)
            **lw (float, optional): line weight. Default = 1.5
            **xmin (date or float or int, optional)
            **xmax (date or float or int, optional)
            **legend (bool, optional): default = True
            **dpi (int, optional): default = 300
            **figsize (tuple, optional): default = (6,4)
            **xlabel (str, optional)
            **ylabel (str, optional)
            **twinx (bool, optional): some plots allow for twin x-axes. Default = False.
            **title (str, optional): default None

        """
        if kind == 'timeseries':
            fig = plots.plot_timeseries(self, **kwargs)
        elif kind == 'spearman':
            fig = plots.plot_spearman(self, **kwargs)
        elif kind == 'wateryear':
            fig = plots.plot_wateryear_totals(self, **kwargs)
        elif kind == 'RWS':
            fig = plots.plot_RWS(self, **kwargs)
        elif kind == 'distribution':
            fig = plots.plot_p_distribution(self, **kwargs)
        else:
            raise ValueError(f"Plot kind not recognized. Got {kind}.")
        return fig

    def _path(self):
        """Make a folder name for storing data."""
        if self.kind == 'watershed':
            folder_name = str(self.coords[0])
        elif self.kind == 'point':
            folder_name = str(self.coords[0]) + '_' + str(self.coords[1])
        elif self.kind == 'shape':
            # If you give it a name, it will save under that name
            # Otherwise, it will save under a random folder name.
            if self.site_name != '':
                folder_name = str(self.site_name)
            else:
                folder_name = 'shape_' + str(random.randint(10, 99))
        else:
            raise ValueError(f'self.kind not recognized. Got {self.kind}.')
        saving_path = os.path.abspath(
            os.path.join(self.saving_dir, folder_name))
        self.saving_path = saving_path
        return saving_path

    def __str__(self):
        return f'StudyArea({self.kind}), named {self.site_name}'

    def __repr__(self):
        return f"StudyArea(kind='{self.kind}', name={self.site_name})"

    def __init__(self, coords, layers=None, saving_dir=default_saving_dir, **kwargs):
        default_kwargs = {
            'site_name': '',
            'interp': True,
            'combine_ET_bands': True,
            'bands_to_combine': ['Es', 'Ec'],
            'band_name_final': 'ET',
            'et_asset': 'pml',
            'et_band': 'ET',
            'ppt_asset': 'prism',
            'ppt_band': 'ppt',
            'snow_asset': 'modis_snow',
            'snow_band': 'snow',
            'snow_correction': True,
            'snow_frac': 10,
            'flow_start_date': '1980-10-01',
            'flow_end_date': '2021-10-01'
        }
        kwargs = {**default_kwargs, **kwargs}
        self.settings = kwargs
        self.coords = coords
        self.layers = layers
        self.saving_dir = saving_dir
        self.get_kind()
        self.get_location(**kwargs)
        self._path()
        t1 = time()
        self.get_data(layers, **kwargs)
        t2 = time()
        print('\nTime to access data: ' + str(round(t2-t1, 3)) + ' seconds')
        self.MAP = round(self.wateryear_totals.P.mean())
