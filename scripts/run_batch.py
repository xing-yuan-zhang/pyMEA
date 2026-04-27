import argparse
from pathlib import Path
import shutil
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pymea.export import collect_output_tables, export_tables_csv, export_tables_excel
from pymea.io import slugify_run_name, write_json
from pymea.pipeline import AnalysisConfig, run_analysis, summarize_run


EXPECTED_COLUMNS = [
    "file_dir",
    "file_name",
    "min_pk_height",
    "min_pk_dist",
    "sample_frequency",
    "toggle_trunc",
    "trunc_start",
    "trunc_end",
    "toggle_silence",
    "silenced_electrodes",
]


def read_batch_sheet(path):
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def as_bool(value):
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def build_parser():
    parser = argparse.ArgumentParser(description="Run Cardio PyMEA batch analysis from a spreadsheet.")
    parser.add_argument("batch_sheet", help="Path to the batch CSV or Excel sheet.")
    parser.add_argument("--output-dir", default=str(ROOT / "results"))
    parser.add_argument("--include-fpd", action="store_true")
    parser.add_argument("--export-workbook", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def row_to_config(row):
    silenced = row["silenced_electrodes"]
    if pd.isna(silenced) or str(silenced).strip() == "":
        silenced_elecs = []
    else:
        silenced_elecs = [item.strip() for item in str(silenced).split(",") if item.strip()]

    return AnalysisConfig(
        min_peak_height=float(row["min_pk_height"]),
        min_peak_distance=float(row["min_pk_dist"]),
        sample_frequency=float(row["sample_frequency"]),
        toggle_trunc=as_bool(row["toggle_trunc"]),
        trunc_start=float(row["trunc_start"]) if not pd.isna(row["trunc_start"]) else 0.0,
        trunc_end=float(row["trunc_end"]) if not pd.isna(row["trunc_end"]) else 0.0,
        toggle_silence=as_bool(row["toggle_silence"]),
        silenced_elecs=silenced_elecs,
    )


def main():
    parser = build_parser()
    args = parser.parse_args()

    batch_sheet = Path(args.batch_sheet).resolve()
    output_dir = Path(args.output_dir).resolve() / slugify_run_name(batch_sheet.stem)

    if output_dir.exists():
        if not args.overwrite:
            parser.error(f"Output directory already exists: {output_dir}. Use --overwrite to reuse it.")
        shutil.rmtree(output_dir)

    batch_df = read_batch_sheet(batch_sheet)
    missing_columns = [column for column in EXPECTED_COLUMNS if column not in batch_df.columns]
    if missing_columns:
        parser.error(f"Batch sheet is missing required columns: {missing_columns}")

    summaries = []
    translocation_rows = []

    for _, row in batch_df.iterrows():
        file_dir = Path(row["file_dir"])
        if not file_dir.is_absolute():
            file_dir = (batch_sheet.parent / file_dir).resolve()
        recording_path = file_dir / str(row["file_name"])
        run_name = slugify_run_name(Path(row["file_name"]).stem)
        run_dir = output_dir / run_name
        config = row_to_config(row)

        run = run_analysis(recording_path, config, include_fpd=args.include_fpd)
        summary = summarize_run(run, recording_path)
        write_json(run_dir / "summary.json", summary)
        write_json(run_dir / "resolved_config.json", config.__dict__)
        export_tables_csv(collect_output_tables(run), run_dir / "tables")
        if args.export_workbook:
            export_tables_excel(collect_output_tables(run), run_dir / "analysis_tables.xlsx")

        summaries.append(summary)
        for event, event_time, distance in zip(
            summary["translocation_events"],
            summary["translocation_times"],
            summary["translocation_distances_um"],
        ):
            translocation_rows.append(
                {
                    "recording": str(recording_path),
                    "event_length_beats": event,
                    "event_time_ms": event_time,
                    "distance_um": distance,
                }
            )

    pd.DataFrame(summaries).to_csv(output_dir / "batch_summary.csv", index=False)
    pd.DataFrame(translocation_rows).to_csv(output_dir / "batch_translocations.csv", index=False)
    write_json(output_dir / "batch_summary.json", {"recordings": summaries})

    print(f"Processed {len(summaries)} recordings from {batch_sheet.name}")
    print(f"Batch results written to: {output_dir}")


if __name__ == "__main__":
    main()
