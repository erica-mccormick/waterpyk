import pandas as pd
import numpy as np
import datetime
import waterpyk.errors as err

def interp_daily(df):
    """Interpolate all data to daily.
        
        Args:
            :obj:`df`: initial long-form dataframe for a single asset (may contain multiple bands) with column 'value' for interpolating
        
        Returns:
           :obj:`df`: dataframe with 'value' column containing daily interpolated daily 
    """
    df_interp = pd.DataFrame()
    temp = pd.DataFrame()
    diff_days = (df.date.max() - df.date.min()).days
    temp['date'] = [df.date.min() + datetime.timedelta(days=x) for x in range(0, diff_days)]
    for i in df.band.unique():
        df_temp = df[df['band']==i]
        df_temp = df_temp.merge(temp, how = 'right', on = 'date')
        df_temp['value'] = df_temp['value'].interpolate(method = "linear")
        df_temp['band'] = i
        df_interp = pd.concat([df_interp,df_temp])
    return df_interp

def combine_bands(df, bands_to_combine, band_name_final):
    """
    Defaults to add together soil and vegetation ET bands (Es and Ec) for PML to create ET band.
    Can be customized to add any bands together to create a new band.
    
    Args:
        bands_to_combine (list of str): list of strings of band names (example: ['Es', 'Ec']) to combine into a single band
        band_name_final (str): the final band name to be stored in the 'band' column of the final dataframe, where the 'value' column will contain the added values from bands_to_combine
    
    Returns:
       :obj:`df`: long-form dataframe from input with appended section which contains date, asset_name, value, band, and value_raw (set to np.nan) columns with data from combined
    """
    to_store = pd.DataFrame()
    for i in bands_to_combine:
        if i == bands_to_combine[0]:
            to_store = df[df['band'] == i]
            to_store.loc[:,'value_raw'] = np.nan
        else:
            subset = df[df['band']==i][['date', 'value']]
            to_store = to_store.merge(subset, how = 'inner', on = 'date')
    val_cols = to_store.loc[:,to_store.columns.str.startswith("value")]
    to_store['value'] = val_cols.sum(axis=1)
    to_store['band'] = band_name_final
    to_store = to_store[['date', 'asset_name', 'value', 'band', 'value_raw']]
    df = pd.concat([df, to_store])
    #df = df.append(to_store)
    df = df.reset_index(drop=True)
    return df



def make_wide_df(df_long, **kwargs):
    """
    Uses ET and P asset and band names (designated in **kwargs) to return a wide-form dataframe with columns:
    date, ET, Ei, P, and P-Ei (where Ei is the interception band from PML and is only extracted if it exists). merge_wide_streamflow() can then be used to merge with streamflow df. 
    
    Args:
        df_long: dataframe such as that produced by extract_assets_at_site() where columns contain asset_name, band, and value.
        **et_asset (str, optional): asset to be used for creation of ET column (default 'pml').
        **et_band (str, optional): band name to be used for creation of ET column (default 'ET').
        **ppt_asset (str, optional): asset name for precipitation column (default 'prism').
        **ppt_band (str, optional): band name for precipitation colum (default 'ppt')
        
    Returns:
        :obj:`df`: wide-form dataframe with columns for date, ET, Ei, P, and P-Ei (where Ei is the interception band from PML and is only included if it exists.)
    """

    default_kwargs = {
        'et_asset': 'pml',
        'et_band': 'ET',
        'ppt_asset': 'prism',
        'ppt_band': 'ppt',
    }
    kwargs = {**default_kwargs, **kwargs} 
        
    # Isolate ET dataset
    et_df = df_long[df_long['asset_name'] == kwargs['et_asset']]
    et_df = et_df[et_df['band'] == kwargs['et_band']]
    et_df['ET'] = et_df['value']
    
    # Isolate P dataset
    ppt_df = df_long[df_long['asset_name'] == kwargs['ppt_asset']]
    ppt_df = ppt_df[ppt_df['band'] == kwargs['ppt_band']]
    ppt_df['P'] = ppt_df['value']
    
    # Merge P + Ei (interception) if Ei band exists
    if 'Ei' in et_df.band.unique():
        ei_df = et_df[et_df['band'] == 'Ei']
        ei_df['Ei'] = ei_df['value']
        ppt_df = ppt_df.merge(ei_df[['date','Ei']], how = 'left', on = 'date')
        ppt_df['P_min_Ei'] = ppt_df['P'] - ppt_df['Ei']
    
        # Merge ET and P
        df_wide = et_df.merge(ppt_df, how = 'inner', on = 'date')[['date', 'ET', 'P', 'P_min_Ei', 'Ei']]
    
    else:
        # Merge ET and P
        df_wide = et_df.merge(ppt_df, how = 'inner', on = 'date')[['date', 'ET', 'P']]
        
    # Add wateryear column
    df_wide = df_wide.set_index(pd.to_datetime(df_wide['date']))
    df_wide['wateryear'] = np.where(~df_wide.index.month.isin([10,11,12]),df_wide.index.year,df_wide.index.year+1)
    df_wide = df_wide.reset_index(drop=True)
    
    return df_wide


