import os

import geopandas as gpd

from waterpyk.raster import add_slash


def reproject(save_dir, shapefile_path, target_epsg='4326'):
    """"
    Reproject a shapefile using geopandas. Save reprojected shapefile with ending '_[target_epsg]'. 
    Returns path to reprojected shapefile.

    Args:
        save_dir (str): path to directory to save reprojected shapefile.
        shapefile_path (str): path to original file.
        target_epsg (str, optional): EPSG code to reproject to. Defaults to '4326'.

    Returns:
        str: path to reprojected shapefile
    """
    # Perform checks
    if type(target_epsg) != str:
        raise TypeError(f'target_epsg must be str. Got {type(target_epsg)}')
    if os.path.exists(shapefile_path) == False:
        raise FileNotFoundError(f'{shapefile_path} does not exist.')
    if os.path.exists(save_dir) == False:
        raise FileNotFoundError(f'{save_dir} does not exist.')

    # Read shapefile, get name, and check if path has '/' at end
    gdf = gpd.read_file(shapefile_path)
    file_name = str(shapefile_path.split('/')[-1]).split('.')[0]
    save_dir = add_slash(save_dir)

    # Reproject geodataframe if necessary
    if gdf.crs != 'epsg:' + target_epsg:
        print(f'Reprojecting {file_name}.shp from {gdf.crs} to {target_epsg}')
        gdf = gdf.to_crs(epsg=target_epsg)
        save_path = save_dir + file_name + '_epsg' + target_epsg + '.shp'
        gdf.to_file(save_path)

    else:
        print(f'No reproject: {file_name}.shp already in {target_epsg}).')
        save_path = save_dir

    return save_path
