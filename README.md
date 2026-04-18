# ucscxenatoolspy

Python port of the R package [UCSCXenaTools](https://github.com/ropensci/UCSCXenaTools) — download and explore datasets from UCSC Xena data hubs.

## Installation

```bash
pip install ucscxenatoolspy
```

## Quick Start

### Workflow (Generate → Filter → Query → Download → Prepare)

```python
from ucscxenatoolspy import xena_generate, xena_filter, xena_query, xena_download, xena_prepare

# Generate: select datasets from metadata
hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")

# Filter: refine by patterns
hub = xena_filter(hub, filter_datasets="clinical")

# Query: build download URLs
query = xena_query(hub)

# Download: fetch files
result = xena_download(query)

# Prepare: load into pandas
data = xena_prepare(result)
```

### Fetch API (Direct queries without downloading)

```python
from ucscxenatoolspy import (
    fetch_dataset_samples,
    fetch_dataset_identifiers,
    fetch_dense_values,
    fetch_sparse_values,
    has_probeMap,
)

host = "https://toil.xenahubs.net"
dataset = "tcga_RSEM_gene_tpm"

# Get sample IDs
samples = fetch_dataset_samples(host, dataset, limit=10)

# Get gene/probe identifiers
identifiers = fetch_dataset_identifiers(host, dataset)

# Fetch expression values (with gene symbol via probeMap)
values = fetch_dense_values(
    host, dataset,
    identifiers=["TP53", "BRCA1"],
    samples=samples[:5],
    use_probeMap=True
)

# Check if dataset has probeMap
if has_probeMap(host, dataset):
    print("Gene symbol queries available")
```

### Query Molecule Value (Single ID & Genomic Signature)

```python
from ucscxenatoolspy import query_molecule_value

# Single gene — returns pd.Series indexed by sample
values = query_molecule_value(
    "ccle/CCLE_copynumber_byGene_2013-12-03",
    "TP53",
)

# Genomic signature formula — auto-queries each gene and evaluates
signature = query_molecule_value(
    "ccle/CCLE_copynumber_byGene_2013-12-03",
    "TP53 + 2 * KRAS - 1.3 * PTEN",
)
```

### Metadata

```python
from ucscxenatoolspy import load_xena_data, xena_data_update

# Load bundled metadata snapshot
df = load_xena_data()

# Fetch fresh metadata from all hubs
df = xena_data_update()
```

## Features

- **Core workflow**: Generate, Filter, Query, Download, Prepare (mirrors R package)
- **Fetch API**: Direct API queries for samples, identifiers, dense/sparse values
- **Query Molecule Value**: Single gene lookup and genomic signature formula evaluation
- **File caching**: Persistent disk cache for query results (configurable via `UCSCXENA_CACHE_DIR`)
- **ProbeMap support**: Query by gene symbols (via probe-to-gene mapping)
- **Metadata management**: Bundled snapshot + live update from 12 Xena hubs
- **R-compatible naming**: camelCase parameter names for easy migration

## API Reference

| Function | Description |
|----------|-------------|
| `xena_generate(subset)` | Select datasets from metadata |
| `xena_filter(hub, filter_cohorts, filter_datasets)` | Filter by regex patterns |
| `xena_query(hub)` | Build download URLs, validate with HEAD request |
| `xena_download(query)` | Download files with progress bar |
| `xena_prepare(result)` | Load TSV files into pandas DataFrame |
| `load_xena_data()` | Load bundled XenaData metadata |
| `xena_data_update()` | Fetch fresh metadata from all hubs |
| `fetch_dataset_samples(host, dataset)` | Get sample IDs |
| `fetch_dataset_identifiers(host, dataset)` | Get probe/gene identifiers |
| `fetch_dense_values(host, dataset, ...)` | Query dense matrix data |
| `fetch_sparse_values(host, dataset, ...)` | Query sparse/mutation data |
| `has_probeMap(host, dataset)` | Check probeMap availability |
| `query_molecule_value(dataset, molecule, host)` | Single gene or formula query (returns pd.Series) |
| `get_data(dataset, identifier, host)` | Fetch single identifier with caching |

## Supported Hubs

12 UCSC Xena hubs are supported by default:

| Hub Name | URL |
|----------|-----|
| tcgaHub | https://tcga.xenahubs.net |
| icgcHub | https://icgc.xenahubs.net |
| toilHub | https://toil.xenahubs.net |
| pancanAtlasHub | https://pancanatlas.xenahubs.net |
| gdcHub | https://gdc.xenahubs.net |
| ccleHub | https://ccle.xenahubs.net |
| gtexHub | https://gtex.xenahubs.net |
| atlasHub | https://atlas.xenahubs.net |
| xenaHub | https://xena.xenahubs.net |
| publicHub | https://public.xenahubs.net |
| pcaHub | https://pca.xenahubs.net |
| tdiHub | https://tdi.xenahubs.net |

## License

GPL-3.0 (same as original R package)