def merge(df_wide, df_merge, merge_with, column_names = None):
    """Merge df_wide (dataframe with columns representing variable names) with streamflow dataframe.
   
    Args:
        df_wide :obj:`df`): wide-form dataframe with 'date' column and other columns with variable names (ie ET, P, etc)
        df_merge (:obj:`df`): dataframe with stuff to merge (streamflow or deficit). Must contain columns for 'date' and column_names if given.
        merge_with (str): choice of 'streamflow' or 'deficit' to merge with df_wide.
        column_names (list of str): Names of the column in df_merge that you wish to merge (default for streamflow: ['Q_mm'], default for deficit: ['D', and 'D_wy']). 'date' is automatically included.
    
    Returns:
        :obj:`df`: merged dataframes.
    """
    # Make sure they are both datetime format
    df_wide['date'] = pd.to_datetime(df_wide['date'])
    df_merge['date'] = pd.to_datetime(df_merge['date'])

    if column_names is None: 
        if merge_with == 'streamflow':
            column_names = ['date','Q_mm']
        elif merge_with == 'deficit':
            column_names = ['date', 'D', 'D_wy']
        else:
            print('merge() works for deficit or streamflow dataframes only.')
    elif 'date' in column_names: pass
    else: column_names = column_names + ['date']
    df_wide = df_wide.merge(df_merge[column_names], how = 'left', on = 'date')
    return df_wide


def wateryear(df_wide):
    """Create total and cumulative wateryear dataframes for all variables (ie columns) given in df_wide.
    
    Args:
        df_wide (:obj:`df`): wide-form dataframe with 'date' column and other columns with variable names (i.e. ET, P, Q_mm, etc.) This dataframe can also have D, D_wy, Q_mm, etc merged into it.
    
    Returns:
        :obj:`df`, :obj:`df`: 2 datafrmes: (1) the  original wide-form dataframe with added columns (in the naming form of ORIGINALNAME_cumulative) with cumulative wateryear values. For example, if 'P' was in original dataframe, then 'P_cumulative' now exists. If 'Q_mm' was in dataframe, then 'Q_mm_cumulative' now exists. (2) dataframe with one row for each wateryear with columns such as wateryear, ET, P, D_wy_max, ET_summer, Q_mm, etc, which represent the total (or maximum, for D_wy_max) wateryear sum.
    """
     # Create wateryear total dataframe and fill in wateryear and Dwy_max if exists
    df_total = pd.DataFrame()
    df_total['wateryear'] = df_wide.groupby(['wateryear'])['wateryear'].first()
    if 'D_wy' in df_wide:
        df_total['D_wy_max'] = df_wide.groupby(['wateryear'])['D_wy'].max()
        
    # Add summer ET to total wateryear df
    df_summer = df_wide.copy()
    df_summer = df_summer.set_index(df_summer['date'])
    df_summer['season'] = np.where(~df_summer.index.month.isin([6,7,8,9]),'summer','other')
    df_summer = df_summer[df_summer['season'] == 'summer']
    df_total['ET_summer'] = df_summer.groupby(['wateryear'])['ET'].sum()

    # Add wateryear cumulative to df_wide
    cols = ['ET', 'P', 'Ei', 'P_min_Ei', 'Q_mm']
    for col in cols:
        if col in df_wide:
            df_wide[col + '_cumulative'] = df_wide.groupby(['wateryear'])[col].cumsum()
            df_total[col] = df_wide.groupby(['wateryear'])[col].sum()

    # Calculate dV if all data is present
    if 'P' and 'ET' and 'Q_mm' in df_wide:
        df_wide['dV'] = df_wide['P_cumulative'] - df_wide['ET_cumulative'] - df_wide['Q_mm_cumulative'] 
        
    return df_wide, df_total
    

