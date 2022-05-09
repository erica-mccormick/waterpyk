
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
import WaterPyk as pyk

layers = pd.read_csv('data/layers_long_contemporary_2021.csv')



def run_tests_limitation_sites():
    # These are the coordinates for the site "Rivendell"
    coords = [39.7273, -123.6433]
    coords_plim = [36.5272 ,-118.8003]

    #We can make objects using these coords
    rivendell = pyk.StudyArea(coords, layers)
    plim = pyk.StudyArea(coords_plim, layers)
    
    kwargs = {'legend':False, 'lw':1}
    fig = plim.plot(kind='RWS', **kwargs)
    fig.savefig('figs/rws_plim.pdf')

def wshed_test():
    gage = [11475560] #Real elder
    #gage = [11180825] #San Lorenzo
    elder = pyk.StudyArea(gage, layers)
    #print(elder.streamflow.head())
    #print(elder.wateryear_total.head())
    #print(elder.wateryear_timeseries.head())
    
    kwargs = {
        'plot_Q': True,
        'plot_P': True,
        'plot_ET': True,
        'plot_D':True,
        'twinx':True,
        'title':'Elder',
        'xmin':2003,
        'xmax':2020
    }
    #fig = elder.plot(kind = 'timeseries',**kwargs)
    #fig.savefig('figs/elder_timeseries.png')
    
    fig2 = elder.plot(kind = 'wateryear', **kwargs)
    fig2.savefig('figs/elder_wateryear.png')
wshed_test()