"""Gene name resolution: validate, correct, and standardize gene identifiers.

Uses the dataset's gene list as ground truth, with mygene as an optional
fallback for ID/alias conversion. The gene list is bundled inside the api/
package — no external file dependency.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import mygene
from ucscxenatoolspy.api_service.cache_utils import ttl_cache

logger = logging.getLogger(__name__)
ENABLE_MYGENE_FALLBACK = os.getenv("UCSCXENA_ENABLE_MYGENE", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# ── Load valid gene list ───────────────────────────────────────────────
# Bundled inside the api/ package — self-contained
_GENE_LIST_PATH = Path(__file__).resolve().parent / "gene_list.txt"

_valid_genes: set[str] = set()

def _load_gene_list() -> set[str]:
    """Load the dataset's gene list (lazy, cached in module global)."""
    global _valid_genes
    if _valid_genes:
        return _valid_genes
    with open(_GENE_LIST_PATH, encoding="utf-8") as f:
        next(f)  # skip header "Gene"
        for line in f:
            gene = line.strip()
            if gene:
                _valid_genes.add(gene)
    logger.info("Loaded %d valid genes from %s", len(_valid_genes), _GENE_LIST_PATH)
    return _valid_genes


# ── mygene client (lazy init) ──────────────────────────────────────────

_mg_client: Optional[mygene.MyGeneInfo] = None

def _get_mg() -> mygene.MyGeneInfo:
    global _mg_client
    if _mg_client is None:
        _mg_client = mygene.MyGeneInfo()
    return _mg_client


# ── Resolution ─────────────────────────────────────────────────────────

@ttl_cache(ttl=86400, maxsize=2048)  # cache mygene lookups for 24h
def _mygene_resolve(query: str) -> Optional[str]:
    """Try to resolve a gene identifier to an official symbol via mygene.

    Uses querymany with broad scopes: symbol, alias, entrezgene, ensembl.gene.
    Returns the first result whose symbol is in the dataset's gene list.
    """
    try:
        results = _get_mg().querymany(
            [query],
            scopes="symbol,alias,entrezgene,ensembl.gene",
            fields="symbol",
            species="human",
        )
    except Exception as e:
        logger.warning("mygene query failed for %r: %s", query, e)
        return None

    if not results:
        return None

    valid = _load_gene_list()
    for item in results:
        symbol = item.get("symbol")
        if symbol and symbol in valid:
            return symbol

    return None


def resolve_gene(query: str) -> dict:
    """Validate and optionally correct a gene identifier.

    Resolution order:
      1. Exact match in dataset gene list → status "exact"
      2. mygene ID/alias lookup → status "resolved"
      3. Not resolved → status "not_found"

    Args:
        query: Gene identifier — symbol (TP53), alias (HER2), Entrez (7157),
               or Ensembl (ENSG00000141510).

    Returns:
        {"input": ..., "symbol": ..., "status": "exact"|"resolved"|"not_found"}
    """
    valid = _load_gene_list()

    # 1. Direct match
    if query in valid:
        return {"input": query, "symbol": query, "status": "exact"}

    # 2. Case-insensitive match (e.g. "tp53" → "TP53")
    upper_match = None
    for g in valid:
        if g.upper() == query.upper():
            upper_match = g
            break
    if upper_match:
        return {"input": query, "symbol": upper_match, "status": "resolved"}

    # 3. mygene lookup
    if not ENABLE_MYGENE_FALLBACK:
        return {"input": query, "symbol": None, "status": "not_found"}

    symbol = _mygene_resolve(query)
    if symbol:
        return {"input": query, "symbol": symbol, "status": "resolved"}

    return {"input": query, "symbol": None, "status": "not_found"}


def resolve_genes(*queries: str) -> list[dict]:
    """Batch-resolve multiple gene identifiers. See resolve_gene()."""
    return [resolve_gene(q) for q in queries]
