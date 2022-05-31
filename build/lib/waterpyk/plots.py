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
        'color_WY': False,
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
    """Plot distribution of wateryear precipitation (P) and root-zone water storage capacity (Smax) in the form of
    Rempe-McCormick et al. (in prep) Fig 1c,f. 
    Either studyarea object must be supplied OR the df_wateryear_totals and smax param with the necessary data for plotting.
    
    Args:
        studyareaobject (object from studyarea class, optional):
        df_wateryear_totals (:obj:`df`, optional): dataframe with wateryear cumulative P and a column named 'P' at minimum.
        smax (int or float, optional): value for root-zone water storage capacity (Smax) in mm
        **xmin (int, optional): default = 0
        **xmax (int, optional): default = 4000
        **xlabel (str, optional): default = 'mm'
        **ylabel (str, optional): default = 'Density'
        **dpi (int, optional): default = 300
        **figsize (tuple, optional): default = (6,4)
        **legend (bool, optional): default = True
        **title (str, optional): default = None
        
    Returns:
        :obj:`fig`
    """
    
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
    return fig

def plot_timeseries(studyareaobject = None, df_daily_wide = None, deficit_timeseries = None, **plot_kwargs):
    """Plot daily (wateryear cumulative) timeseries, following Rempe-McCormick et al. (in prep) Fig 1b,e. 
    Either studyarea object must be supplied OR the df_daily_wide and df_timeseries params with the necessary data for plotting.
    Use **kwargs to choose which datasets to plot, from the options of P, ET, deficit, deficit_wateryear, and streamflow (Q) if available.
    
    Args:
        studyareaobject (object from studyarea class, optional):
        df_daily_wide (:obj:`df`, optional): dataframe with daily cumulative wateryear timeseries and columns corresponding to the chosen data (from **kwargs), at minimum, such as 'ET_cumulative', 'P_cumulative', and 'Q_mm_cumulative', and 'date' columns.
        deficit_timeseries (:obj:`df`, optional): dataframe with deficit timeseries and columns 'D', 'D_wy' and 'date' at minimum.
        **xmin (str, optional): default = '2003-10-01'
        **xmax (str, optional): default = '2020-10-01'
        **xlabel (str, optional): default = 'Date'
        **ylabel (str, optional): default = '[mm]'
        **dpi (int, optional): default = 300
        **figsize (tuple, optional): default = (6,4)
        **legend (bool, optional): default = True
        **title (str, optional): default = None
        **plot_Q (bool, optional): default = False
        **plot_P (bool, optional): default = True
        **plot_D (bool, optional): default = True
        **plot_Dwy (bool, optional): default = True
        **plot_ET (bool, optional): default = False
        **plot_ET_dry (bool, optional): default = False
        **color_Q (str, optional): default = 'blue'
        **color_P (str, optional): default = '#b1d6f0'
        **color_D (str, optional): default = 'black'
        **color_Dwy (str, optional): default = 'black'
        **color_ET (str, optional): default = 'purple'
        **linestyle_Q (str, optional): default = '-'
        **linestyle_P (str, optional): default = '-'
        **linestyle_D (str, optional): default = '-'
        **linestyle_Dwy (str, optional): default = '--'
        **linestyle_ET (str, optional): default = '-'
        **lw (float, optional): lineweight, default = 1.5
        
    Returns:
        :obj:`fig`
    """
    
    print('Plotting timeseries...')
    plot_kwargs = {**default_kwarg_dictionary, **plot_kwargs}    
    
    if studyareaobject is not None:
        df_wy = studyareaobject.daily_df_wide
        df_d = studyareaobject.deficit_timeseries
    elif df_daily_wide is not None:
        df_wy = df_daily_wide
        df_d = deficit_timeseries
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
    if plot_kwargs['title'] is not None: ax.set_title(plot_kwargs['title'])
    if plot_kwargs['legend'] == True: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    return fig


