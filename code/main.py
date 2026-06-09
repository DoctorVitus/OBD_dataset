from __future__ import annotations

import argparse
import csv
import io
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


COLUMN_NAMES = ["Time step(ms)", "PID", "Value"]

PID_DESCRIPTIONS = {
    "10C": "Engine RPM",
    "10D": "Vehicle Speed [km/h]",
    "11F": "Runtime since engine start [s]",
    "12F": "Fuel level input [%]",
    "146": "Ambient temperature [C]",
    "149": "Acceleration pedal position D [%]",
    "14A": "Acceleration pedal position E [%]",
    "20": "Acceleration x; y; z",
    "11": "UTC date (DDMMYY)",
    "10": "UTC time (HHMMSSmm)",
    "A": "GPS Latitude [degree]",
    "B": "GPS Longitude [degree]",
    "C": "GPS altitude / auxiliary value",
    "D": "GPS speed / auxiliary value",
    "F": "GPS direction / auxiliary value",
}

SCALAR_PIDS = ["10C", "10D", "11F", "12F", "146", "149", "14A", "A", "B", "C", "D", "F"]
FIGURE_PIDS = ["10C", "10D", "11F", "12F", "146", "149", "14A"]


@dataclass
class RunningStats:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    min_value: float = math.inf
    max_value: float = -math.inf

    def update(self, value: float) -> None:
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)

    @property
    def std(self) -> float:
        if self.count < 2:
            return 0.0
        return math.sqrt(self.m2 / (self.count - 1))


class Reservoir:
    def __init__(self, limit: int, seed: int = 42) -> None:
        self.limit = limit
        self.items: list[tuple[float, float]] = []
        self.seen = 0
        self.random = random.Random(seed)

    def add(self, item: tuple[float, float]) -> None:
        self.seen += 1
        if len(self.items) < self.limit:
            self.items.append(item)
            return
        index = self.random.randrange(self.seen)
        if index < self.limit:
            self.items[index] = item


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze and visualize the OBD dataset.")
    parser.add_argument("--data-dir", default="data", help="Directory containing the raw dataset folders.")
    parser.add_argument("--results-dir", default="results", help="Directory where tables and figures are written.")
    parser.add_argument("--sample-size", type=int, default=50000, help="Maximum sampled points per figure.")
    return parser.parse_args()


def clean_bytes(path: Path) -> str:
    return path.read_bytes().replace(b"\x00", b"").decode("utf-8", errors="replace")


def route_from_path(path: Path) -> tuple[str, str, str]:
    route = next((part for part in path.parts if "Route" in part), "")
    date_folder = next((part for part in path.parts if part.startswith("OBD_Data_")), "")
    route_match = re.search(r"Route(\d+)", route)
    car_match = re.search(r"#(\d+)", route)
    return (
        date_folder.replace("OBD_Data_", ""),
        f"Route{route_match.group(1)}" if route_match else "",
        f"Vehicle{car_match.group(1)}" if car_match else "",
    )


def parse_csv_rows(path: Path):
    text = clean_bytes(path)
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = next(csv.reader([line]))
        except csv.Error:
            yield None
            continue
        if len(row) < 3:
            yield None
            continue
        yield row[0].strip(), row[1].strip(), row[2].strip()


def parse_float(value: str, pid: str) -> float | None:
    try:
        numeric = float(value)
    except ValueError:
        return None
    if pid in {"A", "B"}:
        return numeric * 1e-6
    return numeric


def write_tables(results_dir: Path, inventory: list[dict], pid_stats: dict, file_rows: list[dict], route_rows: dict) -> None:
    pd.DataFrame(inventory).to_csv(results_dir / "dataset_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(file_rows).to_csv(results_dir / "file_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(route_rows.values()).sort_values(["date", "route", "vehicle"]).to_csv(
        results_dir / "route_summary.csv", index=False, encoding="utf-8-sig"
    )

    summary_rows = []
    for pid, stat in sorted(pid_stats.items()):
        summary_rows.append(
            {
                "PID": pid,
                "Description": PID_DESCRIPTIONS.get(pid, ""),
                "numeric_count": stat.count,
                "mean": stat.mean if stat.count else "",
                "std": stat.std if stat.count else "",
                "min": stat.min_value if stat.count else "",
                "max": stat.max_value if stat.count else "",
            }
        )
    pd.DataFrame(summary_rows).to_csv(results_dir / "pid_summary.csv", index=False, encoding="utf-8-sig")


def setup_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "axes.unicode_minus": False,
            "figure.dpi": 160,
            "savefig.dpi": 220,
        }
    )


def dashed_helper_line(frame: pd.DataFrame, x: str, y: str, bins: int = 80) -> pd.DataFrame:
    if frame.empty:
        return frame
    work = frame[[x, y]].dropna().sort_values(x)
    if len(work) <= bins:
        return work
    work["bin"] = pd.qcut(work[x].rank(method="first"), q=bins, duplicates="drop")
    return work.groupby("bin", observed=True).agg({x: "median", y: "median"}).reset_index(drop=True)


