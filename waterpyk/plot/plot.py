########################## PLOTS ##########################
def plot(self, kind = 'timeseries', title = '', **plot_kwargs):
    default_plotting_kwargs = {
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
    plot_kwargs = {**default_plotting_kwargs, **plot_kwargs}

    fig, ax = plt.subplots(dpi=plot_kwargs['dpi'], figsize = plot_kwargs['figsize'])
    if title is not None: ax.set_title(title) 
    if kind == 'timeseries':
        df_wy = self.wateryear_timeseries
        df_d = self.deficit_timeseries
        df_wy['date'] = pd.to_datetime(df_wy['date'])
        df_d['date'] = pd.to_datetime(df_d['date'])

        if plot_kwargs['plot_Q']:
            if self.kind == 'watershed':
                ax.plot(df_wy['date'], df_wy['Q_cumulative'], plot_kwargs['linestyle_Q'], color=plot_kwargs['color_Q'], lw = plot_kwargs['lw'], label= 'Q (mm)')
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
        if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])

    elif kind == 'wateryear':
        df = self.wateryear_total
        if plot_kwargs['plot_PET']:
            print('Plotting PET!')
            ax.plot(df['wateryear'], df['PET'], plot_kwargs['linestyle_PET'], color = plot_kwargs['color_PET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{PET}_{wy}\/\mathrm{(mm)}$')
        if plot_kwargs['plot_P']:
            ax.plot(df['wateryear'], df['P'], plot_kwargs['linestyle_P'], color = plot_kwargs['color_P'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{P}_{wy}\/\mathrm{(mm)}$')
        if plot_kwargs['plot_Q']:
            if self.kind == 'watershed':
                ax.plot(df['wateryear'], df['Q'], plot_kwargs['linestyle_Q'], color = plot_kwargs['color_Q'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{Q}_{wy}\/\mathrm{(mm)}$')
        if plot_kwargs['twinx']:
            ax2 = ax.twinx()
            ax2.set_ylabel('ET (mm)', color = plot_kwargs['color_ET'])
        else: ax2 = ax
        if plot_kwargs['plot_ET']:
            ax2.plot(df['wateryear'], df['ET'], plot_kwargs['linestyle_ET'], color = plot_kwargs['color_ET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{ET}_{wy}\/\mathrm{(mm)}$')
        if plot_kwargs['plot_ET_dry']:
            ax2.plot(df['wateryear'], df['ET_summer'], ':o', color = plot_kwargs['color_ET'], lw = plot_kwargs['lw'], markeredgecolor = plot_kwargs['markeredgecolor'], label = r'$\mathrm{ET}_{dry}\/\mathrm{(mm)}$')
        ax.set_xlim(plot_kwargs['xmin'], plot_kwargs['xmax'])
        if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])
    elif kind == 'spearman':
        df = self.wateryear_total
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
    if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])

    if plot_kwargs['legend']: ax.legend(loc = 'best')
    
    # elif kind == 'location':
    #     self.site_geometry.plot(ax = ax, crs = self.site_geometry.crs.to_string())
    #     #bbox_gdf.boundary.plot(ax = ax)
    #     self.flowlines.plot(ax = ax, crs = self.site_geometry.crs.to_string())
    #     ctx.add_basemap(ax = ax, crs = self.site_geometry.crs.to_string())
    #     plt.title(self.description)
        
    elif kind == 'RWS':
        df_d = self.deficit_timeseries
        df_d['RWS'] = df_d['D'] - self.smax
        df_d['RWS'] = df_d['RWS'] * -1
        df_d['date'] = pd.to_datetime(df_d['date'])
        ax.plot(df_d['date'], df_d['RWS'], plot_kwargs['linestyle_D'], color=plot_kwargs['color_D'], lw = plot_kwargs['lw'], label=r'$\mathrm{RWS(t)}\/\mathrm{(mm)}$')
        ax.set_xlim(pd.to_datetime(plot_kwargs['xmin'], exact = False), pd.to_datetime(plot_kwargs['xmax'], exact = False))
        if plot_kwargs['title'] is not None: fig.suptitle([plot_kwargs['title']])

    return fig
        