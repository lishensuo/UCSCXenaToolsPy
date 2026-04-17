"""XenaHub model — S4 class replacement using pydantic."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ucscxenatoolspy.api.datalog import (
    _p_cohort_samples_any,
    _p_cohort_samples_all,
    _p_dataset_samples_any,
    _p_dataset_samples_all,
    _p_dataset_samples,
)


class XenaHub(BaseModel):
    """A frozen model representing a selection of UCSC Xena datasets.

    Mirrors the R S4 class `XenaHub` with three slots: hosts, cohorts, datasets.
    Instances are immutable — filtering/querying returns new instances.
    """

    model_config = ConfigDict(frozen=True)

    hosts: list[str]
    cohorts: list[str]
    datasets: list[str]

    def __repr__(self) -> str:
        return self._format_summary()

    def __str__(self) -> str:
        return self._format_summary()

    def _format_summary(self) -> str:
        """Mirror R's show() method output."""
        lines = [f"class: {self.__class__.__name__}"]
        lines.append("hosts():")
        lines.append(f"  {', '.join(self.hosts)}")

        for label, items in [("cohorts", self.cohorts), ("datasets", self.datasets)]:
            total = len(items)
            if total == 0:
                display = "(empty)"
            elif total > 6:
                display = ", ".join(list(items[:3]) + ["...", *items[-2:]]) + f"  ({total} total)"
            else:
                display = ", ".join(items)
            lines.append(f"{label}() ({total} total):")
            lines.append(f"  {display}")

        return "\n".join(lines)


# ── Accessors ──────────────────────────────────────────────────────────────
# These mirror the R accessor functions: hosts(), cohorts(), datasets()


def hosts(x: XenaHub) -> list[str]:
    """Return the hosts list from a XenaHub object."""
    return list(x.hosts)


def cohorts(x: XenaHub) -> list[str]:
    """Return the cohorts list from a XenaHub object."""
    return list(x.cohorts)


def datasets(x: XenaHub) -> list[str]:
    """Return the datasets list from a XenaHub object."""
    return list(x.datasets)


# ── samples() accessor ──────────────────────────────────────────────────────


def samples(
    x: XenaHub,
    i: list[str] | str | None = None,
    by: Literal["hosts", "cohorts", "datasets"] = "datasets",
    how: Literal["each", "any", "all"] = "each",
) -> list | dict:
    """Get samples from a XenaHub object.

    Mirrors R's samples() function. Supports three 'by' modes and three 'how' modes:
    - by="hosts": Get samples by host (using cohorts)
    - by="cohorts": Get samples by cohort
    - by="datasets": Get samples by dataset (default)

    - how="each": Return samples for each host/cohort/dataset separately
    - how="any": Return union of all samples (samples in any of the items)
    - how="all": Return intersection of all samples (samples in all items)

    Args:
        x: A XenaHub object.
        i: Optional subset of hosts/cohorts/datasets to query.
           If None, uses all items from the XenaHub.
        by: What to group by: "hosts", "cohorts", or "datasets".
        how: How to combine: "each", "any", or "all".

    Returns:
        - how="each": A nested list structure (host -> item -> samples)
        - how="any": A flat list of sample IDs (union)
        - how="all": A flat list of sample IDs (intersection)

    Example:
        >>> hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
        >>> samples(hub, by="datasets", how="any")  # all samples in any dataset
    """
    if i is None:
        i = []
    elif isinstance(i, str):
        i = [i]

    if by == "hosts":
        return _samples_by_host(x, i, how)
    elif by == "cohorts":
        return _samples_by_cohort(x, i, how)
    else:  # datasets
        return _samples_by_dataset(x, i, how)


def _samples_by_host(x: XenaHub, hosts_subset: list[str], how: str) -> list | dict:
    """Get samples grouped by host."""
    if not hosts_subset:
        hosts_subset = hosts(x)
    else:
        invalid = [h for h in hosts_subset if h not in hosts(x)]
        if invalid:
            raise ValueError(f"Invalid hosts: {invalid}")

    cohorts_list = cohorts(x)

    result = {}
    for h in hosts_subset:
        samples_list = _p_cohort_samples_any(h, cohorts_list)
        if isinstance(samples_list, list):
            result[h] = samples_list

    if how == "each":
        return result
    elif how == "any":
        return list(set().union(*result.values()))
    else:  # all
        if not result:
            return []
        return list(set.intersection(*[set(s) for s in result.values()]))


def _samples_by_cohort(x: XenaHub, cohorts_subset: list[str], how: str) -> list | dict:
    """Get samples grouped by cohort."""
    if not cohorts_subset:
        cohorts_subset = cohorts(x)
    else:
        invalid = [c for c in cohorts_subset if c not in cohorts(x)]
        if invalid:
            raise ValueError(f"Invalid cohorts: {invalid}")

    hosts_list = hosts(x)

    if how == "each":
        result = {}
        for h in hosts_list:
            host_result = {}
            for c in cohorts_subset:
                samples_list = _p_cohort_samples_any(h, c)
                if isinstance(samples_list, list):
                    host_result[c] = samples_list
            result[h] = host_result
        return result
    elif how == "any":
        result = []
        for h in hosts_list:
            samples_list = _p_cohort_samples_any(h, cohorts_subset)
            if isinstance(samples_list, list):
                result.extend(samples_list)
        return list(set(result))
    else:  # all
        # Intersection across all cohorts
        all_samples = []
        for h in hosts_list:
            samples_list = _p_cohort_samples_all(h, cohorts_subset)
            if isinstance(samples_list, list):
                all_samples.append(set(samples_list))
        if not all_samples:
            return []
        return list(set.intersection(*all_samples))


def _samples_by_dataset(x: XenaHub, datasets_subset: list[str], how: str) -> list | dict:
    """Get samples grouped by dataset."""
    if not datasets_subset:
        datasets_subset = datasets(x)
    else:
        invalid = [d for d in datasets_subset if d not in datasets(x)]
        if invalid:
            raise ValueError(f"Invalid datasets: {invalid}")

    hosts_list = hosts(x)

    if how == "each":
        result = {}
        for h in hosts_list:
            host_result = {}
            for d in datasets_subset:
                samples_list = _p_dataset_samples(h, d, limit=-1)
                if isinstance(samples_list, list):
                    host_result[d] = samples_list
            result[h] = host_result
        return result
    elif how == "any":
        result = []
        for h in hosts_list:
            samples_list = _p_dataset_samples_any(h, datasets_subset)
            if isinstance(samples_list, list):
                result.extend(samples_list)
        return list(set(result))
    else:  # all
        all_samples = []
        for h in hosts_list:
            samples_list = _p_dataset_samples_all(h, datasets_subset)
            if isinstance(samples_list, list):
                all_samples.append(set(samples_list))
        if not all_samples:
            return []
        return list(set.intersection(*all_samples))