def save_time_series_figures(results_dir: Path, samples: dict[str, Reservoir]) -> None:
    figure_dir = results_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    for pid in FIGURE_PIDS:
        data = samples[pid].items
        if not data:
            continue
        frame = pd.DataFrame(data, columns=["Time step(ms)", "Value"]).sort_values("Time step(ms)")
        helper = dashed_helper_line(frame, "Time step(ms)", "Value")

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.scatter(frame["Time step(ms)"], frame["Value"], s=5, alpha=0.28)
        ax.plot(helper["Time step(ms)"], helper["Value"], linestyle="--", linewidth=1.4, color="black")
        ax.set_xlabel("Time step(ms)")
        ax.set_ylabel("Value")
        ax.set_title(f"PID {pid}: {PID_DESCRIPTIONS.get(pid, '')}")
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
        fig.tight_layout()
        fig.savefig(figure_dir / f"pid_{pid}_scatter.png")
        plt.close(fig)


def save_pair_figures(results_dir: Path, pair_samples: dict[str, Reservoir]) -> None:
    figure_dir = results_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    if pair_samples["speed_rpm"].items:
        frame = pd.DataFrame(pair_samples["speed_rpm"].items, columns=["Value_speed_10D", "Value_rpm_10C"])
        helper = dashed_helper_line(frame, "Value_speed_10D", "Value_rpm_10C")
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(frame["Value_speed_10D"], frame["Value_rpm_10C"], s=5, alpha=0.25)
        ax.plot(helper["Value_speed_10D"], helper["Value_rpm_10C"], linestyle="--", linewidth=1.4, color="black")
        ax.set_xlabel("Value (PID 10D Vehicle Speed [km/h])")
        ax.set_ylabel("Value (PID 10C Engine RPM)")
        ax.set_title("Vehicle Speed vs Engine RPM")
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
        fig.tight_layout()
        fig.savefig(figure_dir / "speed_vs_rpm_scatter.png")
        plt.close(fig)

    if pair_samples["gps_route"].items:
        frame = pd.DataFrame(pair_samples["gps_route"].items, columns=["GPS Longitude [degree]", "GPS Latitude [degree]"])
        helper = frame.iloc[:: max(1, len(frame) // 600)]
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(frame["GPS Longitude [degree]"], frame["GPS Latitude [degree]"], s=5, alpha=0.24)
        ax.plot(helper["GPS Longitude [degree]"], helper["GPS Latitude [degree]"], linestyle="--", linewidth=1.0, color="black")
        ax.set_xlabel("GPS Longitude [degree]")
        ax.set_ylabel("GPS Latitude [degree]")
        ax.set_title("GPS Route Samples")
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
        fig.tight_layout()
        fig.savefig(figure_dir / "gps_route_scatter.png")
        plt.close(fig)


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    setup_plot_style()

    csv_paths = sorted(data_dir.rglob("*.CSV"))
    inventory = []
    file_rows = []
    route_rows = defaultdict(lambda: {"date": "", "route": "", "vehicle": "", "files": 0, "rows": 0, "bad_rows": 0})
    pid_counts = Counter()
    pid_stats = defaultdict(RunningStats)
    samples = {pid: Reservoir(args.sample_size, seed=idx + 1) for idx, pid in enumerate(FIGURE_PIDS)}
    pair_samples = {"speed_rpm": Reservoir(args.sample_size, seed=100), "gps_route": Reservoir(args.sample_size, seed=101)}

    for path in data_dir.rglob("*"):
        if path.is_file():
            inventory.append(
                {
                    "path": path.as_posix(),
                    "extension": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                }
            )

    for csv_path in csv_paths:
        date, route, vehicle = route_from_path(csv_path)
        route_key = (date, route, vehicle)
        route_rows[route_key].update({"date": date, "route": route, "vehicle": vehicle})
        route_rows[route_key]["files"] += 1

        file_total = 0
        file_bad = 0
        last_values: dict[str, float] = {}
        for row in parse_csv_rows(csv_path):
            if row is None:
                file_bad += 1
                continue
            time_text, pid, value_text = row
            numeric_time = parse_float(time_text, pid="")
            numeric_value = parse_float(value_text, pid)
            file_total += 1
            pid_counts[pid] += 1

            if numeric_value is not None:
                pid_stats[pid].update(numeric_value)
                if pid in samples and numeric_time is not None:
                    samples[pid].add((numeric_time, numeric_value))
                last_values[pid] = numeric_value

            if "10D" in last_values and "10C" in last_values:
                pair_samples["speed_rpm"].add((last_values["10D"], last_values["10C"]))
            if "A" in last_values and "B" in last_values:
                pair_samples["gps_route"].add((last_values["B"], last_values["A"]))

        file_rows.append(
            {
                "file": csv_path.as_posix(),
                "date": date,
                "route": route,
                "vehicle": vehicle,
                "rows": file_total,
                "bad_rows": file_bad,
                "unique_pids": "",
            }
        )
        route_rows[route_key]["rows"] += file_total
        route_rows[route_key]["bad_rows"] += file_bad

    write_tables(results_dir, inventory, dict(pid_stats), file_rows, route_rows)
    pd.DataFrame(
        [{"PID": pid, "Description": PID_DESCRIPTIONS.get(pid, ""), "rows": count} for pid, count in pid_counts.most_common()]
    ).to_csv(results_dir / "pid_counts.csv", index=False, encoding="utf-8-sig")
    save_time_series_figures(results_dir, samples)
    save_pair_figures(results_dir, pair_samples)

    print(f"Analyzed {len(csv_paths)} CSV files.")
    print(f"Wrote tables to {results_dir.resolve()}.")
    print(f"Wrote figures to {(results_dir / 'figures').resolve()}.")


if __name__ == "__main__":
    main()
