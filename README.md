# ucscxenatoolspy

Python port of the R package [UCSCXenaTools](https://github.com/ropensci/UCSCXenaTools) — download and explore datasets from UCSC Xena data hubs.

[Documentation](https://ucscxenatoolspy.readthedocs.io/)

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
# class: XenaHub
# hosts():
#   https://tcga.xenahubs.net
# cohorts() (38 total):
#   TCGA Ovarian Cancer (OV), TCGA Kidney Clear Cell Carcinoma (KIRC), ...
# datasets() (715 total):
#   TCGA.OV.sampleMap/HumanMethylation27, ...  (715 total)

# Filter: refine by patterns
hub = xena_filter(hub, filter_datasets="LUSC_clinicalMatrix")
# class: XenaHub
# hosts():
#   https://tcga.xenahubs.net
# cohorts() (1 total):
#   TCGA Lung Squamous Cell Carcinoma (LUSC)
# datasets() (1 total):
#   TCGA.LUSC.sampleMap/LUSC_clinicalMatrix

# Query: build download URLs
query = xena_query(hub)
# This will check url status, please be patient.
# QueryResult(hosts=['https://tcga.xenahubs.net'], datasets=['TCGA.LUSC.sampleMap/LUSC_clinicalMatrix'],
#             urls=['https://tcga.xenahubs.net/download/TCGA.LUSC.sampleMap/LUSC_clinicalMatrix'], destfiles=[])

# Download: fetch files
result = xena_download(query)
# All downloaded files will be under: C:\Users\xxx\AppData\Local\Temp

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
# ['TCGA-19-1787-01', 'TCGA-S9-A7J2-01', 'TCGA-G3-A3CH-11', 'TCGA-EK-A2RE-01',
#  'TCGA-44-6778-01', 'TCGA-F4-6854-01', 'TCGA-AB-2863-03', 'TCGA-C8-A1HL-01',
#  'TCGA-EW-A2FS-01', 'TCGA-IR-A3L7-01']

# Get gene/probe identifiers
identifiers = fetch_dataset_identifiers(host, dataset)
# ['ENSG00000000003.14', 'ENSG00000000005.5', 'ENSG00000000419.12',
#  'ENSG00000000457.13', 'ENSG00000000460.16', ...]

# Fetch expression values (with gene symbol via probeMap)
values = fetch_dense_values(
    host, dataset,
    identifiers=["TP53", "BRCA1"],
    samples=samples[:5],
    use_probeMap=True
)
#       TCGA-19-1787-01  TCGA-S9-A7J2-01  TCGA-G3-A3CH-11  TCGA-EK-A2RE-01  TCGA-44-6778-01
# TP53            5.887            5.517            2.382            4.591            5.299
# BRCA1           3.475            1.930            0.670            3.392            2.674

# Check if dataset has probeMap
if has_probeMap(host, dataset):
    print("Gene symbol queries available")
# Gene symbol queries available
```

### Query Molecule Value of Selected dataset (Recommended)

```python
from ucscxenatoolspy import query_molecule_value

# Single gene — returns pd.Series indexed by sample
values = query_molecule_value(
    "tcga_RSEM_gene_tpm",
    "TP53",
)
# TCGA-19-1787-01    5.887
# TCGA-S9-A7J2-01    5.517
# TCGA-G3-A3CH-11    2.382
# TCGA-EK-A2RE-01    4.591
# TCGA-44-6778-01    5.299
# TCGA-F4-6854-01    6.864
# Name: TP53, Length: 10535, dtype: float64

# Genomic signature formula — auto-queries each gene and evaluates
signature = query_molecule_value(
    "tcga_RSEM_gene_tpm",
    "TP53 + KRAS",
)
# Querying multiple identifiers: TP53, KRAS
# TCGA-19-1787-01     9.838
# TCGA-S9-A7J2-01     9.501
# TCGA-G3-A3CH-11     4.198
# TCGA-EK-A2RE-01     8.202
# TCGA-44-6778-01     9.363
# TCGA-F4-6854-01    10.254
# Name: TP53 + KRAS, Length: 10535, dtype: float64
```

### Datsets Metadata (See documentation for more details)

```python
from ucscxenatoolspy import load_xena_data, xena_data_update

# Load bundled metadata snapshot
df = load_xena_data()
# shape: (2314, 17)
# columns: XenaHosts, XenaHostNames, XenaCohorts, XenaDatasets,
#          SampleCount, DataSubtype, Label, Type, AnatomicalOrigin,
#          SampleType, Tags, ProbeMap, LongTitle, Citation, Version, Unit, Platform

# Fetch fresh metadata from all hubs
df = xena_data_update()
# Fetching metadata from UCSC Xena hubs...
#   [1/12] Querying tcgaHub... 715 datasets
#   [2/12] Querying icgcHub... ...
#   ...
# Total: 2314 datasets from 12 hosts
```

### Built-in general phenotype for TCGA samples

```python
from ucscxenatoolspy import tcga_clinical, tcga_survival

# Clinical annotations (Sample, Cancer, Age, Stage, Grade, etc.)
clinical = tcga_clinical()
#           Sample Cancer   Age Code  Gender Stage_ajcc Stage_clinical Grade
# 0  TCGA-OR-A5J1-01    ACC  58.0   TP    MALE   Stage II            NaN   NaN
# 1  TCGA-OR-A5J2-01    ACC  44.0   TP  FEMALE   Stage IV            NaN   NaN
# 2  TCGA-OR-A5J3-01    ACC  23.0   TP  FEMALE  Stage III            NaN   NaN
# 3  TCGA-OR-A5J4-01    ACC  23.0   TP  FEMALE   Stage IV            NaN   NaN
# 4  TCGA-OR-A5J5-01    ACC  30.0   TP    MALE  Stage III            NaN   NaN
# 5  TCGA-OR-A5J6-01    ACC  29.0   TP  FEMALE   Stage II            NaN   NaN

# Survival endpoints (OS, DSS, DFI, PFI with time)
survival = tcga_survival()
#           Sample   OS  OS.time  DSS  DSS.time  DFI  DFI.time  PFI  PFI.time
# 0  TCGA-OR-A5J1-01  1.0   1355.0  1.0    1355.0  1.0     754.0  1.0     754.0
# 1  TCGA-OR-A5J2-01  1.0   1677.0  1.0    1677.0  NaN       NaN  1.0     289.0
# 2  TCGA-OR-A5J3-01  0.0   2091.0  0.0    2091.0  1.0      53.0  1.0      53.0
# 3  TCGA-OR-A5J5-01  1.0    365.0  1.0     365.0  NaN       NaN  1.0      50.0
# 4  TCGA-OR-A5J6-01  0.0   2703.0  0.0    2703.0  0.0    2703.0  0.0    2703.0
# 5  TCGA-OR-A5J7-01  1.0    490.0  1.0     490.0  NaN       NaN  1.0     162.0
```

## Features

- **Core workflow**: Generate, Filter, Query, Download, Prepare (mirrors R package)
- **Fetch API**: Direct API queries for samples, identifiers, dense/sparse values
- **Query Molecule Value**: Single gene lookup and genomic signature formula evaluation
- **Built-in TCGA data**: Clinical annotations and survival endpoints included out of the box
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
| `tcga_clinical()` | Load built-in TCGA clinical annotations |
| `tcga_survival()` | Load built-in TCGA survival endpoints |

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