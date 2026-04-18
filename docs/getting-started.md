# Getting Started

## What is UCSC Xena?

[UCSC Xena](https://xena.ucsc.edu/) is a visualization and exploration tool for functional genomics data. It hosts large-scale cancer genomics datasets including TCGA, ICGC, Pan-Cancer Atlas, and more. UCSCXenaToolsPy provides programmatic access to these datasets from Python.

## Relationship to the R Package

UCSCXenaToolsPy is a Python port of the [R package UCSCXenaTools](https://github.com/ropensci/UCSCXenaTools). It mirrors the R package's workflow pattern (Generate → Filter → Query → Download → Prepare) and uses compatible naming conventions (camelCase parameters, snake_case functions).

See the [Migration Guide](migration-from-r.md) for a detailed comparison.

## Installation

```bash
pip install ucscxenatoolspy
```

Requirements:

- Python 3.10+
- pandas, httpx, pydantic, pyarrow, tqdm

## Quick Start

The core workflow in five steps:

```python
from ucscxenatoolspy import (
    xena_generate, xena_filter, xena_query,
    xena_download, xena_prepare,
)

# 1. Generate: select all TCGA datasets
hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")

# 2. Filter: narrow to BRCA clinical data
hub = xena_filter(hub, filter_datasets="clinical")

# 3. Query: build and validate download URLs
result = xena_query(hub)

# 4. Download: fetch the files
result = xena_download(result, destdir="./data")

# 5. Prepare: load into pandas DataFrames
df = xena_prepare(result.urls)
```

## Supported Hubs

| Hub Name | URL |
|----------|-----|
| publicHub | https://ucscpublic.xenahubs.net |
| tcgaHub | https://tcga.xenahubs.net |
| gdcHub | https://gdc.xenahubs.net |
| icgcHub | https://icgc.xenahubs.net |
| toilHub | https://toil.xenahubs.net |
| pancanAtlasHub | https://pancanatlas.xenahubs.net |
| treehouseHub | https://xena.treehouse.gi.ucsc.edu:443 |
| pcawgHub | https://pcawg.xenahubs.net |
| atacseqHub | https://atacseq.xenahubs.net |
| singlecellHub | https://previewsinglecell.xenahubs.net |
| kidsfirstHub | https://kidsfirst.xenahubs.net |
| tdiHub | https://tdi.xenahubs.net |

You can list all default hosts programmatically:

```python
from ucscxenatoolspy import xena_default_hosts, DEFAULT_HOSTS

# All host URLs
urls = xena_default_hosts()

# A specific host URL
url = xena_default_hosts("tcgaHub")
```

## Dataset Catalog

Browse all 2314 datasets from 11 hubs in the [interactive catalog](xena-datasets-catalog.html). It supports:

- **Search** — filter by any keyword (gene name, cohort, dataset ID)
- **Sort** — click any column header
- **Page size** — choose 10 / 25 / 50 / 100 rows per page
- **Copy CSV** — one-click export of the filtered results

## Next Steps

- [Workflow Tutorial](workflow-tutorial.md) — step-by-step guide to the full pipeline
- [Fetch API Tutorial](fetch-api-tutorial.md) — direct API queries for quick lookups
- [API Reference](api/index) — complete function reference
