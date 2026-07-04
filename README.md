# ucscxenatoolspy

Python port of the R package [UCSCXenaTools](https://github.com/ropensci/UCSCXenaTools) — download and explore datasets from UCSC Xena data hubs.

[Documentation](https://ucscxenatoolspy.readthedocs.io/)

## Installation

**From PyPI (recommended):**

```bash
pip install ucscxenatoolspy
```

**From local source:**

```bash
# Clone or download the source code first
pip install .              # standard install
pip install -e .           # editable install (for development)
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

## TCGA Analysis API

A FastAPI web service providing statistical analysis on TCGA gene expression data. Start the server and query via browser or `curl`.

> **Live Demo**: A temporary instance is deployed at **[https://ucscxenatoolspy.onrender.com](https://ucscxenatoolspy.onrender.com)** — try it directly without local setup:
>
> ```bash
> curl https://ucscxenatoolspy.onrender.com/health
> curl "https://ucscxenatoolspy.onrender.com/api/v1/diff-expr?gene=TP53&cancer=LUAD"
> ```
>
> ⚠️ Render free tier spins down after inactivity; the first request may take ~30 seconds to wake up.

Install the optional API dependencies before running the service:

```bash
pip install "ucscxenatoolspy[api]"

# or, from a local checkout
pip install -e ".[api]"
```

### Start the server

```bash
cd ucscxenatoolspy
uvicorn ucscxenatoolspy.api_service.main:app --reload --port 8765
```

Interactive docs at [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs).

### Public deployment settings

For an internet-facing deployment, configure these environment variables before starting `uvicorn`:

```bash
# Require clients to send X-API-Key: <one-of-these-values>
UCSCXENA_API_KEYS="change-me,second-key"

# Restrict browser callers to your frontend domains
UCSCXENA_CORS_ORIGINS="https://example.org,https://app.example.org"

# Disable interactive docs on the public host
UCSCXENA_ENABLE_DOCS=false

# If running behind a trusted reverse proxy, use X-Forwarded-For / X-Real-IP
UCSCXENA_TRUST_PROXY_HEADERS=true

# Use shared rate-limit state across workers/containers
UCSCXENA_RATE_LIMIT_STORAGE_URI="redis://localhost:6379/0"

# Bound expensive analysis work
UCSCXENA_ANALYSIS_CONCURRENCY=4
UCSCXENA_ANALYSIS_TIMEOUT_SECONDS=120

# Optional: disable external mygene fallback for unknown identifiers
UCSCXENA_ENABLE_MYGENE=false
```

### Deployment guide

The API is a normal ASGI application:

```text
ucscxenatoolspy.api_service.main:app
```

A minimal production deployment usually has `uvicorn` running on localhost and a reverse proxy such as Nginx or Caddy handling HTTPS, public routing, and request size/time limits.

1. Install the package on the server.

```bash
git clone <your-repo-url>
cd ucscxenatoolspy
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[api]"
```

2. Create an environment file for the service, for example `/etc/ucscxena-api.env`.

```bash
UCSCXENA_API_KEYS=replace-with-a-long-random-key
UCSCXENA_CORS_ORIGINS=https://your-frontend.example.org
UCSCXENA_ENABLE_DOCS=false
UCSCXENA_TRUST_PROXY_HEADERS=true
UCSCXENA_ANALYSIS_CONCURRENCY=4
UCSCXENA_ANALYSIS_TIMEOUT_SECONDS=120
UCSCXENA_RATE_LIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
```

`UCSCXENA_API_KEYS` is optional for private/internal deployments, but recommended for any public endpoint. If you run multiple workers, containers, or servers, configure `UCSCXENA_RATE_LIMIT_STORAGE_URI` so rate limits are shared; otherwise slowapi falls back to in-memory state per process.

3. Start the API locally.

```bash
uvicorn ucscxenatoolspy.api_service.main:app \
  --host 127.0.0.1 \
  --port 8765 \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips 127.0.0.1
```

Keep `--workers 1` unless you have configured Redis-backed rate limiting and have enough memory for repeated TCGA analysis workloads. Increase `UCSCXENA_ANALYSIS_CONCURRENCY` before increasing ASGI workers when you mainly need more parallel analysis capacity.

4. Manage the process with systemd.

```ini
[Unit]
Description=ucscxenatoolspy TCGA Analysis API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/ucscxenatoolspy
EnvironmentFile=/etc/ucscxena-api.env
ExecStart=/opt/ucscxenatoolspy/.venv/bin/uvicorn ucscxenatoolspy.api_service.main:app --host 127.0.0.1 --port 8765 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

After saving it as `/etc/systemd/system/ucscxena-api.service`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ucscxena-api
sudo systemctl status ucscxena-api
```

5. Put Nginx in front of the local service.

```nginx
server {
    listen 80;
    server_name api.example.org;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
    }
}
```

Enable HTTPS with your normal certificate workflow, for example certbot or your platform load balancer. The FastAPI app should stay bound to `127.0.0.1` unless you intentionally expose it directly.

6. Verify the deployment.

```bash
curl https://api.example.org/health
curl -H "X-API-Key: replace-with-a-long-random-key" \
  "https://api.example.org/api/v1/diff-expr?gene=TP53&cancer=LUAD"
```

The expected health response is `{"status":"ok"}`. If docs are enabled for a non-public staging instance, the OpenAPI UI is available at `/docs`.

### Endpoints

| Method | Path | Rate | Description |
|--------|------|------|-------------|
| GET | `/health` | none | Health check for monitoring probes |
| GET | `/` | 60/min | API info and endpoint listing |
| GET | `/api/v1/cancers` | 60/min | List all 33+ cancers with tumor/normal sample counts |
| GET | `/api/v1/diff-expr` | 10/min | Differential expression: tumor vs normal (Wilcoxon) |
| GET | `/api/v1/corr` | 10/min | Spearman correlation between two genes in tumors |
| GET | `/api/v1/survival` | 5/min | Survival analysis: gene expression vs 4 endpoints (log-rank) |

Legacy `/api/*` paths redirect to `/api/v1/*` with a `308 Permanent Redirect`.

### Differential Expression

```
GET /api/v1/diff-expr?gene=TP53&cancer=LUAD
```

```json
{
  "gene": "TP53",
  "cancer": "LUAD",
  "cancer_full_name": "Lung adenocarcinoma",
  "dataset": "tcga_RSEM_gene_tpm",
  "tumor":   {"n": 501, "mean": 5.887, "median": 5.799},
  "normal":  {"n": 119, "mean": 4.123, "median": 4.001},
  "log2_fold_change": 1.764,
  "p_value": 2.3e-15,
  "test": "Wilcoxon rank-sum (Mann-Whitney U, two-sided)"
}
```

Parameters:
- `gene` - HUGO gene symbol or supported identifier (TP53, EGFR, HER2, 7157, ENSG00000141510). Aliases and IDs are resolved with mygene and must map to a gene present in `tcga_RSEM_gene_tpm`.
- `cancer` - TCGA abbreviation, case-insensitive (LUAD, brca, KIRC, ...). Requires at least 3 normal samples (e.g. LAML returns 400).

`log2_fold_change` is computed as the tumor mean minus the normal mean because `tcga_RSEM_gene_tpm` values are already log2(TPM + 0.001) transformed.

### Gene Correlation

```
GET /api/v1/corr?gene1=TP53&gene2=EGFR&cancer=LUAD
```

```json
{
  "gene1": "TP53",
  "gene2": "EGFR",
  "cancer": "LUAD",
  "cancer_full_name": "Lung adenocarcinoma",
  "sample_type": "primary_tumor",
  "n": 501,
  "spearman_r": 0.1234,
  "p_value": 0.0056,
  "test": "Spearman rank correlation (two-sided)"
}
```

Only primary tumor (TP) samples are used. Requires at least 5 common samples after intersecting both genes' expression data.

### Survival Analysis

```
GET /api/v1/survival?gene=TP53&cancer=LUAD
```

```json
{
  "gene": "TP53",
  "cancer": "LUAD",
  "cancer_full_name": "Lung adenocarcinoma",
  "sample_type": "primary_tumor",
  "test": "Log-rank test",
  "survival": {
    "OS": {
      "name": "Overall Survival",
      "n_total": 501, "n_events": 187,
      "median_cutoff": {
        "method": "median",
        "cutoff": 5.799,
        "high": {"n": 251, "n_events": 80, "mean_survival_days": 1200.5},
        "low":  {"n": 250, "n_events": 107, "mean_survival_days": 900.3},
        "p_value": 0.012
      },
      "optimal_cutoff": {
        "method": "optimal_cutoff",
        "cutoff": 6.234,
        "high": {"n": 150, "n_events": 35, "mean_survival_days": 1500.2},
        "low":  {"n": 351, "n_events": 152, "mean_survival_days": 800.1},
        "p_value": 0.0003
      },
      "optimal_cutoff_note": "Exploratory minimum-p scan across candidate cutoffs; p_value is not adjusted for multiple cutoff testing."
    },
    "DSS": { ... },
    "DFI": { ... },
    "PFI": { ... }
  }
}
```

Four survival endpoints: OS (Overall), DSS (Disease-Specific), DFI (Disease-Free Interval), PFI (Progression-Free Interval). Each evaluated with **median cutoff** (high vs low expression split at median) and **optimal cutoff** (scanned across p25-p75 for the smallest log-rank p value, minimum 10% in each group). The optimal-cutoff p value is exploratory and is not adjusted for testing multiple cutoffs. Requires at least 10 samples with both expression and survival data.

### Gene Alias Resolution

The API accepts multiple gene identifier formats and resolves them automatically:

| Input type | Example | Resolution |
|------------|---------|------------|
| Standard symbol | `TP53` | Exact match (instant) |
| Common alias | `HER2` | mygene -> `ERBB2` |
| Entrez Gene ID | `7157` | mygene -> `TP53` |
| Ensembl ID | `ENSG00000141510` | mygene -> `TP53` |
| Case-insensitive | `tp53` | Case-insensitive lookup -> `TP53` |

When a gene is resolved (not an exact match), the response includes `gene_input` with the original query string.

### Architecture

```text
src/ucscxenatoolspy/api_service/
  main.py        # FastAPI app, routes, middleware, rate limiting
  analysis.py    # Core stats: Wilcoxon, Spearman, log-rank
  gene_utils.py  # Gene name resolution (exact -> case-insensitive -> mygene)
  cache_utils.py # In-memory TTL cache with LRU eviction
  gene_list.txt  # Bundled valid gene list from tcga_RSEM_gene_tpm
```

Security: gene input is length-bounded and limited to gene identifier characters (`^[A-Za-z0-9][A-Za-z0-9@._-]{0,29}$`), rate limiting per endpoint, error messages sanitized (URLs and retry info stripped), `X-Request-ID` on every response.

### Quick Test

```bash
# List available cancers
curl http://127.0.0.1:8765/api/v1/cancers | python -m json.tool

# Differential expression
curl "http://127.0.0.1:8765/api/v1/diff-expr?gene=TP53&cancer=LUAD" | python -m json.tool

# Gene correlation
curl "http://127.0.0.1:8765/api/v1/corr?gene1=TP53&gene2=EGFR&cancer=LUAD" | python -m json.tool

# Survival analysis
curl "http://127.0.0.1:8765/api/v1/survival?gene=TP53&cancer=LUAD" | python -m json.tool

# Health check
curl http://127.0.0.1:8765/health
```

## AI Assistant Skills

Pre-built integrations that let AI coding assistants (Claude Code, OpenAI Codex, Cursor) query the TCGA Analysis API directly — ask about gene expression, correlation, or survival in natural language (English or Chinese), and the assistant answers with data from the API.

### Supported Platforms

| Platform | Directory | Type |
|----------|-----------|------|
| **Claude Code** | `skills/claude/xena-tcga-gene-query/` | Skill (SKILL.md + helper script) |
| **OpenAI Codex** | `skills/codex/xena-tcga-gene-query/` | Agent (agent config + helper script) |
| **Cursor** | `skills/cursor/xena-tcga-gene-query/` | Rule (.mdc + helper script) |

### What They Do

Each skill/agent/rule teaches the AI assistant to:

- **List cancers** — what TCGA cancers are available, which have normal tissue controls
- **Differential expression** — tumor vs normal comparison for a gene (Wilcoxon test)
- **Gene correlation** — Spearman correlation between two genes in primary tumors
- **Survival analysis** — expression-associated survival across OS, DSS, DFI, PFI (log-rank)
- **Cancer name mapping** — resolves Chinese/English common names (肺癌→LUAD+LUSC, 乳腺癌→BRCA, etc.) and gene aliases (HER2→ERBB2)

The assistant queries the deployed API at `https://ucscxenatoolspy.onrender.com` by default, so no local server setup is required.

### Install a Skill

**Claude Code** — register the skill globally or per-project:

```bash
# Per-project (from repo root)
cp -r skills/claude/xena-tcga-gene-query .claude/skills/

# Or install into your user skills directory
cp -r skills/claude/xena-tcga-gene-query ~/.claude/skills/
```

Then restart Claude Code and ask: *"Is TP53 upregulated in LUAD?"*

**Cursor** — copy the rule into your project:

```bash
cp skills/cursor/xena-tcga-gene-query/xena-tcga-gene-query.mdc .cursor/rules/
```

The rule is set to `alwaysApply: true`, so it activates automatically in every chat.

**OpenAI Codex** — register as a custom agent:

Place the `skills/codex/xena-tcga-gene-query/` directory in your Codex agents directory, or use the Codex dashboard to create an agent from `agents/openai.yaml`.

### Example Queries

Once the skill is installed, you can ask questions like:

| English | Chinese |
|---------|---------|
| "Is TP53 upregulated in LUAD?" | "TP53在肺癌中高表达吗？" |
| "Are EGFR and KRAS co-expressed in lung cancer?" | "EGFR和KRAS在肺癌中共表达吗？" |
| "Does HER2 expression affect breast cancer survival?" | "HER2高表达影响乳腺癌预后吗？" |
| "What cancers have normal tissue controls?" | "哪些癌症有正常组织对照？" |
| "Show me correlation between TP53 and MDM2 in GBM" | "TP53和MDM2在胶质母细胞瘤中的相关性" |

The assistant will call the API endpoints and synthesize results with proper scientific framing (sample sizes, p-values, exploratory vs confirmatory caveats).

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
