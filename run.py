
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
from scipy import stats

#from __init__ import default_saving_dir
from waterpyk import waterpyk
from waterpyk import default_saving_dir

if __name__ == "__main__":
        
    layers_path = '/Users/ericamccormick/Documents/GITHUB/WaterPyk/data/production/layers_minimal.csv'
    layers = pd.read_csv(layers_path)
    
    def make_all_plots(studyareaobject, figname):
        kwargs = {'title': figname}
        fig = studyareaobject.plot(kind = 'timeseries', **kwargs)
        plt.savefig('figs/' + figname + '_timeseries')
        
        fig1 = studyareaobject.plot(kind = 'RWS', **kwargs)
        plt.savefig('figs/' + figname + '_RWS')
        
        fig2 = studyareaobject.plot(kind = 'spearman', **kwargs)
        plt.savefig('figs/' + figname + '_spearman')
        
        fig3 = studyareaobject.plot(kind = 'wateryear', **kwargs)
        plt.savefig('figs/' + figname + '_wateryear')
        
    gage = [11475560]
    coords = [39.7273, -123.6433]
    

    rivendell = waterpyk.StudyArea(coords, layers)
    print(rivendell.site_name)
    print(rivendell.smax)
    #make_all_plots(studyareaobject = rivendell, figname = 'Rivendell')
