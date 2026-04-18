# Workflow Tutorial

This guide walks through the core UCSCXenaToolsPy workflow: **Generate → Filter → Query → Download → Prepare**. This pipeline mirrors the R package's approach.

## Overview

```
xena_generate() ──> xena_filter() ──> xena_query() ──> xena_download() ──> xena_prepare()
  discover data     narrow scope     build URLs       fetch files          load as DataFrame
```

## Step 1: Discover Datasets

Start by loading the bundled metadata snapshot to see what's available:

```python
from ucscxenatoolspy import load_xena_data

xena_data = load_xena_data()
print(xena_data.columns)
# Index(['XenaHosts', 'XenaHostNames', 'XenaDatasets', 'XenaCohorts',
#        'XenaFields', 'XenaDataSubsets', 'ProbeMap', 'DatasetTags'], ...)
```

The key columns are:
- **XenaHosts**: Full URL of the Xena hub
- **XenaHostNames**: Short name (e.g. "tcgaHub")
- **XenaDatasets**: Dataset identifier
- **XenaCohorts**: Cohort/study name

### Scanning for datasets

Use `xena_scan` to search for datasets matching a pattern:

```python
from ucscxenatoolspy import xena_scan

# Find all datasets containing "clinical"
clinical = xena_scan("clinical")

# Find BRCA-related data
brca = xena_scan("BRCA")
```

### Refreshing metadata

The bundled metadata may become stale. Update from live servers:

```python
from ucscxenatoolspy import xena_data_update

# Returns updated DataFrame without saving
df = xena_data_update()

# Also saves the updated data locally
df = xena_data_update(save_to_local=True)
```

## Step 2: Generate

`xena_generate` creates a `XenaHub` object by subsetting the metadata DataFrame:

```python
from ucscxenatoolspy import xena_generate

# All TCGA datasets
hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")

# Multiple hosts
hub = xena_generate(subset=lambda df: df["XenaHostNames"].isin(["tcgaHub", "gdcHub"]))
```

The `subset` parameter replaces R's non-standard evaluation (NSE). In R you would write `XenaHostNames == "tcgaHub"`, but in Python you pass a callable that returns a boolean mask.

## Step 3: Filter

`xena_filter` narrows a `XenaHub` by cohort or dataset patterns using regex:

```python
from ucscxenatoolspy import xena_filter

# Filter by cohort pattern
hub = xena_filter(hub, filter_cohorts="BRCA")

# Filter by dataset pattern
hub = xena_filter(hub, filter_datasets="clinical")

# Combine cohort and dataset filters
hub = xena_filter(hub, filter_cohorts="BRCA|LUAD", filter_datasets="RNAseq")

# Case-sensitive matching
hub = xena_filter(hub, filter_datasets="Clinical", ignore_case=False)
```

At least one of `filter_cohorts` or `filter_datasets` must be provided.

## Step 4: Query

`xena_query` builds and validates download URLs for the filtered datasets:

```python
from ucscxenatoolspy import xena_query

result = xena_query(hub)
print(f"Found {result.n_files} files to download")

# Convert to DataFrame for inspection
df = result.to_dataframe()
print(df.head())
#   hosts              datasets  url
# 0  https://tcga...  tcga_A...   https://tcga...
```

`xena_query` performs HTTP HEAD requests to validate URLs and automatically appends `.gz` if the base URL returns a 404.

## Step 5: Download

`xena_download` fetches the validated files to disk:

```python
from ucscxenatoolspy import xena_download

# Download to a specific directory
result = xena_download(result, destdir="./xena_data")

# Options:
# force=True        — re-download even if file exists
# trans_slash=True  — replace '/' in filenames with '__'
# max_retries=5     — increase retry attempts
```

## Step 6: Prepare

`xena_prepare` loads downloaded TSV files into pandas DataFrames:

```python
from ucscxenatoolspy import xena_prepare

# Load all files
df = xena_prepare(result.urls)

# Load specific files
df = xena_prepare(["file1.tsv.gz", "file2.tsv.gz"])

# Chunked reading for large files
df = xena_prepare(
    result.urls,
    use_chunked=True,
    chunk_size=100,
)

# Custom processing callback
def normalize(df, idx):
    return (df - df.mean()) / df.std()

df = xena_prepare(result.urls, callback=normalize)
```

## Working with the XenaHub object

The `XenaHub` object holds your current selection:

```python
from ucscxenatoolspy import XenaHub, hosts, cohorts, datasets, samples

hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")

# Inspect
print(hub)
# class: XenaHub
# hosts():
#   https://tcga.xenahubs.net
# cohorts() (33 total):
#   TCGA-BRCA, TCGA-LUAD, ...
# datasets() (1560 total):
#   tcga_A..., ...

# Access individual components
host_list = hosts(hub)
cohort_list = cohorts(hub)
dataset_list = datasets(hub)

# Query sample IDs
all_samples = samples(hub, by="datasets", how="any")
brca_samples = samples(hub, i="TCGA-BRCA", by="cohorts", how="each")
```

### samples() modes

The `samples()` function supports three grouping modes (`by`) and three combination strategies (`how`):

| `by` | Description |
|------|-------------|
| `"hosts"` | Samples by host (using cohorts) |
| `"cohorts"` | Samples by cohort |
| `"datasets"` | Samples by dataset |

| `how` | Description |
|-------|-------------|
| `"each"` | Return samples for each item separately |
| `"any"` | Union — samples in any of the items |
| `"all"` | Intersection — samples in all items |

## ProbeMap Queries

For datasets with probe-to-gene mappings:

```python
from ucscxenatoolspy import xena_query_probe_map

hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
probe_map_df = xena_query_probe_map(hub)
```
