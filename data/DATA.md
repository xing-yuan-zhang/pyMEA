# Data

Includes small example recordings plus batch templates for reproducing workflow.

## Layout

- `examples/`: representative MC_DataTool text exports used for smoke testing and demonstrations.
- `metadata/`: ancillary files such as batch templates.

## Expected input format

Cardio PyMEA expects text exports from Multichannel Systems recordings converted with MC_DataTool. The loader in `src/cardio_pymea/io.py` supports the tab-delimited and comma-delimited variants observed in the original repository.

Each recording should contain:

- a time column in milliseconds
- one column per electrode signal
- the original three-line MC_DataTool header

## Batch templates

`metadata/batch_example.csv` is a runnable example for the headless CLI.

`metadata/batch_template_untreated_mea120.xlsx` is the original inherited template and is preserved for provenance. It may require path edits before use.

Both formats use the same schema:

- `file_dir`
- `file_name`
- `min_pk_height`
- `min_pk_dist`
- `sample_frequency`
- `toggle_trunc`
- `trunc_start`
- `trunc_end`
- `toggle_silence`
- `silenced_electrodes`
