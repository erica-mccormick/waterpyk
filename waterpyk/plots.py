import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from scipy import stats

default_kwarg_dictionary = {
        'plot_PET': False,
        'plot_Q': False,
        'plot_P': True,
        'plot_D': True,
        'plot_Dwy': True,
        'plot_ET': False,
        'plot_ET_dry': False,
        'color_PET': 'red',
        'color_Q': 'blue',
        'color_P': '#b1d6f0',
        'color_D': 'black',
        'color_Dwy':'black',
        'color_ET': 'purple',
        'markeredgecolor': 'black',
        'linestyle_PET':'-',
        'linestyle_Q':'-',
        'linestyle_P':'-',
        'linestyle_D': '-',
        'linestyle_Dwy':'--',
        'linestyle_ET': '-',
        'lw': 1.5, 
        'xmin': '2003-10-01',
        'xmax': '2020-10-01',
        'legend': True,
        'dpi': 300,
        'figsize': (6,4),
        'xlabel': 'Date',
        'ylabel': '[mm]',
        'twinx': False,
        'title': None
        }

def plot_p_distribution(studyareaobject = None, df_wateryear_totals = None, smax = None, **plot_kwargs):
    print('Plotting precip distribution...')
    updated_kwargs = {'xmin': 0, 'xmax':4000, 'xlabel':'mm', 'ylabel':'Density'}
    default_kwargs = {**default_kwarg_dictionary, **updated_kwargs}    
    plot_kwargs = {**default_kwargs, **plot_kwargs}    
    
    if studyareaobject is not None:
        wateryear_totals = studyareaobject.wateryear_totals
        smax = studyareaobject.smax
    elif df_wateryear_totals is not None:
        wateryear_totals = df_wateryear_totals
        smax = smax
    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
    sns.kdeplot(data=wateryear_totals, x="P", color = '#79C3DB', alpha = 0.3)
    x = ax.lines[-1].get_xdata()
    y = ax.lines[-1].get_ydata()
    ax.fill_between(x, 0, y, color='#79C3DB', alpha=0.3, label=r'$\mathrm{P}_{wy (2003-2020)}\/\mathrm{(mm)}$')
    ax.fill_between(x, 0, y, where=x<smax, color='#ED9935', hatch = 'x', alpha=0.4)
    plt.axvspan(smax, smax, alpha=1, color='#ED9935', label = r'$\mathrm{S}_{max}\/\mathrm{(mm)}$')
    ax.set_xlim(plot_kwargs['xmin'], plot_kwargs['xmax'])
    if plot_kwargs['title'] is not None: fig.suptitle(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])


def plot_timeseries(studyareaobject = None, df_daily_wide = None, df_timeseries = None, **plot_kwargs):
    print('Plotting timeseries...')
    plot_kwargs = {**default_kwarg_dictionary, **plot_kwargs}    
    
    if studyareaobject is not None:
        df_wy = studyareaobject.daily_df_wide
        df_d = studyareaobject.deficit_timeseries
    elif df_daily_wide is not None:
        df_wy = df_daily_wide
        df_d = df_timeseries
    else:
        print('No data was specified for plotting')
     
    df_wy['date'] = pd.to_datetime(df_wy['date'])
    df_d['date'] = pd.to_datetime(df_d['date'])   
    
    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
      
    # Plot things if given in kwargs
    if plot_kwargs['plot_Q']:
        if studyareaobject.kind == 'watershed':
            ax.plot(df_wy['date'], df_wy['Q_mm_cumulative'], plot_kwargs['linestyle_Q'], color=plot_kwargs['color_Q'], lw = plot_kwargs['lw'], label= 'Q (mm)')
    if plot_kwargs['plot_PET']:
        ax.plot(df_wy['date'], df_wy['PET_cumulative'], plot_kwargs['linestyle_PET'], color=plot_kwargs['color_PET'], lw = plot_kwargs['lw'], label= 'PET (mm)') 
    if plot_kwargs['plot_P']:
        ax.fill_between(df_wy['date'], 0, df_wy['P_cumulative'],color='#b1d6f0', label='P (mm)', alpha = 0.7)
    if plot_kwargs['plot_ET']:
        ax.plot(df_wy['date'], df_wy['ET_cumulative'], plot_kwargs['linestyle_ET'], color=plot_kwargs['color_ET'], lw = plot_kwargs['lw'], label= 'ET (mm)')
    if plot_kwargs['plot_D']:
        ax.plot(df_d['date'], df_d['D'], plot_kwargs['linestyle_D'], color=plot_kwargs['color_D'], lw = plot_kwargs['lw'], label=r'$\mathrm{D(t)}\/\mathrm{(mm)}$')
    if plot_kwargs['plot_Dwy']:
        ax.plot(df_d['date'], df_d['D_wy'], plot_kwargs['linestyle_Dwy'], color=plot_kwargs['color_Dwy'], lw = plot_kwargs['lw'], label=r'$\mathrm{D}_{wy}\/\mathrm{(mm)}$')
    ax.set_xlim(pd.to_datetime(plot_kwargs['xmin'], exact = False), pd.to_datetime(plot_kwargs['xmax'], exact = False))
    if plot_kwargs['title'] is not None: fig.suptitle(plot_kwargs['title'])
    if plot_kwargs['legend'] == True: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    return fig


