"""Headless orchestration for reproducible Cardio PyMEA analyses."""

from dataclasses import dataclass, field
from pathlib import Path

from pymea.analysis import (
    beat_amplitude,
    beat_detection,
    conduction_velocity,
    field_potential_duration,
    local_activation_time,
    pacemaker,
    translocation,
    upstroke_velocity,
)
from pymea.core import create_analysis_state
from pymea.io import load_mea_recording


class _NullLabel:
    def __init__(self):
        self.value = ""

    def setText(self, value):
        self.value = value


class _NullSlider:
    def __init__(self):
        self.maximum = 0

    def setMaximum(self, value):
        self.maximum = value


class HeadlessGUI:
    """Minimal stand-in for the Qt widget tree used by legacy modules."""

    def __init__(self):
        self.fileLength = _NullLabel()
        self.mainSlider = _NullSlider()
        self.file_length = 0.0


@dataclass
class AnalysisConfig:
    min_peak_height: float = 100.0
    min_peak_distance: float = 1000.0
    sample_frequency: float = 1000.0
    toggle_trunc: bool = False
    trunc_start: float = 0.0
    trunc_end: float = 0.0
    toggle_silence: bool = False
    silenced_elecs: list[str] = field(default_factory=list)


@dataclass
class AnalysisRun:
    gui: object
    raw_data: object
    cm_beats: object
    pace_maker: object
    upstroke_vel: object
    local_act_time: object
    conduction_vel: object
    field_potential: object
    input_param: object
    heat_map: object
    cm_stats: object
    psd_data: object
    beat_amp_int: object
    batch_data: object
    electrode_config: object


def _populate_batch_inputs(input_param, batch_data, config):
    batch_data.batch_config = True
    input_param.min_peak_height = config.min_peak_height
    input_param.min_peak_dist = config.min_peak_distance
    input_param.parameter_prominence = 100
    input_param.parameter_width = 3
    input_param.parameter_thresh = 50
    input_param.sample_frequency = config.sample_frequency
    input_param.toggle_trunc = config.toggle_trunc
    input_param.trunc_start = config.trunc_start
    input_param.trunc_end = config.trunc_end
    input_param.toggle_silence = config.toggle_silence
    input_param.silenced_elecs = list(config.silenced_elecs)


def run_analysis(recording_path, config=None, include_fpd=False):
    config = config or AnalysisConfig()
    state = create_analysis_state()
    gui = HeadlessGUI()

    raw_data = state["raw_data"]
    raw_data.imported = load_mea_recording(recording_path)
    raw_data.new_data_size = raw_data.imported.shape
    state["electrode_config"].electrode_toggle(raw_data)

    _populate_batch_inputs(state["input_param"], state["batch_data"], config)

    beat_detection.determine_beats(
        gui,
        raw_data,
        state["cm_beats"],
        state["input_param"],
        state["electrode_config"],
        state["batch_data"],
    )
    pacemaker.calculate_pacemaker(
        gui,
        state["cm_beats"],
        state["pace_maker"],
        state["heat_map"],
        state["input_param"],
        state["electrode_config"],
    )
    local_activation_time.calculate_lat(
        gui,
        state["cm_beats"],
        state["local_act_time"],
        state["heat_map"],
        state["input_param"],
        state["electrode_config"],
    )
    upstroke_velocity.calculate_upstroke_vel(
        gui,
        state["cm_beats"],
        state["upstroke_vel"],
        state["heat_map"],
        state["input_param"],
        state["electrode_config"],
    )
    conduction_velocity.calculate_conduction_velocity(
        gui,
        state["cm_beats"],
        state["conduction_vel"],
        state["local_act_time"],
        state["heat_map"],
        state["input_param"],
        state["electrode_config"],
    )
    beat_amplitude.calculate_beat_amp(
        gui,
        state["cm_beats"],
        state["beat_amp_int"],
        state["pace_maker"],
        state["local_act_time"],
        state["heat_map"],
        state["input_param"],
        state["electrode_config"],
    )
    translocation.pm_translocations(
        gui,
        state["pace_maker"],
        state["electrode_config"],
        state["beat_amp_int"],
    )

    if include_fpd:
        field_potential_duration.calc_fpd(
            gui,
            state["cm_beats"],
            state["field_potential"],
            state["local_act_time"],
            state["heat_map"],
            state["input_param"],
            state["electrode_config"],
        )

    return AnalysisRun(gui=gui, **state)


def summarize_run(run, recording_path):
    recording_path = Path(recording_path)
    summary = {
        "recording": str(recording_path),
        "recording_length_minutes": round(run.gui.file_length, 4),
        "electrode_count": len(run.electrode_config.electrode_names),
        "beat_count_mode": int(run.cm_beats.beat_count_dist_mode[0]),
        "excluded_electrodes": int(run.pace_maker.excluded_elec),
        "pacemaker_max_lag_ms": float(run.pace_maker.param_dist_normalized_max),
        "pacemaker_mean_lag_ms": float(run.pace_maker.param_dist_normalized_mean),
        "local_activation_mean_ms": float(run.local_act_time.param_dist_normalized_mean),
        "upstroke_velocity_mean": float(run.upstroke_vel.param_dist_normalized_mean),
        "conduction_velocity_mean": float(run.conduction_vel.param_dist_raw_mean),
        "mean_beat_interval_ms": float(run.beat_amp_int.mean_beat_int),
        "translocation_count": len(
            [event for event in run.pace_maker.transloc_events if event is not None]
        ),
        "translocation_events": [
            int(event) for event in run.pace_maker.transloc_events if event is not None
        ],
        "translocation_times": [
            float(event) for event in run.pace_maker.transloc_times if event is not None
        ],
        "translocation_distances_um": [
            float(event) for event in run.pace_maker.transloc_dist if event is not None
        ],
    }
    if hasattr(run.field_potential, "FPD"):
        summary["field_potential_duration_mean_ms"] = float(
            run.field_potential.FPD.iloc[:, 3:].stack().mean()
        )
    return summary
