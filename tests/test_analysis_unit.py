"""Unit tests for analysis helpers that should not touch network services."""
from __future__ import annotations

import numpy as np
import pandas as pd


def test_diff_expr_log2_fold_change_uses_log_scale_difference(monkeypatch):
    """tcga_RSEM_gene_tpm values are already log2-scaled."""
    from ucscxenatoolspy.api_service import analysis

    monkeypatch.setattr(
        analysis,
        "resolve_gene",
        lambda gene: {"input": gene, "symbol": gene, "status": "exact"},
    )
    monkeypatch.setattr(
        analysis,
        "_get_cancer_index",
        lambda: {"LUAD": {"tumor": ["T1", "T2", "T3"], "normal": ["N1", "N2", "N3"]}},
    )
    monkeypatch.setattr(
        analysis,
        "query_molecule_value",
        lambda _dataset, _gene: pd.Series(
            [6.0, 8.0, 10.0, 2.0, 4.0, 6.0],
            index=["T1", "T2", "T3", "N1", "N2", "N3"],
        ),
    )
    analysis.diff_expr_analysis.cache_clear()

    result = analysis.diff_expr_analysis("TP53", "LUAD")

    assert result["tumor"]["mean"] == 8.0
    assert result["normal"]["mean"] == 4.0
    assert result["log2_fold_change"] == 4.0


def test_survival_cutoff_returns_high_low_group_counts():
    from ucscxenatoolspy.api_service.analysis import _run_survival_cutoff

    expr = pd.Series([1.0, 2.0, 3.0, 4.0], index=["S1", "S2", "S3", "S4"])
    times = pd.Series([10.0, 20.0, 30.0, 40.0], index=expr.index)
    events = pd.Series([1, 0, 1, 0], index=expr.index)

    result = _run_survival_cutoff(expr, times, events, cutoff=3.0)

    assert result["high"]["n"] == 2
    assert result["low"]["n"] == 2


def test_optimal_cutoff_requires_each_group_at_least_10_percent():
    from ucscxenatoolspy.api_service import analysis

    expr = pd.Series(np.arange(20, dtype=float), index=[f"S{i}" for i in range(20)])
    times = pd.Series(np.arange(20, 40, dtype=float), index=expr.index)
    events = pd.Series([1] * 20, index=expr.index)

    result = analysis._find_optimal_cutoff(expr, times, events)

    assert result["min_group_fraction"] == 0.10
    assert result["min_group_n"] == 2
    assert result["high"]["n"] >= 2
    assert result["low"]["n"] >= 2
