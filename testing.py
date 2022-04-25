
import geopandas as gpd
import urllib
import json
import ee
import pandas as pd
import numpy as np
import datetime
ee.Initialize()

import ee_extractions as ee_tools

# These are the coordinates for the site "Rivendell"
coords = [39.7273, -123.6433]
layers = pd.read_csv('layers_long_contemporary_2021.csv')

# This is the USGS gage ID for Elder Creek
gage = [11475560]

# We can make objects using these coords
rivendell = ee_tools.StudyArea(coords, layers)
print(rivendell.smax)
rivendell.describe()
#elder = ee_tools.StudyArea(coords = gage, kind = 'watershed')

#asset_id = 'projects/pml_evapotranspiration/PML/OUTPUT/PML_V2_8day_v016'
#start_date = '2005-05-31'
#end_date = '2005-10-01'
#bands = ['Es', 'Ec', 'Ei']
#scale = 500

#layers_csv_path = 'https://raw.githubusercontent.com/erica-mccormick/ee_extractions/main/layers_short_contemporary_2021.csv'
#layers_csv_path = 'layers_long_contemporary_2021.csv'
##dir = ''
#file_name = 'test_merged.csv'
#export_csv_path = dir + file_name

#df = rivendell.make_combined_df(layers_csv_path, export_csv_path)
#df = ee_tools.combine_bands(df)

#df_def = ee_tools.calculate_deficit(df)

#print(df_def)

#snow_gt10 = df_def[df_def['Snow']>10]
#print(snow_gt10)

#smax = ee_tools.get_smax(df)
#print(smax)


#def test(**kwargs):
#    if kwargs['combine_a_and_b'] == True:
#        print('combine a and b was true')
#    if kwargs['print_a'] == True:
#        print('print_a was true')
        
#test(**testkwargs)