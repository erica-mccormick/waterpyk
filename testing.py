
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
    
    print(rivendell.smax, rivendell.maxdmax)
    print(plim.smax, plim.maxdmax)

    kwargs = {'legend':False, 'lw':1}
    fig = plim.plot(kind='RWS', **kwargs)
    fig.savefig('figs/rws_plim.pdf')
    
def sedgewick_tests():
    coords = [34.721123, -120.022917]
    title = 'Boulder Creek'
    filetitle = 'bouldercreek'
    boulder = [40.028, -105.488]
    sedge = pyk.StudyArea(boulder, layers)

    fig1kwargs = {'title':title}
    fig1 = sedge.plot(kind = 'timeseries', **fig1kwargs)
    fig1.savefig('figs/' + filetitle + '_timeseries.png')
    
    plotting_kwargs = {'plot_Q': False, 'plot_ET':True, 'xmin':2003, 'xmax':2020, 'linestyle_Q':'-o', 'linestyle_ET':'-o','linestyle_P':'-o','title':title}
    fig2 = sedge.plot(kind = 'wateryear', **plotting_kwargs)
    fig2.savefig('figs/' + filetitle + '_wateryeartotals.png')
    
    kwargs2 = {'legend':False, 'lw':1, 'title':title}
    fig3 = sedge.plot(kind='RWS', **kwargs2)
    fig3.savefig('figs/' + filetitle + '_RWS.png')
    
    plotting_kwargs3 = {'dpi':300, 'xmin':400, 'xmax':1000, 'title':title}
    fig4 = sedge.plot(kind='spearman', **plotting_kwargs3)
    fig4.savefig('figs/' + filetitle + '_spearman.png')

    
def wshed_test():
    gage = [11475560] #Real elder
    #gage = [11180825] #San Lorenzo
    elder = pyk.StudyArea(gage, layers)
    #print(elder.streamflow.head())
    #print(elder.wateryear_total.head())
    #print(elder.wateryear_timeseries.head())
    #elder.make_PET_df(layers, **kwargs)
    print(elder.smax)
    print(elder.maxdmax)
    
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
    
    #fig2 = elder.plot(kind = 'wateryear', **kwargs)
    #fig2.savefig('figs/elder_wateryear.png')
run_tests_limitation_sites()