# Fetch API Tutorial

The Fetch API provides direct, low-level access to Xena data without the full workflow pipeline. Use it for quick lookups and targeted data retrieval.

## When to Use Fetch API vs Workflow

| Workflow | Fetch API |
|----------|-----------|
| Bulk download of many datasets | Quick lookup of specific data |
| Batch processing | Exploring a single dataset |
| Offline analysis (download once) | Real-time queries |

## Dataset Samples

Get sample IDs for a dataset:

```python
from ucscxenatoolspy import fetch_dataset_samples

samples = fetch_dataset_samples(
    "https://tcga.xenahubs.net",
    "tcga_HiSeqV2_PANCAN.gz"
)
print(samples[:5])
# ['TCGA-44-2659-01', 'TCGA-44-3919-01', ...]

# Limit results
samples = fetch_dataset_samples(
    "https://tcga.xenahubs.net",
    "tcga_HiSeqV2_PANCAN.gz",
    limit=10
)
```

## Dataset Identifiers

Get gene/probe identifiers for a dataset:

```python
from ucscxenatoolspy import fetch_dataset_identifiers

ids = fetch_dataset_identifiers(
    "https://tcga.xenahubs.net",
    "tcga_HiSeqV2_PANCAN.gz"
)
print(ids[:5])
# ['A1BG', 'A2M', 'A2ML1', ...]
```

## ProbeMap Support

Check if a dataset supports probe-to-gene mapping (querying by gene symbols instead of probe IDs):

```python
from ucscxenatoolspy import has_probeMap

# Returns True if probeMap is available
if has_probeMap("https://tcga.xenahubs.net", "tcga_HiSeqV2_PANCAN.gz"):
    print("Gene symbol queries available")

# Get the probeMap URL
url = has_probeMap(
    "https://tcga.xenahubs.net",
    "tcga_HiSeqV2_PANCAN.gz",
    return_url=True
)
```

## Dense Values

Query dense matrix data (e.g., gene expression, copy number):

```python
from ucscxenatoolspy import fetch_dense_values

# Query specific genes
values = fetch_dense_values(
    "https://tcga.xenahubs.net",
    "tcga_HiSeqV2_PANCAN.gz",
    identifiers=["TP53", "BRCA1", "EGFR"],
    use_probeMap=True,  # Use gene symbols instead of probe IDs
)

# Query specific samples
values = fetch_dense_values(
    "https://tcga.xenahubs.net",
    "tcga_HiSeqV2_PANCAN.gz",
    identifiers=["TP53"],
    samples=["TCGA-44-2659-01", "TCGA-44-3919-01"],
)
```

The `use_probeMap` parameter automatically handles probe-to-gene conversion when available.

## Sparse Values

Query sparse/mutation data:

```python
from ucscxenatoolspy import fetch_sparse_values

mutations = fetch_sparse_values(
    "https://tcga.xenahubs.net",
    "tcga_Mutation_PANCAN.gz",
    genes=["TP53", "KRAS", "PIK3CA"],
    samples=["TCGA-44-2659-01"],
)
```

Sparse data returns a dictionary mapping genes to their mutation information.

## The XenaClient Class

For custom queries beyond the helper functions, use `XenaClient` directly:

```python
from ucscxenatoolspy.api.client import XenaClient

client = XenaClient("https://tcga.xenahubs.net")

# Custom POST query
result = client.query("dataset/sparsity", "tcga_Mutation_PANCAN.gz")
```

The client handles connection pooling, retries, and error checking automatically.
