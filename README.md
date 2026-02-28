# Python-VPP

3-DOF Velocity Prediction Program based on the [ORC](https://www.orc.org/index.asp?id=21) aero and hydro dynamic models. 

Please see the demo hosted at [https://yacht-vpp.streamlit.app/](https://yacht-vpp.streamlit.app/) and go for a test sail!

## Using the code

To use the code, first clone or download this repository then install the required dependencies (see below).

The main files that are used are `runVPP.py` and `righting_moment.json`. These have to be filled with the data of your boat. By default they are using the YD-41 (from Principle of Yacht Design).

The VPP is run with.

```bash
$ python runVPP.py
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
    Kite only takes area and vce estimate (this is very rough)
1. VPP.set_analysis()
    * TWA range : range of TWA to use
    * TWS range : range of TWS, must be between [2, 35]

## Contributing

We are very keen to see contributions to code, documentation and feature development!

When you make a contribution please make sure that any new functionality is covered with additional tests.

Follow the steps below to contribute to this project.

### Install dependencies

Install the required dependencies from the `requirements.txt` file.

If using `pip` then `pip install -r requirements.txt`.

If using `conda` then follow these steps to create an environment with the right dependencies:

```bash
conda create --name Python-VPP \
    && conda config --add channels conda-forge \
    && conda activate Python-VPP \
    && conda install -y --file requirements.txt
```

### Run tests

Tests are implemented using [pytest](https://docs.pytest.org/en/8.0.x/).

You can run tests with

```bash
pytest -vv
```

You can run a benchmark against the YD-41 results from WinVPP by running the `benchmark.py` script.

```bash
$ python benchmark/benchmark.py -g -o
```

## Acknowledgements

* **[Otto Villani](https://www.linkedin.com/in/otto-villani-552760108/)** - *Initial idea, model selection* - [GitHub](https://github.com/ottovillani)
* **[Marin Lauber](https://www.linkedin.com/in/marin-lauber/)** - *Initial idea, development* - [GitHub](https://github.com/marinlauber)
* **[Thomas Dickson](https://tajd.co.uk/about)** - *Developer* - [GitHub](http://github.com/TAJD)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
