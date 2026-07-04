"""TCGA analysis: differential expression, correlation, and survival.

All analyses use tcga_RSEM_gene_tpm (log2(TPM+0.001) transformed) from toilHub.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Tuple

import numpy as np
import pandas as pd
from scipy import stats

from ucscxenatoolspy import tcga_clinical, tcga_survival, query_molecule_value

from ucscxenatoolspy.api_service.cache_utils import ttl_cache
from ucscxenatoolspy.api_service.gene_utils import resolve_gene

# ── TCGA abbreviation → full name mapping ──────────────────────────────
# Source: tcga_id.txt (37 TCGA project codes)

TCGA_CANCER_NAMES: dict[str, str] = {
    "LAML": "Acute Myeloid Leukemia",
    "ACC": "Adrenocortical carcinoma",
    "BLCA": "Bladder Urothelial Carcinoma",
    "LGG": "Brain Lower Grade Glioma",
    "BRCA": "Breast invasive carcinoma",
    "CESC": "Cervical squamous cell carcinoma and endocervical adenocarcinoma",
    "CHOL": "Cholangiocarcinoma",
    "LCML": "Chronic Myelogenous Leukemia",
    "COAD": "Colon adenocarcinoma",
    "CNTL": "Controls",
    "ESCA": "Esophageal carcinoma",
    "FPPP": "FFPE Pilot Phase II",
    "GBM": "Glioblastoma multiforme",
    "HNSC": "Head and Neck squamous cell carcinoma",
    "KICH": "Kidney Chromophobe",
    "KIRC": "Kidney renal clear cell carcinoma",
    "KIRP": "Kidney renal papillary cell carcinoma",
    "LIHC": "Liver hepatocellular carcinoma",
    "LUAD": "Lung adenocarcinoma",
    "LUSC": "Lung squamous cell carcinoma",
    "DLBC": "Lymphoid Neoplasm Diffuse Large B-cell Lymphoma",
    "MESO": "Mesothelioma",
    "MISC": "Miscellaneous",
    "OV": "Ovarian serous cystadenocarcinoma",
    "PAAD": "Pancreatic adenocarcinoma",
    "PCPG": "Pheochromocytoma and Paraganglioma",
    "PRAD": "Prostate adenocarcinoma",
    "READ": "Rectum adenocarcinoma",
    "SARC": "Sarcoma",
    "SKCM": "Skin Cutaneous Melanoma",
    "STAD": "Stomach adenocarcinoma",
    "TGCT": "Testicular Germ Cell Tumors",
    "THYM": "Thymoma",
    "THCA": "Thyroid carcinoma",
    "UCS": "Uterine Carcinosarcoma",
    "UCEC": "Uterine Corpus Endometrial Carcinoma",
    "UVM": "Uveal Melanoma",
}

# Dataset used for expression queries
EXPR_DATASET = "tcga_RSEM_gene_tpm"


@lru_cache(maxsize=1)
def _get_cancer_index() -> dict[str, dict[str, list[str]]]:
    """Build a cached mapping: cancer_code → {tumor: [...], normal: [...]}.

    Parsed once from tcga_clinical() on first call, then cached in memory.
    """
    clinical = tcga_clinical()
    index: dict[str, dict[str, list[str]]] = {}

    for cancer in clinical["Cancer"].unique():
        sub = clinical[clinical["Cancer"] == cancer]
        tumor_samples = sub[sub["Code"] == "TP"]["Sample"].tolist()
        normal_samples = sub[sub["Code"] == "NT"]["Sample"].tolist()
        index[cancer] = {"tumor": tumor_samples, "normal": normal_samples}

    return index


def get_available_cancers() -> list[dict]:
    """Return all cancers with sample counts for the listing endpoint."""
    index = _get_cancer_index()
    result = []
    for code, info in sorted(index.items()):
        result.append({
            "cancer": code,
            "full_name": TCGA_CANCER_NAMES.get(code, code),
            "tumor_n": len(info["tumor"]),
            "normal_n": len(info["normal"]),
            "has_normal": len(info["normal"]) >= 3,
        })
    return result


def _query_gene_tumor(
    gene: str,
    cancer: str,
) -> Tuple[pd.Series, set]:
    """Query a gene and filter to tumor samples for a given cancer.

    Returns (filtered_series, tumor_sample_set).
    """
    index = _get_cancer_index()
    tumor_sample_set = set(index[cancer]["tumor"])

    try:
        values = query_molecule_value(EXPR_DATASET, gene)
    except Exception as e:
        raise RuntimeError(
            f"Failed to query expression data for gene \"{gene}\": {e}"
        ) from e

    if values is None or len(values) == 0:
        raise RuntimeError(
            f"Gene \"{gene}\" returned no expression data from {EXPR_DATASET}."
        )

    # Filter to tumor samples only, drop NaN
    filtered = values[values.index.isin(tumor_sample_set)]
    filtered = filtered.dropna()

    return filtered, tumor_sample_set


@ttl_cache(ttl=3600, maxsize=256)
def corr_analysis(
    gene1: str,
    gene2: str,
    cancer: str,
) -> dict:
    """Spearman correlation between two genes in primary tumor samples.

    Args:
        gene1: First gene symbol (e.g. "TP53").
        gene2: Second gene symbol (e.g. "KRAS").
        cancer: TCGA cancer abbreviation, case-insensitive (e.g. "LUAD").

    Returns:
        Analysis result dict.

    Raises:
        ValueError: Unknown cancer or insufficient samples.
        RuntimeError: Gene not found or expression query returned no data.
    """
    cancer = cancer.upper()

    # ── Gene resolution ──────────────────────────────────────────────
    r1 = resolve_gene(gene1)
    r2 = resolve_gene(gene2)
    if r1["status"] == "not_found":
        raise ValueError(f"Gene \"{gene1}\" not found in dataset or mygene.")
    if r2["status"] == "not_found":
        raise ValueError(f"Gene \"{gene2}\" not found in dataset or mygene.")
    sym1, sym2 = r1["symbol"], r2["symbol"]

    # ── Cancer validation ────────────────────────────────────────────
    if cancer not in TCGA_CANCER_NAMES:
        raise ValueError(
            f"Unknown cancer abbreviation \"{cancer}\". "
            f"Valid values: {', '.join(sorted(TCGA_CANCER_NAMES.keys()))}"
        )

    index = _get_cancer_index()
    if cancer not in index:
        raise ValueError(
            f"Cancer \"{cancer}\" is a known TCGA project but has no samples "
            f"in the current clinical dataset."
        )

    tumor_n_available = len(index[cancer]["tumor"])
    if tumor_n_available < 5:
        raise ValueError(
            f"Cancer \"{cancer}\" ({TCGA_CANCER_NAMES[cancer]}) has only "
            f"{tumor_n_available} primary tumor sample(s). Need at least 5."
        )

    # Query both genes
    s1, _ = _query_gene_tumor(sym1, cancer)
    s2, _ = _query_gene_tumor(sym2, cancer)

    # Intersect samples that have data for both genes
    common_samples = s1.index.intersection(s2.index)
    if len(common_samples) < 5:
        raise ValueError(
            f"Only {len(common_samples)} samples have expression data for both "
            f"\"{sym1}\" and \"{sym2}\" in {cancer}. Need at least 5."
        )

    x = s1[common_samples].values.astype(float)
    y = s2[common_samples].values.astype(float)

    # Spearman correlation
    rho, p_value = stats.spearmanr(x, y)

    return {
        "gene1": sym1,
        "gene2": sym2,
        "gene1_input": gene1 if r1["status"] != "exact" else None,
        "gene2_input": gene2 if r2["status"] != "exact" else None,
        "cancer": cancer,
        "cancer_full_name": TCGA_CANCER_NAMES[cancer],
        "dataset": EXPR_DATASET,
        "sample_type": "primary_tumor",
        "n": len(common_samples),
        "spearman_r": round(float(rho), 4),
        "p_value": float(p_value),
        "test": "Spearman rank correlation (two-sided)",
    }


# ── Survival analysis ─────────────────────────────────────────────────
# Four TCGA survival endpoints
SURVIVAL_ENDPOINTS = [
    ("OS", "Overall Survival"),
    ("DSS", "Disease-Specific Survival"),
    ("DFI", "Disease-Free Interval"),
    ("PFI", "Progression-Free Interval"),
]

OPTIMAL_CUTOFF_MIN_GROUP_FRACTION = 0.10


def _logrank_test(
    times1: np.ndarray,
    events1: np.ndarray,
    times2: np.ndarray,
    events2: np.ndarray,
) -> dict:
    """Manual log-rank test comparing two survival curves.

    Returns dict with chi2_stat, p_value.
    """
    # Combine and sort unique event times
    all_times = np.unique(np.concatenate([
        times1[events1 == 1],
        times2[events2 == 1],
    ]))
    if len(all_times) == 0:
        return {"chi2_stat": 0.0, "p_value": 1.0}

    sum_oe = 0.0  # Σ (O₁ - E₁)
    sum_var = 0.0  # Σ variance

    for t in all_times:
        # At-risk counts just before time t
        n1 = np.sum(times1 >= t)
        n2 = np.sum(times2 >= t)
        n_total = n1 + n2
        if n_total == 0:
            continue

        # Observed events at time t
        o1 = np.sum((times1 == t) & (events1 == 1))
        o2 = np.sum((times2 == t) & (events2 == 1))
        o_total = o1 + o2
        if o_total == 0:
            continue

        # Expected events in group 1 under H₀
        e1 = n1 * o_total / n_total

        sum_oe += o1 - e1

        # Hypergeometric variance
        if n_total > 1:
            var = (n1 * n2 * o_total * (n_total - o_total)) / (
                n_total * n_total * (n_total - 1)
            )
            sum_var += var

    if sum_var == 0:
        return {"chi2_stat": 0.0, "p_value": 1.0}

    chi2 = (sum_oe * sum_oe) / sum_var
    p_value = stats.chi2.sf(chi2, 1)

    return {"chi2_stat": float(chi2), "p_value": float(p_value)}


def _run_survival_cutoff(
    expr: pd.Series,
    surv_times: pd.Series,
    surv_events: pd.Series,
    cutoff: float,
) -> dict:
    """Run log-rank test for a given expression cutoff (high vs low)."""
    high_mask = expr >= cutoff
    low_mask = expr < cutoff

    times_high = surv_times[high_mask].values.astype(float)
    events_high = surv_events[high_mask].values.astype(float)
    times_low = surv_times[low_mask].values.astype(float)
    events_low = surv_events[low_mask].values.astype(float)

    # Compute mean survival days for each group
    mean_high = float(np.mean(times_high))
    mean_low = float(np.mean(times_low))

    lr = _logrank_test(times_high, events_high, times_low, events_low)

    return {
        "cutoff": round(float(cutoff), 4),
        "high": {
            "n": int(len(times_high)),
            "n_events": int(np.sum(events_high)),
            "mean_survival_days": round(mean_high, 1),
        },
        "low": {
            "n": int(len(times_low)),
            "n_events": int(np.sum(events_low)),
            "mean_survival_days": round(mean_low, 1),
        },
        "chi2_stat": lr["chi2_stat"],
        "p_value": lr["p_value"],
    }


def _find_optimal_cutoff(
    expr: pd.Series,
    surv_times: pd.Series,
    surv_events: pd.Series,
) -> dict:
    """Find the expression cutoff that maximizes survival difference.

    Scans cutoffs between the 25th and 75th percentiles of expression,
    skipping extreme splits that would put <10% of samples in either group.
    """
    values = expr.values
    lo = np.percentile(values, 25)
    hi = np.percentile(values, 75)
    n = len(values)
    min_group_n = int(np.ceil(n * OPTIMAL_CUTOFF_MIN_GROUP_FRACTION))

    candidates = sorted(set(v for v in values if lo <= v <= hi))

    # Sample down if too many candidates (use ~100 evenly-spaced points)
    if len(candidates) > 100:
        step = len(candidates) // 100
        candidates = candidates[::step]

    best = None
    best_p = 1.0

    for cutoff in candidates:
        high_n = np.sum(values >= cutoff)
        low_n = n - high_n
        # Require at least 10% of samples in each group
        if low_n < min_group_n or high_n < min_group_n:
            continue

        lr = _run_survival_cutoff(expr, surv_times, surv_events, cutoff)
        if lr["p_value"] < best_p:
            best_p = lr["p_value"]
            best = lr

    if best is None:
        return {
            "method": "optimal_cutoff",
            "error": (
                "No candidate cutoff satisfied the minimum group size "
                f"requirement ({min_group_n} samples per group)."
            ),
            "min_group_fraction": OPTIMAL_CUTOFF_MIN_GROUP_FRACTION,
            "min_group_n": min_group_n,
        }

    best["method"] = "optimal_cutoff"
    best["min_group_fraction"] = OPTIMAL_CUTOFF_MIN_GROUP_FRACTION
    best["min_group_n"] = min_group_n
    return best


@ttl_cache(ttl=3600, maxsize=256)
def survival_analysis(
    gene: str,
    cancer: str,
) -> dict:
    """Survival analysis: gene expression vs survival in primary tumors.

    For each of the 4 TCGA survival endpoints (OS, DSS, DFI, PFI):
      - Splits samples into high/low expression groups by median cutoff
      - Finds the optimal expression cutoff maximizing survival difference
      - Runs log-rank test for both methods

    Args:
        gene: Gene symbol (e.g. "TP53").
        cancer: TCGA cancer abbreviation, case-insensitive (e.g. "LUAD").

    Returns:
        Analysis result dict with survival results per endpoint.

    Raises:
        ValueError: Unknown cancer or insufficient samples.
        RuntimeError: Gene not found or expression query returned no data.
    """
    cancer = cancer.upper()

    # ── Gene resolution ──────────────────────────────────────────────
    r = resolve_gene(gene)
    if r["status"] == "not_found":
        raise ValueError(f"Gene \"{gene}\" not found in dataset or mygene.")
    symbol = r["symbol"]

    if cancer not in TCGA_CANCER_NAMES:
        raise ValueError(
            f"Unknown cancer abbreviation \"{cancer}\". "
            f"Valid values: {', '.join(sorted(TCGA_CANCER_NAMES.keys()))}"
        )

    index = _get_cancer_index()
    if cancer not in index:
        raise ValueError(
            f"Cancer \"{cancer}\" is a known TCGA project but has no samples "
            f"in the current clinical dataset."
        )

    tumor_samples = set(index[cancer]["tumor"])
    if len(tumor_samples) < 10:
        raise ValueError(
            f"Cancer \"{cancer}\" ({TCGA_CANCER_NAMES[cancer]}) has only "
            f"{len(tumor_samples)} primary tumor sample(s). Need at least 10."
        )

    # Query gene expression, tumor only
    expr_series, _ = _query_gene_tumor(symbol, cancer)

    # Load survival data and filter to available samples
    surv = tcga_survival()
    surv = surv[surv["Sample"].isin(tumor_samples)]

    # Merge expression + survival on common samples
    common = expr_series.index.intersection(surv["Sample"])
    if len(common) < 10:
        raise ValueError(
            f"Only {len(common)} samples have both expression and survival data "
            f"for \"{gene}\" in {cancer}. Need at least 10."
        )

    expr = expr_series[common]
    surv = surv.set_index("Sample").loc[common]

    results = {}
    for endpoint, full_name in SURVIVAL_ENDPOINTS:
        event_col = endpoint
        time_col = f"{endpoint}.time"

        surv_events = surv[event_col]
        surv_times = surv[time_col]

        # Drop samples with missing survival data for this endpoint
        valid = surv_events.notna() & surv_times.notna()
        if valid.sum() < 10:
            results[endpoint] = {
                "name": full_name,
                "error": f"Only {valid.sum()} valid samples (need ≥10). Skipped.",
            }
            continue

        e = expr[valid]
        t = surv_times[valid]
        ev = surv_events[valid]

        # Median cutoff
        median_cutoff = float(np.median(e.values))
        median_result = _run_survival_cutoff(e, t, ev, median_cutoff)
        median_result["method"] = "median"

        # Optimal cutoff
        optimal_result = _find_optimal_cutoff(e, t, ev)

        results[endpoint] = {
            "name": full_name,
            "n_total": int(valid.sum()),
            "n_events": int(ev.sum()),
            "median_cutoff": median_result,
            "optimal_cutoff": optimal_result,
            "optimal_cutoff_note": (
                "Exploratory minimum-p scan across candidate cutoffs; "
                "p_value is not adjusted for multiple cutoff testing."
            ),
        }

    return {
        "gene": symbol,
        "gene_input": gene if r["status"] != "exact" else None,
        "cancer": cancer,
        "cancer_full_name": TCGA_CANCER_NAMES[cancer],
        "dataset": EXPR_DATASET,
        "sample_type": "primary_tumor",
        "test": "Log-rank test",
        "survival": results,
    }


@ttl_cache(ttl=3600, maxsize=256)
def diff_expr_analysis(
    gene: str,
    cancer: str,
) -> dict:
    """Run differential expression analysis for a gene in a cancer type.

    Args:
        gene: Gene symbol (e.g. "TP53").
        cancer: TCGA cancer abbreviation, case-insensitive (e.g. "LUAD").

    Returns:
        Analysis result dict.

    Raises:
        ValueError: Unknown cancer, no normal samples, or insufficient samples.
        RuntimeError: Gene not found or expression query returned no data.
    """
    cancer = cancer.upper()

    # ── Gene resolution ──────────────────────────────────────────────
    r = resolve_gene(gene)
    if r["status"] == "not_found":
        raise ValueError(f"Gene \"{gene}\" not found in dataset or mygene.")
    symbol = r["symbol"]

    # Validate cancer code
    if cancer not in TCGA_CANCER_NAMES:
        raise ValueError(
            f"Unknown cancer abbreviation \"{cancer}\". "
            f"Valid values: {', '.join(sorted(TCGA_CANCER_NAMES.keys()))}"
        )

    # Get sample index
    index = _get_cancer_index()
    if cancer not in index:
        raise ValueError(
            f"Cancer \"{cancer}\" is a known TCGA project but has no samples "
            f"in the current clinical dataset."
        )

    tumor_samples = index[cancer]["tumor"]
    normal_samples = index[cancer]["normal"]
    tumor_sample_set = set(tumor_samples)
    normal_sample_set = set(normal_samples)

    if len(normal_samples) < 3:
        raise ValueError(
            f"Cancer \"{cancer}\" ({TCGA_CANCER_NAMES[cancer]}) has "
            f"only {len(normal_samples)} normal tissue sample(s). "
            f"Need at least 3 for differential expression analysis."
        )

    # Query expression data
    try:
        values = query_molecule_value(EXPR_DATASET, symbol)
    except Exception as e:
        raise RuntimeError(
            f"Failed to query expression data for gene \"{symbol}\": {e}"
        ) from e

    if values is None or len(values) == 0:
        raise RuntimeError(
            f"Gene \"{symbol}\" returned no expression data from {EXPR_DATASET}."
        )

    # Split into tumor / normal groups
    tumor_vals = []
    normal_vals = []
    for sample_id, val in values.items():
        if sample_id in tumor_sample_set:
            tumor_vals.append(val)
        elif sample_id in normal_sample_set:
            normal_vals.append(val)

    tumor_vals = np.array(tumor_vals, dtype=float)
    normal_vals = np.array(normal_vals, dtype=float)

    # Drop NaN
    tumor_vals = tumor_vals[~np.isnan(tumor_vals)]
    normal_vals = normal_vals[~np.isnan(normal_vals)]

    if len(tumor_vals) < 3 or len(normal_vals) < 3:
        raise ValueError(
            f"Insufficient samples after filtering: "
            f"tumor={len(tumor_vals)}, normal={len(normal_vals)} "
            f"(need ≥ 3 each)."
        )

    # Wilcoxon rank-sum test
    _, p_value = stats.mannwhitneyu(
        tumor_vals, normal_vals, alternative="two-sided"
    )

    tumor_mean = float(np.mean(tumor_vals))
    normal_mean = float(np.mean(normal_vals))
    tumor_median = float(np.median(tumor_vals))
    normal_median = float(np.median(normal_vals))

    # Values are already log2(TPM + 0.001); the mean difference is the
    # log2-scale expression change between tumor and normal groups.
    log2fc = tumor_mean - normal_mean

    return {
        "gene": symbol,
        "gene_input": gene if r["status"] != "exact" else None,
        "cancer": cancer,
        "cancer_full_name": TCGA_CANCER_NAMES[cancer],
        "dataset": EXPR_DATASET,
        "tumor": {
            "n": len(tumor_vals),
            "mean": round(tumor_mean, 4),
            "median": round(tumor_median, 4),
        },
        "normal": {
            "n": len(normal_vals),
            "mean": round(normal_mean, 4),
            "median": round(normal_median, 4),
        },
        "log2_fold_change": round(log2fc, 4),
        "p_value": float(p_value),
        "test": "Wilcoxon rank-sum (Mann-Whitney U, two-sided)",
    }