def deficit(df_long, df_wide = None, **kwargs):
    """
    Calculate D(t) after McCormick et al., 2021 and Dralle et al., 2020.

    Args:
        df_long (:obj:`df`): original long-style dataframe with snow, P, and ET data at a minimum
        df_wide (:obj:`df`): dataframe created from make_wide_df(). (default = None, in which case new df_wide is created from df_long using default args). This dataframe must have ET, P, and wateryear columns.
        **interp: (bool, optional): default: True. Currently no option to change to False.
        **combine_ET_bands (bool, optional): (default True) add ET bands to make one ET band.
        **bands_to_combine (list of str, optional): (default [Es, Ec]) ET bands to combine
        **band_names_combined (str, optional): (default ET) name of combined ET band
        **et_asset (str, optional): (default pml) ET dataset to use for deficit calculation, if multiple are given
        **et_band (str, optional): (default ET) band from ET dataset to use for deficit calculation, if multiple are given
        **ppt_asset (str, optional): (default prism) precipitation dataset to use for deficit calculation, if multiple are given
        **ppt_band (str, optional): (default ppt) precipitation dataset to use for deficit calculation, if multiple are given
        **snow_band (str, optional): defaults to 'snow'. Note: You will need to change this if you don't specify to change the default name of this asset upon extraction.
        **snow_correction (bool, optional): (default True) use snow correction factor when calculating deficit
        **snow_correction (bool, optional): (default True) use snow correction factor when calculating deficit
        **snow_frac (int, optional): (default 10) set all ET when snow is greater than this (%) to 0 if snow_correction = True

    Returns:
        :obj:`df`: dataframe with root-zone water storage deficit data where deficit is column 'D' and wateryear deficit is 'D_wy'.
    """
    
    default_kwargs = {
            'et_asset': 'pml',
            'et_band': 'ET',
            'ppt_asset': 'prism',
            'ppt_band': 'ppt',
            'snow_asset':'modis_snow',
            'snow_band':'snow',
            'snow_correction': True,
            'snow_frac': 10,
        }
    kwargs = {**default_kwargs, **kwargs} 
    
    # Make deficit dataframe if none given (just normal wide dataframe but only keep relevant data)
    if df_wide is None:
        df_deficit = make_wide_df(df_long, pivot_all = False, **kwargs)
    else: df_deficit = df_wide.copy()
    
    # Check to make sure everything we need is here
    necessary_columns = ['date', 'ET', 'P', 'wateryear'] 
    for col in necessary_columns:
        if col not in df_deficit:
            raise err.MissingBandsError(col + ' missing. Deficit cannot be calculated. Check assets specified in layers.')
    
    df_deficit = df_deficit[necessary_columns]

    # If using snow_correction, add snow to df_wide
    if kwargs['snow_correction'] == True:
        try:  
            snow_df = df_long[df_long['asset_name'] == kwargs['snow_asset']]
            snow_df = snow_df[snow_df['band'] == kwargs['snow_band']]
            snow_df['Snow'] = snow_df['value']
            # Merge snow together and filter ET by snow fraction
            df_deficit = df_deficit.merge(snow_df, how = 'inner', on = 'date')
            df_deficit.loc[df_deficit['Snow'] > kwargs['snow_frac'], 'ET'] = 0
        except:
            raise err.MissingBandsError("Snow correction can't be applied. Either no snow data presented or snow_band or asset wrong. Given snow_band: {}, snow_asset: {}".format(kwargs['snow_band'], kwargs['snow_asset']))
   
    # Calculate A and D
    df_deficit['A'] = df_deficit['ET'] - df_deficit['P']
    df_deficit['D'] = 0
    for _i in range(df_deficit.shape[0]-1):
        df_deficit.loc[_i+1, 'D'] = max((df_deficit.loc[_i+1, 'A'] + df_deficit.loc[_i, 'D']), 0)
    
    # Calculate wateryear deficit (D(t)_wy)) and merge columns with df_deficit
    df_deficit_wy = pd.DataFrame()
    for wy in df_deficit.wateryear.unique():
        temp = df_deficit[df_deficit['wateryear'] == wy][['date','ET','P']]
        temp['A'] = temp['ET'] - temp['P']
        temp['D_wy'] = 0
        temp = temp.reset_index()
        for _i in range(temp.shape[0]-1):
            temp.loc[_i+1, 'D_wy'] = max((temp.loc[_i+1, 'A'] + temp.loc[_i, 'D_wy']), 0)
        df_deficit_wy = pd.concat([df_deficit_wy, temp])
    df_deficit_wy = df_deficit_wy[['date','D_wy']]
    df_deficit = df_deficit.merge(df_deficit_wy, how = 'left', on = 'date')
    #self.deficit_timeseries = df_deficit
    #self.smax = round(df_deficit.D.max())
    #self.maxdmax = round(df_deficit.D_wy.max())
    return df_deficit


