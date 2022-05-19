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
        # Ep = 0.0023 · (Tmean + 17.8)·(Tmax − Tmin)^0.5 · 0.408 · Rext
        Krs = 0.0023 # Erica changed this from 0.00023 on Oct 15, 2021
        pet_df['PET'] = Krs * pet_df['RA'] * np.sqrt(pet_df['tmax'] - pet_df['tmin']) * (((pet_df['tmin']+pet_df['tmax'])/2) + 17.8)
    
        return pet_df
        