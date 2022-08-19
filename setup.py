import pathlib
from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.rst").read_text()

setup(
    name="waterpyk",
    version="2.1.0",
    description= "Extract, analyze, and plot hydrological timeseries for a site or watershed using the Google Earth Engine and USGS APIs",
    long_description=README,
    long_description_content_type="text/x-rst",
    url= "https://github.com/erica-mccormick/waterpyk",
    author="Erica L. McCormick",
    author_email= "erica.elmstead@gmail.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering :: GIS",
        "Development Status :: 4 - Beta"
    ],
    packages=find_packages(),
    include_package_data= True,
    package_data={'': ['layers_data/*.csv']}
)

