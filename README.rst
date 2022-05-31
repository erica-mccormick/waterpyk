

waterpyk is a simple package for extracting data from the `Google Earth Engine`_ (GEE) and USGS APIs and performing simple water-balance analyses.
All you need to begin is a lat/long or a `USGS gauge ID`_ to start.

For more information on the root-zone water storage capacity and deficit, see `Dralle et al., 2021`_, `McCormick et al., 2021`_, and `Rempe, McCormick et al. (in prep)`_.

Get started
***************

Install waterpyk:
TBD.

To get all of the available data and plots for a site, simply supply a list of coordinates (such as ``[lat, long]`` or [``gaugeID``]):

``from waterpyk install main``

``yoursitename = main.StudyArea(COORDS)``

All of the dataframes will now be available in the form of:

* ``yoursitename.deficit_timeseries``
* ``yoursitename.daily_df_wide``
* ``yoursitename.streamflow``
* ``yoursitename.wateryear_totals``

You can also use ``yoursite.describe`` to see more information, or ``yoursite.smax`` to see Smax.

To plot, simply use ``yoursite.plot(kind = ###)`` and supply a string for which kind (see below).

Read the docs
*************

For full documentation, see `full documentation`_

What waterpyk can do
*********************

* Download timeseries of GEE assets and:

  * Combining bands

  * Applying a scaling factor

  * Interpolating to daily

* Download streamflow for gauged watersheds

* Download watershed information, such as:

  * Boundary and flowline geometry (as GEE or geopandas format)

  * Metadata (such as CRS, name, and gauge ID)

  * Daily discharge (in native units, and converted to mm)

  * Centroid latitude (for calculation of Hargreaves PET)

  * URLs necessary to access all of the above directly

* Calculate cumulative and total wateryear timeseries

* Calculate the root-zone water storage (RWS) deficit

* Create 4 figures, out of the box, with P, ET, Q, and deficit data, including:
 
  * Wateryear cumulative timeseries (``kind = 'wateryear'``)
 
  * Daily timeseries, with options (``kind = 'timeseries'``)
 
  * Plot & calculate Spearman correlation coefficient for summer ET and wateryear P (``kind = 'spearman'``)
 
  * RWS capacity (Smax) relative to P distribution (``kind = 'distribution'``)
 
  * RWS timeseries (``kind = 'RWS'``)


Contact
*******

This is a work in progress and is primarily intended for the Rempe Lab Group and co-authors.
For more information, contact Erica McCormick at erica.mccormick@utexas.edu or the email address given on her `homepage`_.

.. note::

   This project is under active development.


.. _Dralle et al., 2021: https://ericamccormick.com/pdfs/Dralle2021_HESS.pdf
.. _Rempe, McCormick et al. (in prep): https://eartharxiv.org/repository/view/3356/
.. _McCormick et al., 2021: https://ericamccormick.com/pdfs/McCormick_Nature2021.pdf
.. _USGS gauge ID: https://waterdata.usgs.gov/nwis/rt
.. _Google Earth Engine: https://developers.google.com/earth-engine/guides/getstarted
.. _homepage: https://www.ericamccormick.com
.. _full documentation: https://waterpyk.readthedocs.io/en/latest/

