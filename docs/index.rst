UCSCXenaToolsPy
===============

**Download and explore datasets from UCSC Xena data hubs**

UCSCXenaToolsPy is a Python port of the `R package UCSCXenaTools <https://github.com/ropensci/UCSCXenaTools>`_, providing access to cancer genomics datasets hosted by `UCSC Xena <https://xena.ucsc.edu/>`_.

.. code-block:: python

   from ucscxenatoolspy import (
       xena_generate, xena_filter, xena_query,
       xena_download, xena_prepare
   )

   # Discover TCGA datasets
   hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
   hub = xena_filter(hub, filter_cohorts="BRCA")
   query = xena_query(hub)

Quick Start
-----------

.. toctree::
   :maxdepth: 1

   getting-started

Tutorials
---------

.. toctree::
   :maxdepth: 1

   workflow-tutorial
   fetch-api-tutorial
   molecule-query-tutorial
   migration-from-r

API Reference
-------------

.. toctree::
   :maxdepth: 1

   api/index
