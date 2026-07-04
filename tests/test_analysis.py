"""Integration tests for analysis endpoints — requires network access to Xena.

Run with:     pytest -m integration
Skip with:    pytest -m "not integration"
"""
from __future__ import annotations

import pytest


# All tests in this file require the integration marker
pytestmark = pytest.mark.integration


# ═══════════════════════════════════════════════════════════════════════════
# Differential expression
# ═══════════════════════════════════════════════════════════════════════════

class TestDiffExprIntegration:
    def test_tp53_luad_success(self, client):
        """TP53 in LUAD — has normal samples, should return full result."""
        r = client.get("/api/v1/diff-expr?gene=TP53&cancer=LUAD")
        assert r.status_code == 200
        body = r.json()
        # Top-level fields
        assert body["gene"] == "TP53"
        assert body["cancer"] == "LUAD"
        assert body["cancer_full_name"] == "Lung adenocarcinoma"
        assert body["dataset"] == "tcga_RSEM_gene_tpm"
        assert body["test"].startswith("Wilcoxon")
        # Tumor / normal groups
        assert body["tumor"]["n"] >= 3
        assert body["normal"]["n"] >= 3
        assert "mean" in body["tumor"]
        assert "median" in body["tumor"]
        assert "mean" in body["normal"]
        assert "median" in body["normal"]
        # Stats
        assert isinstance(body["p_value"], float)
        assert 0 <= body["p_value"] <= 1
        # log2_fold_change may be None or a number
        if body["log2_fold_change"] is not None:
            assert isinstance(body["log2_fold_change"], float)

    def test_egfr_brca_success(self, client):
        """EGFR in BRCA — should also work."""
        r = client.get("/api/v1/diff-expr?gene=EGFR&cancer=BRCA")
        assert r.status_code == 200
        body = r.json()
        assert body["gene"] == "EGFR"
        assert body["cancer"] == "BRCA"

    def test_cancer_without_normal_returns_400(self, client):
        """LAML has no normal samples — should return 400."""
        r = client.get("/api/v1/diff-expr?gene=TP53&cancer=LAML")
        assert r.status_code == 400
        body = r.json()
        assert "error" in body
        assert "only" in body["error"]

    def test_case_insensitive_cancer(self, client):
        """Cancer abbreviation should be case-insensitive."""
        r = client.get("/api/v1/diff-expr?gene=TP53&cancer=luad")
        assert r.status_code == 200
        assert r.json()["cancer"] == "LUAD"

    def test_gene_alias_resolution(self, client):
        """HER2 should be resolved to ERBB2."""
        r = client.get("/api/v1/diff-expr?gene=HER2&cancer=BRCA")
        # Could succeed or fail depending on mygene — check graceful handling
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            body = r.json()
            assert body["gene"] == "ERBB2"
            assert body["gene_input"] == "HER2"


# ═══════════════════════════════════════════════════════════════════════════
# Gene correlation
# ═══════════════════════════════════════════════════════════════════════════

class TestCorrIntegration:
    def test_tp53_egfr_luad_success(self, client):
        """TP53 vs EGFR in LUAD."""
        r = client.get("/api/v1/corr?gene1=TP53&gene2=EGFR&cancer=LUAD")
        assert r.status_code == 200
        body = r.json()
        assert body["gene1"] == "TP53"
        assert body["gene2"] == "EGFR"
        assert body["cancer"] == "LUAD"
        assert body["sample_type"] == "primary_tumor"
        assert body["test"].startswith("Spearman")
        # Stats
        assert isinstance(body["n"], int) and body["n"] >= 5
        assert isinstance(body["spearman_r"], float)
        assert -1 <= body["spearman_r"] <= 1
        assert isinstance(body["p_value"], float)
        assert 0 <= body["p_value"] <= 1
        # gene_input should be None for exact matches
        assert body["gene1_input"] is None
        assert body["gene2_input"] is None

    def test_same_gene_correlation(self, client):
        """Same gene → rho should be 1.0."""
        r = client.get("/api/v1/corr?gene1=TP53&gene2=TP53&cancer=LUAD")
        assert r.status_code == 200
        body = r.json()
        assert abs(body["spearman_r"] - 1.0) < 0.001

    def test_unknown_gene_returns_404(self, client):
        r = client.get("/api/v1/corr?gene1=TP53&gene2=ZZNOTAGENE&cancer=LUAD")
        assert r.status_code in (400, 404)
        assert "error" in r.json()


# ═══════════════════════════════════════════════════════════════════════════
# Survival analysis
# ═══════════════════════════════════════════════════════════════════════════

class TestSurvivalIntegration:
    def test_tp53_luad_success(self, client):
        """TP53 survival in LUAD."""
        r = client.get("/api/v1/survival?gene=TP53&cancer=LUAD")
        assert r.status_code == 200
        body = r.json()
        assert body["gene"] == "TP53"
        assert body["cancer"] == "LUAD"
        assert body["sample_type"] == "primary_tumor"
        assert body["test"] == "Log-rank test"
        assert "survival" in body
        survival = body["survival"]
        # Should have 4 endpoints
        for ep in ("OS", "DSS", "DFI", "PFI"):
            assert ep in survival
        # At least OS should have results
        assert "error" not in survival["OS"] or survival["OS"].get("n_total", 0) >= 10
        # Each valid endpoint should have median_cutoff and optimal_cutoff
        for ep in ("OS", "DSS", "DFI", "PFI"):
            result = survival[ep]
            if "error" not in result:
                assert "median_cutoff" in result
                assert "optimal_cutoff" in result
                assert "n_total" in result
                assert "n_events" in result
                # Check cutoff structure
                mc = result["median_cutoff"]
                assert "p_value" in mc
                assert "high" in mc
                assert "low" in mc
                assert mc["method"] == "median"

    def test_unknown_gene_returns_404(self, client):
        r = client.get("/api/v1/survival?gene=ZZNOTAGENE&cancer=LUAD")
        assert r.status_code in (400, 404)
        assert "error" in r.json()


# ═══════════════════════════════════════════════════════════════════════════
# Response cache (same query twice → second is cached)
# ═══════════════════════════════════════════════════════════════════════════

class TestCacheBehavior:
    def test_repeated_query_consistent(self, client):
        """Same query twice should produce identical results (via cache)."""
        r1 = client.get("/api/v1/cancers")
        r2 = client.get("/api/v1/cancers")
        assert r1.json() == r2.json()
