# Reaction Energy Profile Plotter

A lightweight Python/Jupyter workflow for plotting one-dimensional reaction energy profiles from CSV data.

The project is designed for computational chemistry workflows where relative energies for reactants, intermediates, transition states, and products are already available and need to be converted into clean, publication-ready reaction-coordinate diagrams.

## Features

- Read reaction profiles directly from CSV files
- Plot one or multiple reaction pathways in the same figure
- Custom path names and Matplotlib-compatible colors
- Support missing energy values in individual pathways
- Optional connection across missing states
- Automatic y-axis range with configurable margins
- Configurable energy labels, fonts, line widths, spacing, legend, and title
- Deduplicate identical displayed energy labels at the same reaction state
- Optional zero-energy reference line
- UTF-8, UTF-8 with BOM, and GB18030 CSV decoding
- Automatic detection of comma, semicolon, or tab delimiters
- Return standard Matplotlib `Figure` and `Axes` objects for further customization
- Convenient SVG export through the included Jupyter Notebook

## Repository Layout

A typical repository layout is:

```text
.
├── energy_profile_tools_v20260719_r2.py
├── PES_csv_notebook_v20260719_r2.ipynb
├── example.csv
├── README.md
└── LICENSE
```

The Jupyter Notebook is the main interactive entry point. The Python file is a reusable plotting module and is not intended to be executed directly from the command line.

> If you rename the Python module, update the import statement in the notebook accordingly.

## Requirements

- Python 3.8 or newer
- Matplotlib
- Jupyter Notebook or JupyterLab

Install the required packages with:

```bash
python -m pip install matplotlib jupyter
```

No NumPy or pandas dependency is required by the plotting module.

## Quick Start

1. Place the Python module, notebook, and CSV file in the same directory.
2. Open `PES_csv_notebook_v20260719_r2.ipynb`.
3. Set the input and output filenames in the **User settings** cell.
4. Adjust `PlotConfig` if needed.
5. Run the notebook cells in order.

Example:

```python
from pathlib import Path

from energy_profile_tools_v20260719_r2 import (
    PlotConfig,
    load_profile_csv,
    plot_energy_profile,
)

CSV_FILE = Path("example.csv")
OUTPUT_FILE = Path("energy_profile.svg")

profile = load_profile_csv(CSV_FILE)

config = PlotConfig(
    dpi=600,
    show_title=False,
    show_legend=True,
    show_energy_labels=True,
)

fig, ax = plot_energy_profile(profile, config)
fig.savefig(OUTPUT_FILE, format="svg", bbox_inches="tight")
```

## CSV Format

The first five rows contain figure metadata, pathway names, and pathway colors. Reaction-state data begin on row 6.

General layout:

```text
,Figure title
,Reaction coordinate
,Relative energy (kcal/mol)
,Path A,Path B
,#d62728,#1f77b4
R,0.0,0.0
TS1,15.2,16.4
IM1,-8.1,-6.7
P,-20.4,-18.9
```

The first column of the first five rows can contain descriptive text such as `pic_title`, `X_title`, `Y_title`, `index`, and `color`; the plotting code reads the metadata from the remaining columns.

For example, a single-path file may look like:

```text
pic_title,
X_title,Reaction Path
Y_title,Free Energy (kcal/mol)
index,
color,red
A,0
intAB,32.87450734
B,24.65620693
intBC,31.40695088
C,14.19276212
D,5.978665787
E,8.013446917
```

If a pathway name is omitted, the program automatically assigns a name such as `Path 1`.

If a color is omitted, a color is selected from the current Matplotlib color cycle.

### Missing Values

Blank cells and the following tokens are treated as missing values:

```text
NA
N/A
NaN
None
null
-
```

By default, a pathway is connected only between adjacent reaction states that both contain energy values.

Set:

```python
connect_across_missing_states=True
```

to connect across missing intermediate states.

## Multiple Pathways

