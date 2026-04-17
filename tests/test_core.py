"""Tests for ucscxena core modules."""

import pytest
import pandas as pd

from ucscxenatoolspy.core.defaults import xena_default_hosts, DEFAULT_HOSTS, HOST_NAME_TO_URL
from ucscxenatoolspy.core.xena_hub import XenaHub, hosts, cohorts, datasets
from ucscxenatoolspy.core.xena_data import load_xena_data
from ucscxenatoolspy.workflow.generate import xena_generate
from ucscxenatoolspy.workflow.filter import xena_filter


class TestDefaults:
    def test_default_hosts_count(self):
        assert len(DEFAULT_HOSTS) == 12

    def test_default_hosts_function(self):
        result = xena_default_hosts()
        assert len(result) == 12
        assert all(u.startswith("https://") for u in result)

    def test_default_hosts_by_name(self):
        assert xena_default_hosts("tcgaHub") == "https://tcga.xenahubs.net"

    def test_invalid_host_name(self):
        with pytest.raises(KeyError):
            xena_default_hosts("invalidHub")

    def test_reverse_mapping(self):
        assert len(HOST_NAME_TO_URL) == 12
        assert HOST_NAME_TO_URL["tcgaHub"] == "https://tcga.xenahubs.net"


class TestXenaHub:
    def test_create(self):
        hub = XenaHub(
            hosts=["https://tcga.xenahubs.net"],
            cohorts=["TCGA Lung Cancer (LUNG)"],
            datasets=["TCGA.LUNG.sampleMap/LUNG_clinicalMatrix"],
        )
        assert hub.hosts == ["https://tcga.xenahubs.net"]
        assert hub.cohorts == ["TCGA Lung Cancer (LUNG)"]

    def test_frozen(self):
        hub = XenaHub(hosts=["a"], cohorts=["b"], datasets=["c"])
        with pytest.raises(Exception):
            hub.hosts = ["modified"]

    def test_repr(self):
        hub = XenaHub(hosts=["a"], cohorts=["b", "c"], datasets=["d"])
        s = repr(hub)
        assert "XenaHub" in s
        assert "cohorts() (2 total)" in s

    def test_empty_lists(self):
        hub = XenaHub(hosts=[], cohorts=[], datasets=[])
        assert hosts(hub) == []
        assert cohorts(hub) == []
        assert datasets(hub) == []

    def test_accessors(self):
        hub = XenaHub(
            hosts=["h1", "h2"],
            cohorts=["c1"],
            datasets=["d1", "d2", "d3"],
        )
        assert hosts(hub) == ["h1", "h2"]
        assert cohorts(hub) == ["c1"]
        assert datasets(hub) == ["d1", "d2", "d3"]


class TestXenaData:
    def test_load_shape(self):
        df = load_xena_data()
        assert df.shape == (2314, 17)

    def test_columns(self):
        df = load_xena_data()
        expected = [
            "XenaHosts", "XenaHostNames", "XenaCohorts", "XenaDatasets",
            "SampleCount", "DataSubtype", "Label", "Type",
            "AnatomicalOrigin", "SampleType", "Tags", "ProbeMap",
            "LongTitle", "Citation", "Version", "Unit", "Platform",
        ]
        assert list(df.columns) == expected

    def test_unique_hosts(self):
        df = load_xena_data()
        # 11 hosts have data in the bundled snapshot (tdiHub may be empty)
        assert df["XenaHosts"].nunique() >= 11


class TestXenaGenerate:
    def test_all_data(self):
        hub = xena_generate()
        # At least 11 hosts have data in bundled snapshot
        assert len(hosts(hub)) >= 11

    def test_filter_by_host_name(self):
        hub = xena_generate(
            subset=lambda df: df["XenaHostNames"] == "tcgaHub"
        )
        assert len(hosts(hub)) == 1
        assert hosts(hub)[0] == "https://tcga.xenahubs.net"

    def test_filter_by_cohort(self):
        hub = xena_generate(
            subset=lambda df: df["XenaCohorts"].str.contains("BRCA", na=False)
        )
        assert len(cohorts(hub)) > 0
        assert all("BRCA" in c for c in cohorts(hub))

    def test_filter_returns_xena_hub(self):
        hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "publicHub")
        assert isinstance(hub, XenaHub)


class TestXenaFilter:
    @pytest.fixture
    def tcga_hub(self):
        return xena_generate(
            subset=lambda df: df["XenaHostNames"] == "tcgaHub"
        )

    def test_filter_datasets(self, tcga_hub):
        filtered = xena_filter(tcga_hub, filter_datasets="clinical")
        assert all("clinical" in d.lower() for d in datasets(filtered))

    def test_filter_datasets_regex(self, tcga_hub):
        filtered = xena_filter(tcga_hub, filter_datasets="LUAD|LUSC")
        assert len(datasets(filtered)) > 0

    def test_filter_cohorts(self, tcga_hub):
        filtered = xena_filter(tcga_hub, filter_cohorts="Lung Cancer")
        assert all("Lung" in c for c in cohorts(filtered))

    def test_no_filter_raises(self, tcga_hub):
        with pytest.raises(ValueError, match="At least one"):
            xena_filter(tcga_hub)

    def test_no_match_raises(self, tcga_hub):
        with pytest.raises(ValueError, match="No matching"):
            xena_filter(tcga_hub, filter_datasets="NONEXISTENT_PATTERN_XYZ")

    def test_returns_new_hub(self, tcga_hub):
        filtered = xena_filter(tcga_hub, filter_datasets="clinical")
        assert isinstance(filtered, XenaHub)
        assert filtered is not tcga_hub
