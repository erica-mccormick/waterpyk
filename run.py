
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
from scipy import stats

#from __init__ import default_saving_dir
from waterpyk import main
from waterpyk.main import default_saving_dir

if __name__ == "__main__":
        
    layers_path = '/Users/ericamccormick/Documents/GITHUB/WaterPyk/data/production/layers_minimal.csv'
    layers = pd.read_csv(layers_path)
    
    def make_all_plots(studyareaobject, figname):
        kwargs = {'title': figname}
        fig = studyareaobject.plot(kind = 'timeseries', **kwargs)
        plt.savefig('figs/' + figname + '_timeseries.png')
        
        fig1 = studyareaobject.plot(kind = 'RWS', **kwargs)
        plt.savefig('figs/' + figname + '_RWS.png')
        
        fig2 = studyareaobject.plot(kind = 'spearman', **kwargs)
        plt.savefig('figs/' + figname + '_spearman.png')
        
        fig3 = studyareaobject.plot(kind = 'wateryear', **kwargs)
        plt.savefig('figs/' + figname + '_wateryear.png')

        fig4 = studyareaobject.plot(kind = 'distribution', **kwargs)
        plt.savefig('figs/' + figname + '_pdistribution.png')
        
    gage = [11475560]
    #coords = [39.7273, -123.6433] #rivendell
    #coords = [43.463, -124.111] # oregon
    #coords = [43.46347, -124.11239] #where daniella is now
    coords = [40.007, -105.493] #gordon gulch

    rivendell = main.StudyArea(coords, layers)
    print('Smax:', rivendell.smax)
    print('MAP:', rivendell.MAP)
    make_all_plots(studyareaobject = rivendell, figname = 'Gordon Gulch')
