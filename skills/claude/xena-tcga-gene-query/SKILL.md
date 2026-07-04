---
name: xena-tcga-gene-query
description: Query TCGA tumor biology through the ucscxenatoolspy FastAPI service. Use when a user asks in English or Chinese about a gene in cancer, tumor, carcinoma, lung cancer, breast cancer, TCGA, differential expression, prognosis, survival, co-expression, correlation, biomarker relevance. English examples: "Is TP53 upregulated in LUAD?", "Are EGFR and KRAS co-expressed in lung cancer?", "Does HER2 expression affect breast cancer survival?", "What cancers have normal tissue controls?", "Show me correlation between TP53 and MDM2 in GBM", "Is there a survival difference for high vs low PD-L1 in melanoma?". Chinese examples: "TP53在肺癌中的作用", "EGFR和肺癌有什么关系", "HER2在乳腺癌预后如何", "KRAS和TP53在胰腺癌中是否共表达?", "列出所有可以做差异表达分析的癌症", "PD-L1高表达是否影响黑色素瘤患者生存?", "肝癌中MET和EGFR的相关性如何?". Supports tumor-vs-normal expression, gene-gene correlation, survival association, sample counts, and alias/ID resolution.
---

# TCGA Gene Tumor Query

## Overview

Use the deployed ucscxenatoolspy API to answer gene-cancer questions for tumor scientists. The default base URL is `https://ucscxenatoolspy.onrender.com`; override it if the user gives another deployment URL or `UCSCXENA_API_BASE_URL` is set.

This skill supports four API tasks:

- List cancers and tumor/normal sample counts.
- Compare tumor vs normal expression for one gene in one TCGA cancer.
- Correlate two genes in primary tumor samples for one TCGA cancer.
- Evaluate expression-associated survival across OS, DSS, DFI, and PFI.

## Quick Workflow

1. Confirm the API service is running before any biological query:
   - Check the base URL, e.g. `curl https://ucscxenatoolspy.onrender.com/`, and verify it returns service metadata.
   - Check `curl https://ucscxenatoolspy.onrender.com/health` and verify it returns an OK status.
   - If either check fails, stop and report the connection error instead of querying task endpoints.
2. Normalize the user request into one or more API tasks.
3. Query the API directly with `curl` — simplest, no dependency or path issues:
   - `curl https://ucscxenatoolspy.onrender.com/api/v1/cancers`
   - `curl "https://ucscxenatoolspy.onrender.com/api/v1/diff-expr?gene=TP53&cancer=LUAD"`
   - `curl "https://ucscxenatoolspy.onrender.com/api/v1/corr?gene1=TP53&gene2=EGFR&cancer=LUAD"`
   - `curl "https://ucscxenatoolspy.onrender.com/api/v1/survival?gene=TP53&cancer=LUAD"`
4. The helper script `scripts/query_tcga_api.py` provides compact one-line summaries via its `summarize()` function. Use it when you want deterministic formatting:
   - `python .claude/skills/xena-tcga-gene-query/scripts/query_tcga_api.py diff-expr --gene TP53 --cancer LUAD`
5. If API key auth is enabled, pass `-H "X-API-Key: VALUE"` with curl, or `--api-key VALUE` with the script.
6. Interpret JSON conservatively for a tumor scientist:
   - Report sample sizes before effect sizes.
   - Report p-values as statistical associations, not causality.
   - For survival, distinguish median cutoff from optimal cutoff; optimal cutoff is exploratory and minimum-p based.
   - Mention missing normal samples or insufficient sample errors plainly.
6. Include the endpoint, gene/cancer inputs, and any alias resolution shown by `gene_input`, `gene1_input`, or `gene2_input`.

## Task Selection

Use `/api/v1/cancers` when the user asks what cancers are available or whether normal tissue controls exist.

Use `/api/v1/diff-expr` when the user asks whether a gene is up- or down-regulated in a tumor type, e.g. "TP53 in LUAD tumor vs normal".