Add additional energy columns to the CSV:

```text
,Comparison
,Reaction coordinate
,Relative energy (kcal/mol)
,Path A,Path B,Path C
,red,blue,#2ca02c
R,0.0,0.0,0.0
TS1,15.2,16.4,14.7
IM1,-8.1,-6.7,-7.4
TS2,10.3,12.1,11.0
P,-20.4,-18.9,-21.2
```

Each active energy column is plotted as a separate reaction pathway.

## Plot Configuration

Plot appearance is controlled through `PlotConfig`.

Important options include:

| Option | Default | Description |
|---|---:|---|
| `figsize` | `(10.0, 6.0)` | Figure size in inches |
| `dpi` | `150` | Figure DPI |
| `plateau_width` | `0.82` | Width of horizontal energy levels |
| `state_spacing` | `2.0` | Horizontal spacing between reaction states |
| `plateau_linewidth` | `4.0` | Energy-level line width |
| `connector_linewidth` | `2.4` | Connector line width |
| `connector_linestyle` | `"--"` | Connector line style |
| `zero_line` | `True` | Draw a horizontal line at zero energy |
| `show_energy_labels` | `True` | Display numerical energies |
| `deduplicate_energy_labels` | `True` | Draw identical displayed values only once per state |
| `energy_label_decimals` | `1` | Number of displayed decimal places |
| `show_title` | `False` | Display the title stored in the CSV |
| `show_legend` | `True` | Display pathway legend |
| `connect_across_missing_states` | `False` | Connect non-adjacent available states |
| `x_tick_rotation` | `0.0` | Rotation of reaction-state labels |
| `y_limits` | `None` | Manual `(lower, upper)` y-axis limits |
| `font_family` | `None` | Optional Matplotlib font family |

Example:

```python
config = PlotConfig(
    figsize=(10.0, 6.0),
    dpi=600,
    plateau_linewidth=4.0,
    connector_linewidth=2.4,
    connector_linestyle="--",
    zero_line=True,
    show_energy_labels=True,
    energy_label_decimals=1,
    energy_label_fontsize=20.0,
    tick_fontsize=22.0,
    axis_label_fontsize=28.0,
    legend_fontsize=22.0,
    show_title=False,
    show_legend=True,
    y_limits=None,
)
```

## Using the Python Module Directly

The module exposes four public objects:

```python
ProfileData
PlotConfig
load_profile_csv
plot_energy_profile
```

A minimal non-notebook workflow is:

```python
from energy_profile_tools_v20260719_r2 import (
    PlotConfig,
    load_profile_csv,
    plot_energy_profile,
)

data = load_profile_csv("example.csv")
fig, ax = plot_energy_profile(data, PlotConfig())
fig.savefig("energy_profile.svg", bbox_inches="tight")
```

Because `plot_energy_profile()` returns the Matplotlib `Figure` and `Axes`, additional Matplotlib commands can be applied before saving.

## Output Formats

The included notebook saves SVG by default:

```python
fig.savefig("energy_profile.svg", format="svg", bbox_inches="tight")
```

Other Matplotlib-supported formats can also be used, for example:

```python
fig.savefig("energy_profile.pdf", bbox_inches="tight")
fig.savefig("energy_profile.png", dpi=600, bbox_inches="tight")
```

SVG is recommended when the figure will be edited further in vector-graphics software or used in publication workflows.

## Notes

- Energies are plotted exactly as provided in the CSV. The program does not perform energy normalization, unit conversion, thermochemical correction, or electronic-structure calculations.
- The y-axis label is user-defined, so the numerical data may represent electronic energies, free energies, enthalpies, or other quantities as appropriate.
- Colors must be valid Matplotlib color specifications.
- Non-finite values are treated as missing values.
- This tool is intended for visualization. The user remains responsible for the physical meaning, units, reference state, and scientific interpretation of the supplied data.

## License

This project is released under the MIT License. See `LICENSE` for details.
