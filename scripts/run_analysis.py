import argparse
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pymea.export import collect_output_tables, export_tables_csv, export_tables_excel
from pymea.io import read_json_config, slugify_run_name, write_json
from pymea.pipeline import AnalysisConfig, run_analysis, summarize_run


def build_parser():
    parser = argparse.ArgumentParser(description="Run the headless Cardio PyMEA pipeline.")
    parser.add_argument("recording", help="Path to the MEA recording text export.")
    parser.add_argument("--config", help="Optional JSON config path.")
    parser.add_argument("--output-dir", default=str(ROOT / "results"))
    parser.add_argument("--run-name", help="Optional run directory name.")
    parser.add_argument("--include-fpd", action="store_true", help="Also compute field potential duration.")
    parser.add_argument("--export-workbook", action="store_true", help="Write an Excel workbook alongside CSV tables.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing run directory.")
    parser.add_argument("--min-peak-height", type=float)
    parser.add_argument("--min-peak-distance", type=float)
    parser.add_argument("--sample-frequency", type=float)
    return parser


def build_config(args):
    config_payload = {}
    if args.config:
        config_payload.update(read_json_config(args.config))

    if args.min_peak_height is not None:
        config_payload["min_peak_height"] = args.min_peak_height
    if args.min_peak_distance is not None:
        config_payload["min_peak_distance"] = args.min_peak_distance
    if args.sample_frequency is not None:
        config_payload["sample_frequency"] = args.sample_frequency

    return AnalysisConfig(**config_payload)


def main():
    parser = build_parser()
    args = parser.parse_args()

    recording_path = Path(args.recording).resolve()
    config = build_config(args)
    run_name = args.run_name or slugify_run_name(recording_path.stem)
    run_dir = Path(args.output_dir).resolve() / run_name

    if run_dir.exists():
        if not args.overwrite:
            parser.error(f"Output directory already exists: {run_dir}. Use --overwrite to reuse it.")
        shutil.rmtree(run_dir)

    run = run_analysis(recording_path, config, include_fpd=args.include_fpd)
    summary = summarize_run(run, recording_path)
    tables = collect_output_tables(run)

    write_json(run_dir / "summary.json", summary)
    write_json(run_dir / "resolved_config.json", config.__dict__)
    export_tables_csv(tables, run_dir / "tables")
    if args.export_workbook:
        export_tables_excel(tables, run_dir / "analysis_tables.xlsx")

    print(f"Completed analysis for {recording_path.name}")
    print(f"Beat count mode: {summary['beat_count_mode']}")
    print(f"Translocation count: {summary['translocation_count']}")
    print(f"Results written to: {run_dir}")


if __name__ == "__main__":
    main()
