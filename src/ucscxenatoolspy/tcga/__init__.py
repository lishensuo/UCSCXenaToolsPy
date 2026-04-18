"""TCGA built-in clinical and survival datasets."""

from pathlib import Path

import pandas as pd

_DATA_DIR = Path(__file__).parent.parent / "data"


def tcga_clinical() -> pd.DataFrame:
    """Load the built-in TCGA clinical dataset.

    Returns:
        DataFrame with columns: Sample, Cancer, Age, Code, Gender,
        Stage_ajcc, Stage_clinical, Grade
    """
    return pd.read_csv(_DATA_DIR / "tcga_clinical.csv.gz")


def tcga_survival() -> pd.DataFrame:
    """Load the built-in TCGA survival dataset.

    Returns:
        DataFrame with columns: Sample, OS, OS.time, DSS, DSS.time,
        DFI, DFI.time, PFI, PFI.time
    """
    return pd.read_csv(_DATA_DIR / "tcga_survival.csv.gz")