def plot_wateryear_totals(studyareaobject = None, df_wateryear_totals = None, **plot_kwargs):
        
    """Plot summed wateryear timeseries. 
    Either studyarea object must be supplied OR the df_wateryear_totals param with the necessary data for plotting.
    Use **kwargs to choose which datasets to plot, from the options of P, ET, ET_summer, deficit, and streamflow (Q) if available.

    Args:
        studyareaobject (object from studyarea class, optional):
        df_wateryear_totals (:obj:`df`, optional): dataframe with cumulative wateryear timeseries and columns corresponding to the chosen data (from **kwargs), at minimum, such as 'P', 'D', 'ET', 'ET_summer', and 'Q_mm', and 'wateryear' columns.
        **xmin (int, optional): default = 2003
        **xmax (int, optional): default = 2020
        **xlabel (str, optional): default = 'Wateryear'
        **ylabel (str, optional): default = '[mm]'
        **dpi (int, optional): default = 300
        **figsize (tuple, optional): default = (6,4)
        **legend (bool, optional): default = True
        **title (str, optional): default = None
        **plot_Q (bool, optional): default = True
        **plot_P (bool, optional): default = True
        **plot_D (bool, optional): default = True
        **plot_ET (bool, optional): default = True
        **plot_ET_dry (bool, optional): default = False
        **color_Q (str, optional): default = 'blue'
        **color_P (str, optional): default = '#b1d6f0'
        **color_D (str, optional): default = 'black'
        **color_ET (str, optional): default = 'purple'
        **linestyle_Q (str, optional): default = '-o'
        **linestyle_P (str, optional): default = '-o'
        **linestyle_D (str, optional): default = '-'
        **linestyle_ET (str, optional): default = '-o'
        **lw (float, optional): lineweight, default = 1.5
        **twinx (bool, optional): Put ET data on twin x-axis to P data. default = True
        
    Returns:
        :obj:`fig`
    """
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
    if plot_kwargs['title'] is not None: ax.set_title(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    return fig



def plot_spearman(studyareaobject = None, df_wateryear_totals = None, **plot_kwargs):
    """Scatter plot of wateryear precipitation and summer (ie dry season) ET, following Rempe-McCormick et al. (in prep) Fig 1b,e.
    Spearman correlation coefficient (rho) and p-value is given in upper right corner of plot. 
    Either studyarea object must be supplied OR the df_wateryear_totals param with the necessary data for plotting (ie wateryear, P, and ET_summer columns).
    
    Args:
        studyareaobject (object from studyarea class, optional):
        df_wateryear_totals (:obj:`df`, optional): dataframe with columns 'P', 'ET_summer', and 'wateryear'
        deficit_timeseries (:obj:`df`, optional): dataframe with deficit timeseries and columns 'D', 'D_wy' and 'date' at minimum.
        **xmin (int, optional): default = 0
        **xmax (int, optional): default = 3000
        **dpi (int, optional): default = 300
        **figsize (tuple, optional): default = (6,4)
        **color_WY (bool, optional): This puts a wateryear legend and colors the dots by wateryear. default = True
        **title (str, optional): default = None
        **markeredgecolor (str, optional): default = 'black'
        **lw (float, optional): lineweight, default = 1.5
        
    Returns:
        :obj:`fig`
    """
    
    print('Plotting spearman...')
    if studyareaobject is not None:
        df = studyareaobject.wateryear_totals
    elif df_wateryear_totals is not None:
        df = df_wateryear_totals
    else:
        print('No data was specified for plotting')

    # Get kwargs set up
    updated_kwargs = {'xmin':0, 'xmax':3000, 'color_WY': True}
    default_kwargs = {**default_kwarg_dictionary, **updated_kwargs}    
    plot_kwargs = {**default_kwargs, **plot_kwargs}     

    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])

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
    if plot_kwargs['title'] is not None: ax.set_title(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    if plot_kwargs['color_WY']:
        cax = fig.add_axes([0.14, 0.15, 0.05, 0.70]) #[left, bottom, width, height]
        my_cmap = plt.get_cmap('tab20', 17)
        im = ax.scatter(df['P'], df['ET_summer'], c = df.wateryear, vmin=2004, vmax=2021, cmap = my_cmap, s = 150, edgecolor = 'black')
        fig.colorbar(im, cax=cax, orientation='vertical', spacing='proportional')
    else:
        ax.plot(df['P'], df['ET_summer'], 'o', color = '#a4a5ab', markersize = 12, lw = plot_kwargs['lw'],  markeredgecolor = plot_kwargs['markeredgecolor'], label = '')
    return fig


def plot_RWS(studyareaobject = None, df_deficit =  None, smax = None, **plot_kwargs):
    """Plot root-zone water storage (RWS) timeseries, following Rempe-McCormick et al. (in prep) SI Fig 1. 
    Either studyarea object must be supplied OR the df_deficit and smax params with the necessary data for plotting (ie columns for 'D' and 'date' and smax value)
    
    Args:
        studyareaobject (object from studyarea class, optional):
        deficit_timeseries (:obj:`df`, optional): dataframe with deficit timeseries and columns 'D', and 'date' at minimum.
        smax (int or float, optional): root-zone water storage capacity (Smax) in mm
        **xmin (str, optional): default = '2003-10-01'
        **xmax (str, optional): default = '2020-10-01'
        **xlabel (str, optional): default = 'Date'
        **ylabel (str, optional): default = 'RWS (mm)'
        **dpi (int, optional): default = 300
        **figsize (tuple, optional): default = (6,4)
        **legend (bool, optional): default = False
        **title (str, optional): default = None
        **color_D (str, optional): default = 'black'
        **linestyle_D (str, optional): default = '-'
        **lw (float, optional): lineweight, default = 1
        
    Returns:
        :obj:`fig`
    """
    
    print('Plotting RWS...')
    updated_kwargs = {'legend': False, 'lw':1, 'ylabel': 'RWS (mm)'}
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
    if plot_kwargs['title'] is not None: ax.set_title(plot_kwargs['title'])
    if plot_kwargs['legend']: ax.legend(loc = 'best')
    ax.set_xlabel(plot_kwargs['xlabel'])
    ax.set_ylabel(plot_kwargs['ylabel'])
    return fig
        
        
