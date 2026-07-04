"""Tests for gene name resolution — mocks mygene to avoid network calls."""
from __future__ import annotations

import pytest

from ucscxenatoolspy.api_service.gene_utils import resolve_gene, _load_gene_list


# ── Test data ─────────────────────────────────────────────────────────────

class TestLoadGeneList:
    """The dataset gene list must be loadable."""
    def test_loads_without_error(self):
        genes = _load_gene_list()
        assert isinstance(genes, set)
        assert len(genes) > 50_000  # 58,581 expected

    def test_contains_common_genes(self):
        genes = _load_gene_list()
        assert "TP53" in genes
        assert "EGFR" in genes
        assert "KRAS" in genes
        assert "BRCA1" in genes
        assert "GAPDH" in genes

    def test_cached_second_call(self):
        """Second call should return exact same set object (lru_cache)."""
        g1 = _load_gene_list()
        g2 = _load_gene_list()
        assert g1 is g2


class TestResolveGeneExactMatch:
    """Exact matches should be found without mygene."""
    def test_common_gene_tp53(self):
        r = resolve_gene("TP53")
        assert r["status"] == "exact"
        assert r["symbol"] == "TP53"
        assert r["input"] == "TP53"

    def test_common_gene_egfr(self):
        r = resolve_gene("EGFR")
        assert r["status"] == "exact"
        assert r["symbol"] == "EGFR"

    def test_common_gene_kras(self):
        r = resolve_gene("KRAS")
        assert r["status"] == "exact"

    def test_case_sensitive(self):
        """'tp53' (lowercase) should not be an exact match but case-insensitive."""
        r = resolve_gene("tp53")
        # case-insensitive match resolves it
        assert r["status"] == "resolved"
        assert r["symbol"] == "TP53"


class TestResolveGeneCaseInsensitive:
    """Lower/upper-case variants should be resolved without mygene."""
    def test_lowercase(self):
        r = resolve_gene("egfr")
        assert r["status"] == "resolved"
        assert r["symbol"] == "EGFR"

    def test_mixed_case(self):
        r = resolve_gene("Tp53")
        assert r["status"] == "resolved"
        assert r["symbol"] == "TP53"


class TestResolveGeneNotFound:
    """Non-existent genes should return not_found."""
    def test_completely_fake(self):
        r = resolve_gene("FAKE_GENE_XYZ_999")
        assert r["status"] == "not_found"
        assert r["symbol"] is None

    def test_empty_like(self):
        r = resolve_gene("ZZZZNOTAGENEZZZZ")
        assert r["status"] == "not_found"

    def test_mygene_hit_outside_dataset_is_not_found(self, monkeypatch):
        """A mygene hit is only usable if the symbol exists in gene_list.txt."""
        from ucscxenatoolspy.api_service import gene_utils

        class FakeMyGene:
            def querymany(self, *_args, **_kwargs):
                return [{"symbol": "NOT_IN_TCGA_RSEM"}]

        gene_utils._mygene_resolve.cache_clear()
        monkeypatch.setattr(gene_utils, "_get_mg", lambda: FakeMyGene())

        r = resolve_gene("external_alias")
        assert r["status"] == "not_found"
        assert r["symbol"] is None


class TestResolveGenesBatch:
    """Batch resolution via resolve_genes."""
    def test_mixed_results(self):
        from ucscxenatoolspy.api_service.gene_utils import resolve_genes
        results = resolve_genes("TP53", "ZZZZNOTAGENE", "egfr")
        assert results[0]["status"] == "exact"
        assert results[1]["status"] == "not_found"
        assert results[2]["status"] == "resolved"
        assert results[2]["symbol"] == "EGFR"
