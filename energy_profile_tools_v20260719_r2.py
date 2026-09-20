#!/usr/bin/env python3
"""Reusable utilities for plotting reaction energy profiles from CSV data.

This file is intended to be imported by a notebook. It does not provide a
command-line entry point and does not create figures during import.
"""

from __future__ import annotations

import csv
import io
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


__all__ = [
    "ProfileData",
    "PlotConfig",
    "load_profile_csv",
    "plot_energy_profile",
]

PathLike = Union[str, Path]
MISSING_TOKENS = {"", "na", "n/a", "nan", "none", "null", "-"}


@dataclass
class ProfileData:
    """Reaction profile data parsed from a CSV file."""

    title: str
    x_label: str
    y_label: str
    state_labels: List[str]
    path_labels: List[str]
    colors: List[str]
    energies: List[List[Optional[float]]]


@dataclass
class PlotConfig:
    """Plot appearance and label behavior."""

    figsize: Tuple[float, float] = (10.0, 6.0)
    dpi: int = 150
    plateau_width: float = 0.82
    state_spacing: float = 2.0
    plateau_linewidth: float = 4.0
    connector_linewidth: float = 2.4
    connector_linestyle: str = "--"
    zero_line: bool = True
    zero_line_color: str = "0.55"
    zero_line_width: float = 1.4
    show_energy_labels: bool = True
    deduplicate_energy_labels: bool = True
    energy_label_decimals: int = 1
    energy_label_fontsize: float = 16.0
    energy_label_vertical_offset: float = 8.0
    energy_label_horizontal_spacing: float = 40.0
    tick_fontsize: float = 15.0
    axis_label_fontsize: float = 19.0
    legend_fontsize: float = 14.0
    title_fontsize: float = 18.0
    show_title: bool = False
    show_legend: bool = True
    connect_across_missing_states: bool = False
    x_tick_rotation: float = 0.0
    y_limits: Optional[Tuple[float, float]] = None
    y_margin_fraction: float = 0.14
    minimum_y_margin: float = 0.5
    spine_linewidth: float = 1.8
    font_family: Optional[str] = None


@dataclass
class _LabelGroup:
    values: List[float]
    colors: List[str]
    text: str


def _read_text_with_fallback(path: Path, encoding: Optional[str]) -> str:
    if encoding is not None:
        return path.read_text(encoding=encoding)

    for candidate in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=candidate)
        except UnicodeDecodeError:
            continue

    raise ValueError("Unable to decode the CSV as UTF-8 or GB18030.")


def _detect_delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        return dialect.delimiter
    except csv.Error:
        return ","


def _strip_rows(rows: Sequence[Sequence[str]]) -> List[List[str]]:
    cleaned = [[cell.strip() for cell in row] for row in rows]
    while cleaned and not any(cleaned[-1]):
        cleaned.pop()
    return cleaned


def _parse_energy(value: str, row_number: int, column_number: int) -> Optional[float]:
    token = value.strip()
    if token.lower() in MISSING_TOKENS:
        return None

    try:
        number = float(token)
    except ValueError as exc:
        raise ValueError(
            "Invalid energy at CSV row {0}, column {1}: {2!r}".format(
                row_number, column_number, value
            )
        ) from exc

    if not math.isfinite(number):
        return None
    return number


def _default_colors(count: int) -> List[str]:
    color_cycle = plt.rcParams.get("axes.prop_cycle")
    colors = color_cycle.by_key().get("color", []) if color_cycle is not None else []
    if not colors:
        colors = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]
    return [colors[index % len(colors)] for index in range(count)]


