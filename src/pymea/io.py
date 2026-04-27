"""Data loading and configuration helpers."""

import json
from pathlib import Path

import pandas as pd


def load_mea_recording(path):
    """Load MC_DataTool text exports observed in this repository.

    Supports both tab-delimited and comma-delimited exports while preserving the
    original three-line MC_DataTool header convention.
    """

    path = Path(path)
    data = pd.read_csv(
        path,
        sep=r"\t+|,",
        engine="python",
        skiprows=3,
        header=0,
        encoding="iso-8859-15",
        skipinitialspace=True,
        low_memory=False,
    )
    data = data.dropna(axis="columns", how="all")
    clean_columns = [str(col).strip() for col in data.columns]
    data.columns = clean_columns
    data = data.loc[:, [col for col in data.columns if col and col != "\r"]]
    return data.apply(pd.to_numeric, errors="coerce")


def read_json_config(path):
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def slugify_run_name(name):
    return "".join(
        char.lower() if char.isalnum() else "_" for char in name
    ).strip("_")
