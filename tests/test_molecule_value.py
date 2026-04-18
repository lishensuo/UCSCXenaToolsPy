"""Tests for query_molecule_value and caching utilities."""

import os
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from ucscxenatoolspy.utils.cache import (
    get_cache_dir,
    make_cache_key,
    read_cache,
    write_cache,
)
from ucscxenatoolspy.query.molecule_value import (
    _extract_formula_variables,
    _safe_eval_formula,
    get_data,
    query_molecule_value,
)


class TestCacheKey:
    def test_deterministic(self):
        k1 = make_cache_key("TP53", "ccle_expression", "https://tcga.xenahubs.net")
        k2 = make_cache_key("TP53", "ccle_expression", "https://tcga.xenahubs.net")
        assert k1 == k2

    def test_different_identifier(self):
        k1 = make_cache_key("TP53", "ds", "host")
        k2 = make_cache_key("KRAS", "ds", "host")
        assert k1 != k2

    def test_different_dataset(self):
        k1 = make_cache_key("TP53", "ds1", "host")
        k2 = make_cache_key("TP53", "ds2", "host")
        assert k1 != k2

    def test_with_kwargs(self):
        k1 = make_cache_key("TP53", "ds", "host", aggr="mean")
        k2 = make_cache_key("TP53", "ds", "host", aggr="median")
        assert k1 != k2


class TestCacheIO:
    @pytest.fixture(autouse=True)
    def tmp_cache(self, tmp_path):
        """Redirect cache dir to a temporary path for each test."""
        with patch("ucscxenatoolspy.utils.cache.get_cache_dir", return_value=tmp_path):
            yield tmp_path

    def test_write_read_roundtrip(self):
        data = {"values": [1.0, 2.0, 3.0], "index": ["a", "b", "c"]}
        key = "testkey"
        write_cache(key, data)
        result = read_cache(key)
        assert result == data

    def test_miss_returns_none(self):
        assert read_cache("nonexistent") is None

    def test_corrupted_returns_none(self):
        cache_dir = get_cache_dir()
        path = cache_dir / "corrupt.pkl"
        path.write_text("not a pickle")
        assert read_cache("corrupt") is None


class TestExtractFormulaVariables:
    def test_simple_addition(self):
        assert _extract_formula_variables("TP53 + KRAS") == ["TP53", "KRAS"]

    def test_complex_formula(self):
        result = _extract_formula_variables("TP53 + 2 * KRAS - 1.3 * PTEN")
        assert result == ["TP53", "KRAS", "PTEN"]

    def test_parentheses(self):
        result = _extract_formula_variables("(TP53 + KRAS) / 2")
        assert result == ["TP53", "KRAS"]

    def test_single_gene(self):
        assert _extract_formula_variables("TP53") == ["TP53"]

    def test_log_formula(self):
        result = _extract_formula_variables("log2(TP53 + 1) - log2(KRAS + 1)")
        assert result == ["TP53", "KRAS"]


class TestSafeEvalFormula:
    def test_addition(self):
        df = pd.DataFrame({"TP53": [1, 2, 3], "KRAS": [4, 5, 6]})
        result = _safe_eval_formula("TP53 + KRAS", df)
        expected = pd.Series([5, 7, 9], index=df.index, name="TP53 + KRAS")
        pd.testing.assert_series_equal(result, expected)

    def test_scalar_multiplication(self):
        df = pd.DataFrame({"TP53": [1, 2, 3]})
        result = _safe_eval_formula("2 * TP53", df)
        expected = pd.Series([2, 4, 6], index=df.index, name="2 * TP53")
        pd.testing.assert_series_equal(result, expected)

    def test_complex_formula(self):
        df = pd.DataFrame({"TP53": [10, 20], "KRAS": [2, 4], "PTEN": [1, 1]})
        result = _safe_eval_formula("TP53 + 2 * KRAS - PTEN", df)
        expected = pd.Series([13, 27], index=df.index, name="TP53 + 2 * KRAS - PTEN")
        pd.testing.assert_series_equal(result, expected)

    def test_math_function(self):
        df = pd.DataFrame({"TP53": [1.0, 4.0, 9.0]})
        result = _safe_eval_formula("sqrt(TP53)", df)
        expected = pd.Series([1.0, 2.0, 3.0], index=df.index, name="sqrt(TP53)")
        pd.testing.assert_series_equal(result, expected)


