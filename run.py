
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
from scipy import stats

#from __init__ import default_saving_dir
from waterpyk import main, analyses
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
    coords = [39.7273, -123.6433] #rivendell
    #coords = [43.463, -124.111] # oregon
    #coords = [43.46347, -124.11239] #where daniella is now
    #coords = [40.007, -105.493] #gordon gulch

    ### Generic Setup ###
    rivendell = main.StudyArea(coords, layers)
    #print('Smax:', rivendell.smax)
    #print('MAP:', rivendell.MAP)
    make_all_plots(studyareaobject = rivendell, figname = 'Rivendell')
    
    
    #### Working on the bursts ###
    df = rivendell.daily_df_wide
    print(df)
    #df = analyses.deficit_bursts(rivendell.daily_df_wide)
    #print(df)
    df_zero = df[df.D == 0]
    print(df_zero)

    # get the start and end dates of the bursts and add in an artificial 'burst' starting on the first date of the year and ending at the start of the next burst
    start_of_bursts = []
    end_of_bursts = []
    max_D = []

    # For all the dates where the deficit = 0, find the time between the dates and the maximum value between the dates
    for j in range(len(df_zero['date'])-1):
        if (df_zero['date'][j+1] > df_zero['date'][j]):
            print(df_zero['date'][j])
            mask2 = (pd.to_datetime(df['date']) >= df_zero['date'][j]) & (pd.to_datetime(df['date']) <= df_zero['date'][j+1])
            bursts = pd.DataFrame()
            bursts = df.loc[mask2]
            if (len(bursts['D'])>2):
                start_of_bursts.append(bursts['date'][0])
                end_of_bursts.append(bursts['date'][-1])
                max_D.append(bursts['D'].max())
            else: continue
        else: continue
        
    # Save in df
    burstdf = pd.DataFrame()
    burstdf['start'] = start_of_bursts
    burstdf['end'] = end_of_bursts
    burstdf['max_D'] = max_D
  
    # Clean up and add more columns
    burstdf['start'] = pd.to_datetime(burstdf['start'])
    burstdf['end'] = pd.to_datetime(burstdf['end'])
    burstdf['duration'] = (burstdf['end'] - burstdf['start']).dt.days.astype('int16')
    burstdf = burstdf.set_index(burstdf['start'])
    burstdf['start_wateryear'] = np.where(~burstdf.index.month.isin([10,11,12]),burstdf.index.year,burstdf.index.year+1)
    burstdf = burstdf.reset_index(drop=True)
    burstdf = burstdf.set_index(burstdf['end'])
    burstdf['end_wateryear'] = np.where(~burstdf.index.month.isin([10,11,12]),burstdf.index.year,burstdf.index.year+1)
    burstdf = burstdf.reset_index(drop=True)

    

