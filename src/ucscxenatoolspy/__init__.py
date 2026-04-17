"""UCSCXenaTools Python port — Download and explore UCSC Xena datasets."""

from ucscxenatoolspy.core.defaults import (
    xena_default_hosts,
    DEFAULT_HOSTS,
)
from ucscxenatoolspy.core.xena_hub import (
    XenaHub,
    hosts,
    cohorts,
    datasets,
)
from ucscxenatoolspy.core.xena_data import (
    load_xena_data,
    xena_data_update,
)
from ucscxenatoolspy.workflow.generate import xena_generate
from ucscxenatoolspy.workflow.filter import xena_filter
from ucscxenatoolspy.workflow.query import xena_query, QueryResult
from ucscxenatoolspy.workflow.download import xena_download
from ucscxenatoolspy.workflow.prepare import xena_prepare
from ucscxenatoolspy.fetch.dense import (
    fetch_dataset_samples,
    fetch_dataset_identifiers,
    has_probeMap,
    fetch_dense_values,
    fetch_sparse_values,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "XenaHub",
    "hosts",
    "cohorts",
    "datasets",
    "xena_default_hosts",
    "DEFAULT_HOSTS",
    "load_xena_data",
    "xena_data_update",
    # Workflow
    "xena_generate",
    "xena_filter",
    "xena_query",
    "xena_download",
    "xena_prepare",
    "QueryResult",
    # Fetch API
    "fetch_dataset_samples",
    "fetch_dataset_identifiers",
    "has_probeMap",
    "fetch_dense_values",
    "fetch_sparse_values",
]
