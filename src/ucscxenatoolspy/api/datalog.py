"""Datalog query rendering and parameter marshalling.

Mirrors R's api_inner.R and api_xq.R: parameter marshalling (.marshall_param),
list formatting (.arrayfmt), and dynamic query generation from .xq templates.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ucscxenatoolspy.api.client import xena_post

# ── Parameter marshalling (mirrors R's .marshall_param) ───────────────────


def _quote(s: str) -> str:
    """Wrap a string in double quotes: foo -> "foo"."""
    return f'"{s}"'


def _arrayfmt(items: list[str], collapse: str = " ") -> str:
    """Format a list as Datalog array: ["a" "b" "c"]."""
    return "[" + collapse.join(_quote(x) for x in items) + "]"


def marshall_param(p: Any) -> str:
    """Marshall a parameter into Datalog format.

    Mirrors R's .marshall_param():
    - list/tuple -> Datalog array ["a" "b"], empty list -> []
    - single str -> quoted "str"
    - None -> nil
    """
    if p is None:
        return "nil"
    if isinstance(p, (list, tuple)):
        items = [str(x) for x in p]
        if len(items) == 0:
            return "[]"  # Empty array, not nil
        return _arrayfmt(items)
    if isinstance(p, str):
        return _quote(p)
    # Numeric or other atomic types
    return str(p)


def call_query(query: str, params: list[Any]) -> str:
    """Format a query body with marshalled parameters.

    R's .call(): sprintf("(%s %s)", query, params)
    Produces: ((body ...) "val" -1)
    """
    marshalled = " ".join(marshall_param(p) for p in params)
    return f"({query} {marshalled})"


# ── Query template loading ────────────────────────────────────────────────

_QUERIES_DIR = Path(__file__).parent / "queries"
_template_cache: dict[str, str] = {}


def _load_template(name: str) -> str:
    """Load a .xq template by name (without extension).

    Strips semicolon comments (R's read_file behavior).
    """
    if name in _template_cache:
        return _template_cache[name]

    path = _QUERIES_DIR / f"{name}.xq"
    if not path.exists():
        raise FileNotFoundError(f"Query template not found: {path}")

    content = path.read_text(encoding="utf-8").strip()
    # Strip semicolon comments (matches R's read_file behavior)
    lines = content.split("\n")
    code_lines = [line for line in lines if not line.strip().startswith(";")]
    content = "\n".join(code_lines).strip()

    _template_cache[name] = content
    return content


def _parse_params(template: str) -> list[str]:
    """Extract parameter names from (fn [param1 param2 ...]) header.

    Mirrors R's parameter extraction regex: ^[^[]+[[]([^]]*)[]].*$
    """
    match = re.search(r"\[([^\]]*)\]", template)
    if not match:
        return []
    return [p.strip() for p in match.group(1).split() if p.strip()]


def _p_query(template_name: str, host: str, **kwargs: Any) -> Any:
    """Generic query execution: load template, wrap with params, POST to host.

    Mirrors R's pattern: .call(read_file(template), list(params))
    Produces: ((fn [param1 param2] body...) "val1" "val2")
    """
    template = _load_template(template_name)
    param_names = _parse_params(template)
    args = [kwargs.get(p) for p in param_names]
    query_str = call_query(template, args)
    return xena_post(host, query_str)


# ── Generated query functions (mirrors R's .p_* functions) ────────────────
# Each function loads its corresponding .xq template and executes it.


def _p_dataset_fetch(host: str, dataset: str, samples: list | str, probes: list | str) -> Any:
    """Fetch values from a dense matrix dataset."""
    if isinstance(samples, str):
        samples = [samples]
    if isinstance(probes, str):
        probes = [probes]
    return _p_query("datasetFetch", host, dataset=dataset, samples=samples, probes=probes)


def _p_dataset_samples(host: str, dataset: str, limit: int = -1) -> Any:
    """Get samples from a dataset."""
    return _p_query("datasetSamples", host, dataset=dataset, limit=limit)


def _p_dataset_field(host: str, dataset: str) -> Any:
    """Get identifiers (fields) from a dataset."""
    return _p_query("datasetField", host, dataset=dataset)


def _p_sparse_data(host: str, dataset: str, samples: list | str, genes: list | str) -> Any:
    """Fetch sparse (mutation) data."""
    if isinstance(samples, str):
        samples = [samples]
    if isinstance(genes, str):
        genes = [genes]
    return _p_query("sparseData", host, dataset=dataset, samples=samples, genes=genes)


def _p_all_cohorts(host: str, exclude: list | None = None) -> Any:
    """Get all cohorts from a host.

    Args:
        host: Xena host URL.
        exclude: List of data types to exclude. Default empty list (exclude nothing).
    """
    if exclude is None:
        exclude = []
    return _p_query("allCohorts", host, exclude=exclude)


def _p_dataset_metadata(host: str, dataset: str) -> Any:
    """Get dataset metadata."""
    return _p_query("datasetMetadata", host, dataset=dataset)


def _p_dataset_gene_probe_avg(host: str, dataset: str, samples: list | str, genes: list | str) -> Any:
    """Get gene expression via probeMap averaging."""
    if isinstance(samples, str):
        samples = [samples]
    if isinstance(genes, str):
        genes = [genes]
    return _p_query("datasetGeneProbeAvg", host, dataset=dataset, samples=samples, genes=genes)


def _p_cohort_samples(host: str, cohort: str) -> Any:
    """Get samples from a cohort."""
    return _p_query("cohortSamples", host, cohort=cohort)


def _p_dataset_list(host: str, cohorts: list | str) -> Any:
    """Get all datasets for given cohorts."""
    if isinstance(cohorts, str):
        cohorts = [cohorts]
    return _p_query("datasetList", host, cohorts=cohorts)
