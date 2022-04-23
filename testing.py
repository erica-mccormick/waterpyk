
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
elder = ee_tools.StudyArea(coords, kind = 'watershed')

asset_id = 'projects/pml_evapotranspiration/PML/OUTPUT/PML_V2_8day_v016'
start_date = '2005-05-31'
end_date = '2005-10-01'
bands = ['Es', 'Ec', 'Ei']
scale = 500

rivendell.get_feature()
et = rivendell.extract_asset(asset_id, start_date, end_date, scale, bands, interp = True)
print(et)