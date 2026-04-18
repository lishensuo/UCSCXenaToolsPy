# Molecule Query Tutorial

The `query_molecule_value` and `get_data` functions provide convenient lookups for single genes or genomic signatures across samples.

## Single Gene Lookup

Use `get_data` to fetch expression or copy number values for a single gene:

```python
from ucscxenatoolspy import get_data

# Get TP53 copy number values
values = get_data(
    dataset="ccle/CCLE_copynumber_byGene_2013-12-03",
    identifier="TP53",
    host="https://broad.xenahubs.net",
)

print(values.head())
# LC4S_LUNG       -0.43
# SW620_INTESTINE   0.05
# ...

print(values.shape)  # pd.Series indexed by sample
```

If `host` is not provided, the function auto-detects it from the dataset path.

## Genomic Signature Formula

`query_molecule_value` supports genomic signature formulas — mathematical expressions combining multiple genes:

```python
from ucscxenatoolspy import query_molecule_value

# Single gene (same as get_data)
values = query_molecule_value(
    "ccle/CCLE_copynumber_byGene_2013-12-03",
    "TP53",
)

# Genomic signature: a weighted combination of genes
signature = query_molecule_value(
    "ccle/CCLE_copynumber_byGene_2013-12-03",
    "TP53 + 2 * KRAS - 1.3 * PTEN",
)
```

### Supported Formula Syntax

The formula parser supports:

- Basic arithmetic: `+`, `-`, `*`, `/`
- Numeric literals: `1.5`, `2`, `0.3`
- Gene names (auto-detected as identifiers)
- Math functions: `sqrt()`, `log()`, `log2()`, `log10()`, `exp()`, `abs()`, `round()`

Examples:

```python
# Simple ratio
query_molecule_value("dataset", "BRCA1 / BRCA2")

# Log-transformed expression
query_molecule_value("dataset", "log2(TP53 + 1)")

# Complex signature
query_molecule_value("dataset", "sqrt(abs(EGFR)) + 0.5 * KRAS")
```

## File Caching

Both `get_data` and `query_molecule_value` use persistent disk caching to avoid redundant API calls:

```python
# Caching is enabled by default
values = get_data("ccle/CCLE_copynumber_byGene_2013-12-03", "TP53")

# Disable caching for a single call
values = get_data("ccle/CCLE_copynumber_byGene_2013-12-03", "TP53", cache=False)
```

### Cache Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `UCSCXENA_CACHE_DIR` | `~/.cache/ucscxenatoolspy` | Cache directory location |
| Cache key | MD5 hash | Computed from identifier + dataset + host |

Set a custom cache directory via environment variable:

```bash
export UCSCXENA_CACHE_DIR="/path/to/custom/cache"
```

Or in Python before importing:

```python
import os
os.environ["UCSCXENA_CACHE_DIR"] = "/path/to/custom/cache"

from ucscxenatoolspy import get_data
```

## Auto Host Detection

If you don't specify `host`, the functions attempt to auto-detect it from the dataset path by checking the default Xena hubs:

```python
# Auto-detects host from dataset "ccle/CCLE_copynumber_byGene_2013-12-03"
values = query_molecule_value(
    "ccle/CCLE_copynumber_byGene_2013-12-03",
    "TP53",
)
```

If auto-detection fails, an error is raised with a hint to specify the host manually.
