
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

# This is the USGS gage ID for Elder Creek
gage = [11475560]

# We can make objects using these coords
rivendell = ee_tools.StudyArea(coords, kind = 'point')
elder = ee_tools.StudyArea(coords = gage, kind = 'watershed')

asset_id = 'projects/pml_evapotranspiration/PML/OUTPUT/PML_V2_8day_v016'
start_date = '2005-05-31'
end_date = '2005-10-01'
bands = ['Es', 'Ec', 'Ei']
scale = 500

#layers_csv_path = 'https://raw.githubusercontent.com/erica-mccormick/ee_extractions/main/layers_short_contemporary_2021.csv'
layers_csv_path = 'layers_short_contemporary_2021.csv'
layers = pd.read_csv('layers_short_contemporary_2021.csv')
dir = ''
file_name = 'test_merged.csv'
export_csv_path = dir + file_name

df = rivendell.make_combined_df(layers_csv_path, export_csv_path)

# Trying to get a combined df

bands_to_combine = ['Es', 'Ec', 'Ei']
band_name_combined = 'ET'

to_store = pd.DataFrame()
for i in bands_to_combine:
    if i == bands_to_combine[0]:
        to_store = df[df['band'] == i]
        to_store['value_raw'] = np.nan

    else:
        subset = df[df['band']==i][['date', 'value']]
        to_store = to_store.merge(subset, how = 'inner', on = 'date')
        
val_cols = to_store.loc[:,to_store.columns.str.startswith("value")]
to_store['value'] = val_cols.sum(axis=1)
to_store['band'] = band_name_combined
to_store = to_store[['date', 'asset_name', 'value', 'band', 'value_raw']]

df = df.append(to_store)
df = df.reset_index(drop=True)



#prinxt(df.tail())
print(df)
#df
#rivendell.get_feature()
#et = elder.extract_asset(asset_id, start_date, end_date, scale, bands, interp = True)
#print(et)