Use `/api/v1/corr` when the user asks whether two genes co-vary in tumor samples, e.g. "EGFR and MET correlation in GBM".

Use `/api/v1/survival` when the user asks whether high expression of a gene is prognostic or associated with survival in a cancer.

For broad biological questions, run the smallest set of relevant endpoints and synthesize. Example: "Is TP53 important in LUAD?" usually means differential expression plus survival; add correlation only if a second gene or pathway partner is mentioned.

## Natural Language Cancer Mapping

When users use common Chinese or broad cancer names, map them to TCGA cancer codes before querying. If one common name maps to multiple TCGA subtypes, query the main relevant subtypes and explain that the disease category is heterogeneous.

For complete TCGA abbreviations, read `references/tcga_codes.md` when the cancer name is uncommon, ambiguous, or not covered below.

Common mappings:

- Lung cancer / 肺癌: query LUAD and LUSC unless the user specifies adenocarcinoma or squamous carcinoma.
- Lung adenocarcinoma / 肺腺癌: LUAD.
- Lung squamous cell carcinoma / 肺鳞癌: LUSC.
- Breast cancer / 乳腺癌: BRCA.
- Colon cancer / 结肠癌: COAD; colorectal cancer / 结直肠癌: consider COAD and READ.
- Liver cancer / 肝癌: LIHC.
- Gastric cancer / 胃癌: STAD.
- Prostate cancer / 前列腺癌: PRAD.
- Pancreatic cancer / 胰腺癌: PAAD.
- Glioblastoma / 胶质母细胞瘤: GBM; lower-grade glioma / 低级别胶质瘤: LGG.
- Kidney cancer / 肾癌: consider KIRC, KIRP, and KICH unless subtype is specified.

For broad questions like "TP53在肺癌中的作用" or "What is the role of TP53 in lung cancer?", do not answer only from general knowledge. Use this API to query LUAD and LUSC differential expression and survival, then synthesize with cautious biological interpretation.

## Running The Helper Script

Before running task-specific commands, confirm the local service is reachable:

```bash
curl https://ucscxenatoolspy.onrender.com/
curl https://ucscxenatoolspy.onrender.com/health
```

Then, from any working directory, run:

```bash
python .claude/skills/xena-tcga-gene-query/scripts/query_tcga_api.py cancers
python .claude/skills/xena-tcga-gene-query/scripts/query_tcga_api.py diff-expr --gene TP53 --cancer LUAD
python .claude/skills/xena-tcga-gene-query/scripts/query_tcga_api.py corr --gene TP53 --gene2 EGFR --cancer LUAD
python .claude/skills/xena-tcga-gene-query/scripts/query_tcga_api.py survival --gene TP53 --cancer LUAD
```

Common options:

- `--base-url https://ucscxenatoolspy.onrender.com` overrides the API URL.
- `--api-key VALUE` sends `X-API-Key: VALUE`.
- `--timeout 120` adjusts request timeout seconds.
- `--json` returns raw JSON without a short human summary.

If Python is unavailable, call the same endpoints with `curl` or the available HTTP tool. See `references/api.md` for endpoint details and interpretation notes.

## Response Style

Use concise scientific language:

- "In LUAD, TP53 expression is higher in tumor than normal in this dataset (tumor n=..., normal n=..., log2-scale difference=..., Mann-Whitney p=...)."
- "The survival association is exploratory for the optimal cutoff; validate externally before treating it as a biomarker threshold."
- "This API uses TCGA/toil expression and TCGA clinical/survival annotations; it does not prove mechanism or clinical utility."

When results conflict across endpoints, do not force a single conclusion. Say which association is supported and which is not.

## Safety And Limits

Do not present API results as medical advice, diagnostic guidance, or treatment recommendations. Frame outputs as research-oriented TCGA associations.

If the API is unreachable during the initial base URL or `/health` check, return the connection error and suggest checking whether the service is running, whether the base URL is correct, and whether API key auth is required.
