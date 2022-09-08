import os
from glob import glob

import fiona
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import rasterio as rio
from rasterio.mask import mask

from waterpyk import raster
from waterpyk import shapefile as shp


def file_finder(base_directory, file_type, skip_files=None, include_files=None, sub_dirs=4):
    """
    Get all of the files with designated file types (and filtered by include/skip files lists)
    for all of the subdirectories in the base directory. Get a list of paths and the names of those files.

    Args:
        base_directory (str): Directory to search for files in. Don't include the / at the end.
        file_type (str or list of str): File type(s) to search for. Include the period, ie '.tif' or provide a list of strings, like ['.tif', '.tiff'].
        skip_files (list of str, optional): List of files to skip. Just include the name of the file and the ending, i.e. ['image_of_cats.tif'] and not any folder/location information.
        include_files (list of str, optional): List of files to keep in the final list. Just include the name of the file and the ending, i.e. ['image_of_cats.tif'] and not any folder/location information.
        sub_dirs (int, optional): Number of sub-directory levels to look for files in. Default = 4.

    Returns:
        list, list: list of file locations and list of file names

    """
    def glob_options(file_type):
        endings = []
        for i in range(sub_dirs):
            endings.append('/**'*i + '/*' + file_type)
        return endings

    # If there is one file type, just get the glob_options
    if type(file_type) == str:
        endings = glob_options(file_type)
    # If there is a list of file types, get glob_options for all items in the list
    elif type(file_type) == list:
        endings = []
        for item in file_type:
            if type(item) == str:
                endings.append(glob_options(item))
            else:
                raise TypeError(
                    f'File_type can take a str (ex ".tif") or a list of strings. Recieved list of {type(item)}')
        # Flatten endings list
        endings = [item for sublist in endings for item in sublist]
    # If it is not a list of strings or a string, raise error
    else:
        raise TypeError(
            f'File_type can take a str (ex ".tif") or a list of strings. Recieved {type(file_type)}')

    file_paths = []
    for ending in endings:
        file_paths.append(glob(base_directory + ending))

    # Flatten file_paths list
    file_paths = [item for sublist in file_paths for item in sublist]

    # Remove skip_files
    if skip_files is not None:
        file_paths = [i for i in file_paths if i.split(
            '/')[-1] not in skip_files]

    # Remove all files not in include_files
    if include_files is not None:
        file_paths = [i for i in file_paths if i.split(
            '/')[-1] in include_files]

    # Get a name for each file for plotting, etc
    file_names = [str(i.split('/')[-1]).split('.')[0] for i in file_paths]

    return file_paths, file_names


def clip_raster_by_shapefile(raster_path, shapefile_path, target_epsg='4326', raster_save_dir='.', shape_save_dir='.', fig_save_dir='.', plot_result=False):
    # Reproject shapefile (will skip if not necessary
    shapefile_path = shp.reproject(save_dir=shape_save_dir,
                                   shapefile_path=shapefile_path,
                                   target_epsg=target_epsg)
    # Get geometry of shapefile
    with fiona.open(shapefile_path, "r") as shapefile:
        shapes = [feature["geometry"] for feature in shapefile]

    # Reproject raster (will skip if not necessary)
    raster_path = raster.reproject(save_dir=raster_save_dir,
                                   raster_path=raster_path,
                                   target_epsg=target_epsg)

    # Open reprojected raster and clip by reprojected hapefile
    with rio.open(raster_path) as src:
        out_image, out_transform = mask(dataset=src,
                                        shapes=shapes,
                                        crop=True)
        out_meta = src.meta

    # Update the metadata of the clipped raster
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    # Get a new name for the final raster
    name_r = str(raster_path.split('/')[-1]).split('.')[0]
    name_s = str(shapefile_path.split('/')[-1]).split('.')[0]
    dir_r = raster.add_slash(raster_save_dir)
    raster_save_path = dir_r + name_r + '_maskedby_' + name_s + '.tif'

    # Save the clipped raster to a new file
    with rio.open(raster_save_path, "w", **out_meta) as dest:
        dest.write(out_image)

    if plot_result == True:
        with rio.open(raster_save_path) as src:
            plt.imshow(src.read(1))
            dir_fig = raster.add_slash(fig_save_dir)
            plt.savefig(dir_fig + name_r + '_' + name_s + '.png')