def plot_wateryear_totals(studyareaobject = None, df_wateryear_totals = None, **plot_kwargs):
    print('Plotting wateryear data...')
    if studyareaobject is not None:
        df = studyareaobject.wateryear_totals
    elif df_wateryear_totals is not None:
        df = df_wateryear_totals
    else:
        print('No data was specified for plotting.')
    # Get kwargs set up
    updated_kwargs = {
            'plot_Q': True,
            'plot_P': True,
            'plot_ET': True,
            'plot_D':True,
            'twinx':True,
            'xmin':2003,
            'xmax':2020,
            'linestyle_Q':'-o',
            'linestyle_ET':'-o',
            'linestyle_P':'-o',
            'xlabel':'Wateryear'
        }
    
    default_kwargs = {**default_kwarg_dictionary, **updated_kwargs}    
    plot_kwargs = {**default_kwargs, **plot_kwargs}    
        
    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
    if plot_kwargs['plot_PET']:
        print('Plotting PET!')
        ax.plot(df['wateryear'], df['PET'], plot_kwargs['linestyle_PET'], color = plot_kwargs['color_PET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{PET}_{wy}\/\mathrm{(mm)}$')
    if plot_kwargs['plot_P']:
        ax.plot(df['wateryear'], df['P'], plot_kwargs['linestyle_P'], color = plot_kwargs['color_P'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{P}_{wy}\/\mathrm{(mm)}$')
    if plot_kwargs['plot_Q']:
        if studyareaobject.kind == 'watershed':
            ax.plot(df['wateryear'], df['Q_mm'], plot_kwargs['linestyle_Q'], color = plot_kwargs['color_Q'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{Q}_{wy}\/\mathrm{(mm)}$')
    if plot_kwargs['twinx']:
        ax2 = ax.twinx()
        ax2.set_ylabel('ET (mm)', color = plot_kwargs['color_ET'])
    else: ax2 = ax
    if plot_kwargs['plot_ET']:
        ax2.plot(df['wateryear'], df['ET'], plot_kwargs['linestyle_ET'], color = plot_kwargs['color_ET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{ET}_{wy}\/\mathrm{(mm)}$')
    if plot_kwargs['plot_ET_dry']:
        ax2.plot(df['wateryear'], df['ET_summer'], ':o', color = plot_kwargs['color_ET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{ET}_{dry}\/\mathrm{(mm)}$')
    ax.set_xlim(plot_kwargs['xmin'], plot_kwargs['xmax'])
    if plot_kwargs['title'] is not None: fig.suptitle(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    return fig



def plot_spearman(studyareaobject = None, df_wateryear_totals = None, **plot_kwargs):
    print('Plotting spearman...')
    if studyareaobject is not None:
        df = studyareaobject.wateryear_totals
    elif df_wateryear_totals is not None:
        df = df_wateryear_totals
    else:
        print('No data was specified for plotting')

    # Get kwargs set up
    updated_kwargs = {'xmin':0, 'xmax':3000}
    default_kwargs = {**default_kwarg_dictionary, **updated_kwargs}    
    plot_kwargs = {**default_kwargs, **plot_kwargs}     

    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
    ax.plot(df['P'], df['ET_summer'], 'o', color = '#a4a5ab', markersize = 12, lw = plot_kwargs['lw'],  markeredgecolor = plot_kwargs['markeredgecolor'], label = '')
    plot_kwargs['xlabel'] = r'$\mathrm{P}_{wy}\/\mathrm{(mm)}$'
    plot_kwargs['ylabel'] = r'$\mathrm{ET}_{dry}\/\mathrm{(mm)}$'
    plot_kwargs['legend'] = False
    ax.set_ylim(0,600)
    corr, p = stats.spearmanr(df[['P','ET_summer']])
    ax.annotate(r'$\rho$' + ' = ' + str(round(corr,2)) + '\n p-val = ' + str(round(p,4)),
                xy=(.88, .85), xycoords='figure fraction',
                horizontalalignment='right', verticalalignment='top',
                fontsize=10)
    ax.set_xlim(plot_kwargs['xmin'], plot_kwargs['xmax'])
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    if plot_kwargs['title'] is not None: fig.suptitle(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
        
    return fig


def plot_RWS(studyareaobject = None, df_deficit =  None, **plot_kwargs):
    print('Plotting RWS...')
    updated_kwargs = {'legend': False, 'lw':1}
    default_kwargs = {**default_kwarg_dictionary, **updated_kwargs}    
    plot_kwargs = {**default_kwargs, **plot_kwargs}    
    
    if studyareaobject is not None:
        df_d = studyareaobject.deficit_timeseries
        smax = studyareaobject.smax
    elif df_deficit is not None:
        df_d = df_deficit
        smax = df_deficit.max()
    
    df_d['RWS'] = df_d['D'] - smax
    df_d['RWS'] = df_d['RWS'] * -1
    df_d['date'] = pd.to_datetime(df_d['date'])

    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])

    ax.plot(df_d['date'], df_d['RWS'], plot_kwargs['linestyle_D'], color=plot_kwargs['color_D'], lw = plot_kwargs['lw'], label=r'$\mathrm{RWS(t)}\/\mathrm{(mm)}$')
    ax.set_xlim(pd.to_datetime(plot_kwargs['xmin'], exact = False), pd.to_datetime(plot_kwargs['xmax'], exact = False))
    if plot_kwargs['title'] is not None: fig.suptitle(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    return fig
        