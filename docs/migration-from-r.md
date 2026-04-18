# Migration from R to Python

This guide helps users of the R package [UCSCXenaTools](https://github.com/ropensci/UCSCXenaTools) migrate to UCSCXenaToolsPy.

## Function Name Mapping

| R Function | Python Function | Notes |
|------------|-----------------|-------|
| `XenaHosts()` | `hosts(x)` | Takes XenaHub as argument |
| `XenaCohorts()` | `cohorts(x)` | Takes XenaHub as argument |
| `XenaDatasets()` | `datasets(x)` | Takes XenaHub as argument |
| `XenaGenerate()` | `xena_generate(subset=lambda df: ...)` | Uses callable instead of NSE |
| `XenaFilter()` | `xena_filter(x, filter_cohorts, filter_datasets)` | Similar signature |
| `XenaQuery()` | `xena_query(x)` | Returns QueryResult instead of S4 |
| `XenaDownload()` | `xena_download(result, destdir)` | Returns QueryResult |
| `XenaPrepare()` | `xena_prepare(urls)` | Returns pd.DataFrame |
| `XenaScan()` | `xena_scan(pattern)` | Returns pd.DataFrame |
| `XenaHub()` | `XenaHub(hosts, cohorts, datasets)` | Pydantic model instead of S4 |
| `XenaData` | `load_xena_data()` | Function call instead of lazy dataset |
| `samples()` | `samples(x, i, by, how)` | Similar signature |
| `XenaQueryProbeMap()` | `xena_query_probe_map(x)` | Returns pd.DataFrame |

## Key Differences

### 1. Non-Standard Evaluation → Lambda Functions

In R, you use NSE expressions:

```r
hub <- XenaGenerate(subset = XenaHostNames == "tcgaHub")
```

In Python, pass a callable that returns a boolean Series:

```python
hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
```

### 2. Pipe Operator → Explicit Variables

In R, you chain with `%>%`:

```r
hub <- XenaGenerate(...) %>%
    XenaFilter(filter_datasets = "clinical") %>%
    XenaQuery()
```

In Python, pass variables explicitly:

```python
hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
hub = xena_filter(hub, filter_datasets="clinical")
result = xena_query(hub)
```

### 3. S4 Objects → Pydantic Models

R uses S4 classes with slots accessed via `@`:

```r
hub@hosts
```

Python uses Pydantic frozen models with attribute access:

```python
hub.hosts
```

The model is immutable — filtering returns new instances.

### 4. Data Types

| R | Python |
|---|--------|
| S4 object | Pydantic `BaseModel` |
| R matrix / data.frame | `pd.DataFrame` |
| R list | `list` or `dict` |
| R factor | `str` |

### 5. Naming Conventions

- **Function names**: PascalCase in R → snake_case in Python (`XenaGenerate` → `xena_generate`)
- **Parameter names**: camelCase preserved (`filterDatasets` → `filter_datasets` in Python)

### 6. Immutability

Both R and Python implementations are immutable. Filtering or querying returns a new object rather than modifying in place.

## Feature Parity

| Feature | R | Python |
|---------|---|--------|
| Generate/Filter/Query/Download/Prepare | Yes | Yes |
| samples() with by/how modes | Yes | Yes |
| ProbeMap queries | Yes | Yes |
| Metadata management | Yes | Yes |
| TCGA built-in data | Yes | Yes |
| Molecule value queries | Yes | Yes |
| File caching | Yes | Yes |
| Interactive widgets | Yes | No |

## TCGA Built-in Data

Both packages provide built-in TCGA clinical and survival datasets:

**R:**
```r
tcga_clinical
tcga_survival
```

**Python:**
```python
from ucscxenatoolspy import tcga_clinical, tcga_survival

clinical = tcga_clinical()
survival = tcga_survival()
```

## Common Workflow: Side by Side

**R:**
```r
library(UCSCXenaTools)

hub <- XenaGenerate(subset = XenaHostNames == "tcgaHub") %>%
    XenaFilter(filter_cohorts = "BRCA")
query <- XenaQuery(hub)
XenaDownload(query, destdir = "./data")
df <- XenaPrepare(query)
```

**Python:**
```python
from ucscxenatoolspy import (
    xena_generate, xena_filter, xena_query,
    xena_download, xena_prepare,
)

hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
hub = xena_filter(hub, filter_cohorts="BRCA")
result = xena_query(hub)
result = xena_download(result, destdir="./data")
df = xena_prepare(result.urls)
```