def load_profile_csv(
    csv_file: PathLike,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> ProfileData:
    """Read the original five-row profile layout from a CSV file.

    Expected layout:

        ,Figure title
        ,Reaction coordinate
        ,Relative energy (kcal/mol)
        ,Path A,Path B
        ,#d62728,#1f77b4
        R,0.0,0.0
        TS1,15.2,16.4
        IM1,-8.1,-6.7

    Blank energy cells are treated as missing values.
    """

    path = Path(csv_file)
    if not path.is_file():
        raise FileNotFoundError("CSV file not found: {0}".format(path))

    text = _read_text_with_fallback(path, encoding)
    selected_delimiter = delimiter or _detect_delimiter(text)
    rows = _strip_rows(
        list(csv.reader(io.StringIO(text), delimiter=selected_delimiter))
    )

    if len(rows) < 6:
        raise ValueError(
            "The CSV must contain five metadata rows followed by at least one state row."
        )

    title = rows[0][1] if len(rows[0]) > 1 else ""
    x_label = (
        rows[1][1]
        if len(rows[1]) > 1 and rows[1][1]
        else "Reaction coordinate"
    )
    y_label = (
        rows[2][1]
        if len(rows[2]) > 1 and rows[2][1]
        else "Relative energy"
    )

    maximum_columns = max(len(row) for row in rows)
    candidate_path_count = max(0, maximum_columns - 1)
    if candidate_path_count == 0:
        raise ValueError("No energy columns were found in the CSV.")

    raw_path_labels = (rows[3][1:] + [""] * candidate_path_count)[:candidate_path_count]
    raw_colors = (rows[4][1:] + [""] * candidate_path_count)[:candidate_path_count]

    state_labels: List[str] = []
    energy_rows: List[List[Optional[float]]] = []

    for row_number, row in enumerate(rows[5:], start=6):
        padded = list(row) + [""] * (candidate_path_count + 1 - len(row))
        state_label = padded[0].strip()
        energy_tokens = padded[1 : candidate_path_count + 1]

        if not state_label and not any(token.strip() for token in energy_tokens):
            continue
        if not state_label:
            raise ValueError("Missing state label at CSV row {0}.".format(row_number))

        parsed_values = [
            _parse_energy(token, row_number, column_number)
            for column_number, token in enumerate(energy_tokens, start=2)
        ]
        state_labels.append(state_label)
        energy_rows.append(parsed_values)

    if not state_labels:
        raise ValueError("No reaction states were found in the CSV.")

    active_columns: List[int] = []
    for column_index in range(candidate_path_count):
        label_present = bool(raw_path_labels[column_index].strip())
        color_present = bool(raw_colors[column_index].strip())
        energy_present = any(
            row[column_index] is not None for row in energy_rows
        )
        if label_present or color_present or energy_present:
            active_columns.append(column_index)

    if not active_columns:
        raise ValueError("All path columns are empty.")

    fallback_colors = _default_colors(len(active_columns))
    path_labels: List[str] = []
    colors: List[str] = []
    energies: List[List[Optional[float]]] = []

    for output_index, column_index in enumerate(active_columns):
        label = raw_path_labels[column_index].strip() or "Path {0}".format(
            output_index + 1
        )
        color = raw_colors[column_index].strip() or fallback_colors[output_index]

        if not is_color_like(color):
            raise ValueError(
                "Invalid Matplotlib color for {0!r}: {1!r}".format(label, color)
            )

        path_values = [row[column_index] for row in energy_rows]
        if not any(value is not None for value in path_values):
            warnings.warn("Skipping empty path {0!r}.".format(label), RuntimeWarning)
            continue

        path_labels.append(label)
        colors.append(color)
        energies.append(path_values)

    if not energies:
        raise ValueError("No numeric energy values were found.")

    return ProfileData(
        title=title,
        x_label=x_label,
        y_label=y_label,
        state_labels=state_labels,
        path_labels=path_labels,
        colors=colors,
        energies=energies,
    )


def _format_energy(value: float, decimals: int) -> str:
    if decimals < 0:
        raise ValueError("energy_label_decimals must be zero or greater.")

    threshold = 0.5 * 10.0 ** (-decimals)
    normalized = 0.0 if abs(value) < threshold else value
    return "{0:.{1}f}".format(normalized, decimals)


def _all_energies(data: ProfileData) -> List[float]:
    return [
        value
        for path_values in data.energies
        for value in path_values
        if value is not None
    ]


def _validate_data(data: ProfileData) -> None:
    state_count = len(data.state_labels)
    if state_count == 0:
        raise ValueError("At least one reaction state is required.")
    if not data.energies:
        raise ValueError("At least one reaction path is required.")
    if len(data.path_labels) != len(data.energies):
        raise ValueError("The number of path labels does not match the path data.")
    if len(data.colors) != len(data.energies):
        raise ValueError("The number of colors does not match the path data.")
    if any(len(path_values) != state_count for path_values in data.energies):
        raise ValueError("Every path must contain one entry for each reaction state.")
    if not _all_energies(data):
        raise ValueError("No finite energy values are available for plotting.")


def _set_y_limits(ax: Axes, data: ProfileData, config: PlotConfig) -> None:
    if config.y_limits is not None:
        lower, upper = config.y_limits
        if lower >= upper:
            raise ValueError("The lower y limit must be smaller than the upper y limit.")
        ax.set_ylim(lower, upper)
        return

    values = _all_energies(data)
    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum
    if span == 0.0:
        span = max(abs(maximum), 1.0)
    margin = max(span * config.y_margin_fraction, config.minimum_y_margin)
    ax.set_ylim(minimum - margin, maximum + margin)


def _label_groups_for_state(
    data: ProfileData,
    state_index: int,
    config: PlotConfig,
) -> List[Tuple[float, str, str]]:
    grouped: Dict[str, _LabelGroup] = {}

    for path_index, path_values in enumerate(data.energies):
        value = path_values[state_index]
        if value is None:
            continue

        text = _format_energy(value, config.energy_label_decimals)
        if config.deduplicate_energy_labels:
            key = text
        else:
            key = "{0}:{1}".format(path_index, text)

        if key not in grouped:
            grouped[key] = _LabelGroup(values=[], colors=[], text=text)
        grouped[key].values.append(value)
        grouped[key].colors.append(data.colors[path_index])

    entries: List[Tuple[float, str, str]] = []
    for group in grouped.values():
        label_y = sum(group.values) / len(group.values)
        unique_colors = list(dict.fromkeys(group.colors))
        label_color = unique_colors[0] if len(unique_colors) == 1 else "black"
        entries.append((label_y, group.text, label_color))

    return sorted(entries, key=lambda entry: entry[0])


def _draw_energy_labels(
    ax: Axes,
    data: ProfileData,
    centers: Sequence[float],
    config: PlotConfig,
) -> None:
    lower_limit, upper_limit = ax.get_ylim()

    for state_index, center in enumerate(centers):
        entries = [
            entry
            for entry in _label_groups_for_state(data, state_index, config)
            if lower_limit <= entry[0] <= upper_limit
        ]
        entry_count = len(entries)
        if entry_count == 0:
            continue

        for rank, (value, text, color) in enumerate(entries):
            x_offset = (
                rank - (entry_count - 1) / 2.0
            ) * config.energy_label_horizontal_spacing
            ax.annotate(
                text,
                xy=(center, value),
                xytext=(x_offset, config.energy_label_vertical_offset),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=config.energy_label_fontsize,
                color=color,
                clip_on=True,
                annotation_clip=True,
                zorder=5,
            )


def plot_energy_profile(
    data: ProfileData,
    config: Optional[PlotConfig] = None,
) -> Tuple[Figure, Axes]:
    """Create a reaction energy profile and return its Figure and Axes."""

    selected_config = config or PlotConfig()
    _validate_data(data)

    if selected_config.dpi <= 0:
        raise ValueError("dpi must be greater than zero.")
    if selected_config.state_spacing <= 0:
        raise ValueError("state_spacing must be greater than zero.")
    if selected_config.plateau_width <= 0:
        raise ValueError("plateau_width must be greater than zero.")
    if selected_config.plateau_width >= selected_config.state_spacing:
        raise ValueError("plateau_width must be smaller than state_spacing.")

    state_count = len(data.state_labels)
    centers = [
        index * selected_config.state_spacing for index in range(state_count)
    ]
    half_width = selected_config.plateau_width / 2.0

    rc_settings = {"axes.unicode_minus": False}
    if selected_config.font_family:
        rc_settings["font.family"] = selected_config.font_family

    with matplotlib.rc_context(rc_settings):
        fig, ax = plt.subplots(
            figsize=selected_config.figsize,
            dpi=selected_config.dpi,
            constrained_layout=True,
        )

        legend_handles: List[Line2D] = []

        for path_index, path_values in enumerate(data.energies):
            color = data.colors[path_index]
            label = data.path_labels[path_index]

            for state_index, value in enumerate(path_values):
                if value is None:
                    continue
                center = centers[state_index]
                ax.plot(
                    [center - half_width, center + half_width],
                    [value, value],
                    color=color,
                    linewidth=selected_config.plateau_linewidth,
                    solid_capstyle="butt",
                    zorder=3,
                )

            previous_index: Optional[int] = None
            previous_value: Optional[float] = None

            for state_index, value in enumerate(path_values):
                if value is None:
                    continue

                if previous_index is not None and previous_value is not None:
                    states_are_adjacent = state_index == previous_index + 1
                    if (
                        states_are_adjacent
                        or selected_config.connect_across_missing_states
                    ):
                        ax.plot(
                            [
                                centers[previous_index] + half_width,
                                centers[state_index] - half_width,
                            ],
                            [previous_value, value],
                            color=color,
                            linewidth=selected_config.connector_linewidth,
                            linestyle=selected_config.connector_linestyle,
                            zorder=2,
                        )

                previous_index = state_index
                previous_value = value

            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    color=color,
                    linewidth=selected_config.connector_linewidth,
                    linestyle=selected_config.connector_linestyle,
                    label=label,
                )
            )

        if selected_config.zero_line:
            ax.axhline(
                0.0,
                color=selected_config.zero_line_color,
                linewidth=selected_config.zero_line_width,
                linestyle="--",
                zorder=1,
            )

        _set_y_limits(ax, data, selected_config)

        x_margin = max(
            selected_config.state_spacing * 0.42,
            half_width + 0.12,
        )
        ax.set_xlim(centers[0] - x_margin, centers[-1] + x_margin)
        ax.set_xticks(centers)
        ax.set_xticklabels(
            data.state_labels,
            rotation=selected_config.x_tick_rotation,
            ha="right" if selected_config.x_tick_rotation else "center",
            fontsize=selected_config.tick_fontsize,
        )
        ax.tick_params(
            axis="y",
            labelsize=selected_config.tick_fontsize,
            width=selected_config.spine_linewidth,
        )
        ax.tick_params(axis="x", width=selected_config.spine_linewidth)

        ax.set_xlabel(
            data.x_label,
            fontsize=selected_config.axis_label_fontsize,
            fontweight="bold",
        )
        ax.set_ylabel(
            data.y_label,
            fontsize=selected_config.axis_label_fontsize,
            fontweight="bold",
        )

        if selected_config.show_title and data.title:
            ax.set_title(
                data.title,
                fontsize=selected_config.title_fontsize,
                fontweight="bold",
            )

        if selected_config.show_energy_labels:
            _draw_energy_labels(ax, data, centers, selected_config)

        if selected_config.show_legend and legend_handles:
            ax.legend(
                handles=legend_handles,
                fontsize=selected_config.legend_fontsize,
                frameon=True,
            )

        for spine in ax.spines.values():
            spine.set_linewidth(selected_config.spine_linewidth)

    return fig, ax
