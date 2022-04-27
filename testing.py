
import geopandas as gpd
import urllib
import json
import ee
import pandas as pd
import numpy as np
import datetime
ee.Initialize()
import matplotlib
import matplotlib.pyplot as plt
import ee_extractions as ee_tools

# These are the coordinates for the site "Rivendell"
coords = [39.7273, -123.6433]
layers = pd.read_csv('layers_long_contemporary_2021.csv')

# This is the USGS gage ID for Elder Creek
gage = [11475560]

# We can make objects using these coords
rivendell = ee_tools.StudyArea(coords, layers)
#rivendell.get_feature()
print(rivendell.description)
print(rivendell.wateryear_timeseries)
print(rivendell.wateryear_total)

wytotal = rivendell.wateryear_total
print(type(wytotal.wateryear))

#kwargs = {'plot_ET': True}
##fig = rivendell.plot(kind='timeseries', title = 'Rivendell', **kwargs)
#fig.savefig('timeseries.png')

#kwargs = {'plot_ET': True, 'plot_P': False, 'color_D': 'green', 'linestyle_D': '--', 'linestyle_ET':':'}
#fig = rivendell.plot(kind='timeseries', title = 'Rivendell', **kwargs)
#fig.savefig('timeseries_2.png')

kwargs = {'plot_ET': True, 'plot_ET_dry':True, 'xmin':2004, 'xmax':2020, 'linestyle_ET':'-o', 'linestyle_P':'-o', 'twinx': True, 'legend':False}
fig = rivendell.plot(kind='wateryear', title = 'Rivendell', **kwargs)
fig.savefig('timeseries_3.png')

kwargs_spearman = {'xmin':0, 'xmax':4000, 'legend':False}
fig2 = rivendell.plot(kind = 'spearman', title = 'Rivendell', **kwargs_spearman)
fig2.savefig('spearman.png')

#print(rivendell.wateryear_timeseries)
#print(rivendell.wateryear_total)
#print(rivendell.smax)
#rivendell.describe()
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
        
#test(**testkwa


#import seaborn as sns
#import matplotlib.pyplot as plt

#fig = plt.figure(dpi=200)
#df = df.reset_index(drop=True)
#sns.lineplot(data=df, x="date", y="value", hue="band")
#plt.xlabel('Date')
#plt.ylabel('Daily amount [mm]')
#plt.title('Rivendell')
