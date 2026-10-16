# Python-VPP

3-DOF Velocity Prediction Program based on the [ORC](https://www.orc.org/index.asp?id=21) aero and hydro dynamic models. 

Please see the demo hosted at [https://yacht-vpp.streamlit.app/](https://yacht-vpp.streamlit.app/) and go for a test sail!

## Using the code

The project is managed with [uv](https://docs.astral.sh/uv/). Install it once (see the [uv docs](https://docs.astral.sh/uv/getting-started/installation/) for other methods):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repository and install the dependencies into a local `.venv`:

```bash
git clone https://github.com/marinlauber/Python-VPP.git
cd Python-VPP
uv sync
```

The main files that are used are `runVPP.py` and `righting_moment.json`. These have to be filled with the data of your boat. By default they are using the YD-41 (from Principle of Yacht Design).

The VPP is run from the root of the repository with

```bash
uv run python runVPP.py
```

At each TWS/TWA the boat speed is maximised over boat speed, heel, leeway, sail flattening and reefing, subject to force and moment equilibrium (SLSQP). `VPP.set_analysis` takes an optional maximum heel angle (`phi_max`, default 35 degrees); the sails are only flattened (down to flat = 0.53) and reefed as much as is fastest within it, following the ORC VPP 2026 depowering scheme. Kites are further limited to their own `max_heel` (default 21.5 degrees, the ORC limit under spinnaker). Points where a sail set cannot be carried within its heel limit are left at 0 and not plotted. The apparent wind follows the ORC heeled wind triangle: TWS is taken at 10 m and scaled to the sail plan's centre of effort with a log wind profile (z0 = 0.005 m), and its cross-track component is reduced by cos(heel). `VPP.run` accepts `method="sequential"` (default) or `"parallel"` (same results, spread over all CPU cores).

To run the Streamlit demo locally:

```bash
uv sync --extra demo --extra api
uv run streamlit run demos/Home.py
```

Once the code has run, it should generate the following figure (or a similar one)

<p align="center">
    <img src="Figure.png" alt="YD-41 VPP results" width="1024">
</p>

See the [documentation](https://marinlauber.github.io/Python-VPP/).

### Input variables

Here is a list of the key variables used in the VPP.

1. Appendages :
    * Cu : Root Chord / Upper Chord (m)
    * Cl : Tip Chord / Lower Chord (m)
    * Span : Span (m)
1. Yacht :
    * Lwl : Length waterline (m)
    * Vol : Displ. volume of canoebody (m^3)
    * Bwl : Beam waterline (m)
    * Tc : Canoe body draft (m)
    * WSA : Wetted surface area (m^2)
    * Tmax : Draft max, i.e. Keel (m)
    * Amax : Max. section area (m^2)
    * Mass : Total mass of the yacht, including keel (kg)
    * Ff : Freeboard height fore (m)
    * Fa : Freeboard height aft (m)
    * Boa : Beam overall (m)
    * Loa : Length overall (m)
    * App : List of appendages
    * Sails : List of Sails
1. Sails:
    Standard measurements, except Roach is defined as 1-A/(0.5PE)
    HBI (jib) is the height of the base of I above the waterline; sail centres of effort (kite vce) are measured from it
    Kite only takes area and vce estimate (this is very rough), min_reef (default 0.85) for depowering and max_heel (default 21.5 degrees)
1. VPP.set_analysis()
    * TWA range : range of TWA to use
    * TWS range : range of TWS, must be between [2, 35]

## Contributing

We are very keen to see contributions to code, documentation and feature development!

When you make a contribution please make sure that any new functionality is covered with additional tests.

Follow the steps below to contribute to this project.

### Install dependencies

Install the project with the development tools (pytest, ruff, mypy) and the API dependencies:

```bash
uv sync --extra dev --extra api
```

Note that `uv sync` removes extras that are not listed, so pass every extra you need (or use `uv sync --all-extras`).

If using `pip` instead:

```bash
pip install -e ".[dev,api]"
```

### Run tests

Tests are implemented using [pytest](https://docs.pytest.org/en/8.0.x/).

You can run tests with

```bash
uv run pytest -vv
```

You can run a benchmark against the YD-41 results from WinVPP by running the `benchmark.py` script (`-g` plots the polars, `-s` saves the results).

```bash
uv run python benchmark/benchmark.py -g -s
```

## Acknowledgements

* **[Otto Villani](https://www.linkedin.com/in/otto-villani-552760108/)** - *Initial idea, model selection* - [GitHub](https://github.com/ottovillani)
* **[Marin Lauber](https://www.linkedin.com/in/marin-lauber/)** - *Initial idea, development* - [GitHub](https://github.com/marinlauber)
* **[Thomas Dickson](https://tajd.co.uk/about)** - *Developer* - [GitHub](http://github.com/TAJD)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