class TestGetData:
    @pytest.fixture(autouse=True)
    def tmp_cache(self, tmp_path):
        with patch("ucscxenatoolspy.utils.cache.get_cache_dir", return_value=tmp_path):
            yield tmp_path

    def test_cache_hit_returns_cached(self):
        mock_series = pd.Series([1.0, 2.0], index=["S1", "S2"], name="TP53")
        cached = {"values": [1.0, 2.0], "index": ["S1", "S2"]}

        with patch("ucscxenatoolspy.query.molecule_value.read_cache", return_value=cached), \
             patch("ucscxenatoolspy.query.molecule_value.fetch_dense_values") as mock_fetch:
            result = get_data("ccle_expression", "TP53", host="https://tcga.xenahubs.net", cache=True)
            pd.testing.assert_series_equal(result, mock_series)
            mock_fetch.assert_not_called()

    def test_cache_miss_calls_api(self):
        with patch("ucscxenatoolspy.query.molecule_value.read_cache", return_value=None), \
             patch("ucscxenatoolspy.query.molecule_value.fetch_dense_values",
                   return_value=pd.DataFrame([[5.5, 6.6]], columns=["S1", "S2"])), \
             patch("ucscxenatoolspy.query.molecule_value.write_cache") as mock_write:
            result = get_data("ccle_expression", "TP53", host="https://tcga.xenahubs.net", cache=True)
            assert result.tolist() == [5.5, 6.6]
            mock_write.assert_called_once()


class TestQueryMoleculeValue:
    @pytest.fixture(autouse=True)
    def tmp_cache(self, tmp_path):
        with patch("ucscxenatoolspy.utils.cache.get_cache_dir", return_value=tmp_path):
            yield tmp_path

    def test_single_identifier(self):
        mock_series = pd.Series([1.0, 2.0, 3.0], index=["S1", "S2", "S3"], name="TP53")
        with patch("ucscxenatoolspy.query.molecule_value.get_data", return_value=mock_series):
            result = query_molecule_value("ccle_expression", "TP53", host="https://tcga.xenahubs.net")
            pd.testing.assert_series_equal(result, mock_series)

    def test_formula_mode(self):
        tp53 = pd.Series([1, 2, 3], index=["S1", "S2", "S3"], name="TP53")
        kras = pd.Series([4, 5, 6], index=["S1", "S2", "S3"], name="KRAS")

        def mock_get_data(dataset, identifier, **kwargs):
            if identifier == "TP53":
                return tp53
            return kras

        with patch("ucscxenatoolspy.query.molecule_value.get_data", side_effect=mock_get_data):
            result = query_molecule_value("ccle_expression", "TP53 + KRAS", host="https://tcga.xenahubs.net")
            expected = pd.Series([5, 7, 9], index=["S1", "S2", "S3"], name="TP53 + KRAS")
            pd.testing.assert_series_equal(result, expected)

    def test_formula_failure_returns_na(self):
        with patch("ucscxenatoolspy.query.molecule_value.get_data", side_effect=RuntimeError("bad")):
            result = query_molecule_value("ccle_expression", "TP53 + KRAS", host="https://tcga.xenahubs.net")
            assert result.iloc[0] is np.nan or pd.isna(result.iloc[0])


@pytest.mark.slow
@pytest.mark.integration
class TestQueryMoleculeValueLive:
    """Integration tests that hit the real UCSC Xena API."""

    def test_single_gene_live(self):
        """Query a known gene from a known dataset."""
        result = query_molecule_value(
            "XenaTcgaBRCAHer2Total_hg38",
            "ERBB2",
            host="https://ucscpublic.xenahubs.net",
        )
        assert isinstance(result, pd.Series)
        assert len(result) > 0

    def test_cache_speedup(self):
        """Second query should be instant from cache."""
        import time

        query_molecule_value(
            "XenaTcgaBRCAERTotal_hg38",
            "ESR1",
            host="https://ucscpublic.xenahubs.net",
        )
        t0 = time.time()
        query_molecule_value(
            "XenaTcgaBRCAERTotal_hg38",
            "ESR1",
            host="https://ucscpublic.xenahubs.net",
        )
        cached_time = time.time() - t0
        assert cached_time < 1.0  # Cache hit should be under 1 second
