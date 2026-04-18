Core API
========

XenaHub Model
-------------

.. autoclass:: ucscxenatoolspy.XenaHub
   :members:
   :undoc-members:
   :show-inheritance:

Accessors
---------

.. autofunction:: ucscxenatoolspy.hosts
.. autofunction:: ucscxenatoolspy.cohorts
.. autofunction:: ucscxenatoolspy.datasets
.. autofunction:: ucscxenatoolspy.samples

Defaults
--------

.. autofunction:: ucscxenatoolspy.xena_default_hosts

.. py:data:: DEFAULT_HOSTS

   Mapping of Xena host URLs to short names. Contains 12 default hubs including
   tcgaHub, gdcHub, icgcHub, and more. See :func:`xena_default_hosts` for usage.

Metadata
--------

.. autofunction:: ucscxenatoolspy.load_xena_data
.. autofunction:: ucscxenatoolspy.xena_data_update