def deficit_bursts(df):
    """
    Still under development!! Get a dataframe with the length and maximum deficit of each "burst" (i.e. deficits that are continuously above zero).

    Args:
        df (:obj:`df`): dataframe with columns for date and D (for deficit), at minimum.

    Returns: 
        :obj:`df`: dataframe with columns for start and end dates, and max_D [mm], duration [days] and start and end wateryear of each burst.
    """
    # get all places where deficit = 0
    df_zero = df[df.D == 0]

    # get the start and end dates of the bursts and add in an artificial 'burst' starting on the first date of the year and ending at the start of the next burst
    start_of_bursts = []
    end_of_bursts = []
    max_D = []

    # For all the dates where the deficit = 0, find the time between the dates and the maximum value between the dates
    for j in range(len(df_zero['date'])-1):
        if (df_zero['date'][j+1] > df_zero['date'][j]):
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

    return burstdf


"""
def getRA(site_lat_decimal):
  ## J (julian day)
  J = (np.linspace(1,365,365))
  ## Gsc (solar constant)  [MJ m-2 day -1] 
  Gsc = 0.0820
  ## inverse relative distance Earth-Sun
  dr = 1+0.033*np.cos(((2*np.pi)/365)*J) 
  ## delta = solar declination [rad]
  delta = 0.409*np.sin(((2*np.pi)/365)*J-1.39)  
  ## psi [rad] = convert decimal latitude to radians
  psi = (np.pi/180)*(32.3863) 
  ## omega_s (ws)= solar time angle at beginning of period [rad]
  omega_s = np.arccos(-np.tan(psi)*np.tan(delta)) 
  ## [ws * sin(psi) * sin(delta) + cos(psi) * cos(delta) * sin(ws)]
  angles = omega_s * np.sin(psi) * np.sin(delta) + np.cos(psi) * np.cos(delta) * np.sin(omega_s)
  RA = ((24*60)/np.pi) * Gsc * dr * angles

  df = pd.DataFrame()
  df['RA'] = RA
  df['J'] = J
  df['J']= df['J'].astype(int)
  return df


def calculate_PET(daily_data_df, latitude):#gage, p, tmin = 'tmin', tmax = 'tmax', tmean = 'tmean'):
    if 'tmax' and 'tmin' not in daily_data_df['band'].unique():
        sys.exit("'PET cannot be calsculated because PRISM temperature was not extracted.'")  
    else:
        # Get temperatures from prism
        prism_df = daily_data_df[daily_data_df['asset_name'] == 'prism']
        pet_df = pd.DataFrame()
        pet_df['tmax'] = prism_df[prism_df['band'] == 'tmax']['value'].values
        pet_df['tmin'] = prism_df[prism_df['band'] == 'tmin']['value'].values
        pet_df['date'] = pd.to_datetime(prism_df[prism_df['band'] == 'tmin']['date']).values

        # get RA (extraterrestrial radiation) with julian day column
        RA_df = getRA(latitude)
        pet_df['J'] = pd.to_datetime(pet_df['date']).dt.strftime('%j')
        pet_df['J'] = pet_df['J'].astype(int)
        
        # merge prism df with RA
        pet_df = pet_df.merge(RA_df, how='left', on=['J'])

        # calculate PET (Hargreave and Semani 1985)
        # Ep = 0.0023 · (Tmean + 17.8)·(Tmax - Tmin)^0.5 · 0.408 · Rext
        Krs = 0.0023 # Erica changed this from 0.00023 on Oct 15, 2021
        pet_df['PET'] = Krs * pet_df['RA'] * np.sqrt(pet_df['tmax'] - pet_df['tmin']) * (((pet_df['tmin']+pet_df['tmax'])/2) + 17.8)
    
        return pet_df
"""      