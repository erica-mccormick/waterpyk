import os

import numpy as np
import rasterio as rio
from rasterio import warp
from rasterio.crs import CRS


def add_slash(path):
    """
    Silly workaround to ensure filepaths are correct when saving.
    This will be replaced by proper os.path usage at some point.
    """
    if path[-1] != '/':
        path = path + '/'
    return path


def info(raster_path):
    """
    Print information about a raster, including the file name, CRS, shape of
    the resulting array, and, if it is a projected CRS, the units and scale information.
    Returns the result of .read, which is a numpy array of all bands of the raster.

    Args:
        raster_path (str): path to the .tif or .tiff file that will be opened by rasterio.

    Returns:
        array: the opened rasterio is converted to a numpy array and returned.

    """
    with rio.open(raster_path) as src:
        name = str(raster_path.split('/')[-1])  # .split('.')[0]
        print(f"{'Name': <13}: {name}")
        print(f"{'CRS': <13}: {src.crs}")
        print(f"{'Projected': <13}: {src.crs.is_projected}")
        if src.crs.is_projected:
            print(f"{'Units': <13}: {src.crs.linear_units}")
            print(f"{'Factor (m)': <13}: {src.crs.linear_units_factor}")
        array = src.read()
        print(f"{'band,row,col': <13}: {array.shape}")
    return array


def reproject(save_dir, raster_path, target_epsg='4326'):
    """
    Reproject raster and save it in a new place. Checks for validity of
    target EPSG code. Returns path to saved, reprojected raster, which has the original
    file name plus the ending '_[target_epsg]'. Currently,
    the pixel size is set to be able to change slightly to optimize the reprojection.
    This won't change the pixel sizes very much, however these defaults could be changed in the future.

    Args:
        save_dir (str): path to the directory where the reprojected raster should be saved.
        raster_path (str): path the original raster
        target_epsg (str, optional): EPSG code to reproject to. Defaults to '4326'.

    Returns:
        str: path to reprojected raster

    """
    # Perform checks
    if type(target_epsg) != str:
        raise TypeError(f'target_epsg must be str. Got {type(target_epsg)}')
    if os.path.exists(raster_path) == False:
        raise FileNotFoundError(f'{raster_path} does not exist.')
    if os.path.exists(save_dir) == False:
        raise FileNotFoundError(f'{save_dir} does not exist.')
    # Check if epsg code is valid
    crs_test = CRS.from_epsg(target_epsg)
    if crs_test.is_epsg_code == False:
        raise ValueError(f'Target EPSG code {target_epsg} is not valid.')

    # Get name of raster and format crs name
    file_name = str(raster_path.split('/')[-1]).split('.')[0]
    dst_crs = 'EPSG:' + target_epsg

    with rio.open(raster_path) as src:
        if src.crs == 'EPSG:' + target_epsg:
            save_path = raster_path
            print(f'No reproject: {file_name}.tif already in {target_epsg}).')
        else:
            # Make save_path, checking for right number of backslashes
            save_dir = add_slash(save_dir)
            save_path = save_dir + file_name + '_epsg' + target_epsg + '.tif'

            # Open the raster, check current crs, and update metadata
            with rio.open(raster_path) as src:
                print(
                    f'Reprojecting {file_name}.tif from {src.crs} to {target_epsg}')
                transform, width, height = warp.calculate_default_transform(
                    src.crs, dst_crs, src.width, src.height, *src.bounds)
                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': dst_crs,
                    'transform': transform,
                    'width': width,
                    'height': height
                })

                # Perform reprojection and save reprojected version
                with rio.open(save_path, 'w', **kwargs) as dst:
                    for i in range(1, src.count + 1):
                        warp.reproject(
                            source=rio.band(src, i),
                            destination=rio.band(dst, i),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=transform,
                            dst_crs=dst_crs,
                            resampling=warp.Resampling.nearest)
    return save_path
