"""XenaHub model — S4 class replacement using pydantic."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
