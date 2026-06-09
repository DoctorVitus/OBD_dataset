# OBD Dataset Analysis

This repository organizes the provided OBD dataset into three top-level directories:

- `data/`: Original raw files and technical documents, preserved without content edits.
- `code/`: Reproducible analysis and visualization code.
- `results/`: Generated summary tables and figures.

## Run

```powershell
python code/main.py --data-dir data --results-dir results
```

## Outputs

The analysis writes CSV summary tables into `results/`:

- `dataset_inventory.csv`: File inventory with paths, extensions, and file sizes.
- `file_summary.csv`: Per-CSV row counts and parsing-quality counts.
- `route_summary.csv`: Per-date, route, and vehicle row/file summary.
- `pid_counts.csv`: PID frequency table.
- `pid_summary.csv`: Numeric descriptive statistics by PID.

Figures are written into `results/figures/`. All figures use scatter points with a dashed auxiliary trend/path line, and Times New Roman font settings.
