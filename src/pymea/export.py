"""Export helpers for analysis tables and summaries."""

from pathlib import Path

import pandas as pd


def collect_output_tables(run):
    tables = {
        "pacemaker_normalized": run.pace_maker.param_dist_normalized,
        "pacemaker_raw": run.pace_maker.param_dist_raw,
        "pacemaker_per_beat_max": run.pace_maker.param_dist_normalized_per_beat_max,
        "local_activation_time_normalized": run.local_act_time.param_dist_normalized,
        "local_activation_time_distance": run.local_act_time.distance_from_min,
        "upstroke_velocity": run.upstroke_vel.param_dist_normalized,
        "conduction_velocity": run.conduction_vel.param_dist_raw,
        "conduction_velocity_vector_magnitude": run.conduction_vel.vector_mag,
        "conduction_velocity_vector_x": run.conduction_vel.vector_x_comp,
        "conduction_velocity_vector_y": run.conduction_vel.vector_y_comp,
        "beat_amplitude": run.beat_amp_int.beat_amp,
        "delta_beat_amplitude": run.beat_amp_int.delta_beat_amp,
        "beat_interval": run.beat_amp_int.beat_interval,
    }
    if hasattr(run.field_potential, "FPD"):
        tables["field_potential_duration"] = run.field_potential.FPD
    return tables


def export_tables_csv(tables, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        target = output_dir / f"{name}.csv"
        if isinstance(table, pd.Series):
            table.to_csv(target, header=True)
        else:
            table.to_csv(target)


def export_tables_excel(tables, workbook_path):
    workbook_path = Path(workbook_path)
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(workbook_path) as writer:
        for name, table in tables.items():
            sheet_name = name[:31]
            if isinstance(table, pd.Series):
                table.to_frame(name=name).to_excel(writer, sheet_name=sheet_name)
            else:
                table.to_excel(writer, sheet_name=sheet_name)
