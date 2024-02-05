# Python-VPP

3-DOF Velocity Prediction Program base on the [ORC](https://www.orc.org/index.asp?id=21) aero and hydro dynamic models. The code makes use of Object-oriented-Programming to be as general as possible.

## Contributing

### Installing dependencies

Install the required dependencies from the `requirements.txt` file.

If using `pip` then `pip install requirements.txt`.

If using `conda` then follow these steps to create an environment with the right dependencies:

```bash
conda create --name Python-VPP \
    && conda config --add channels conda-forge \
    && conda activate Python-VPP \
    && conda install -y --file requirements.txt
```

### Running tests

Tests are implemented using [pytest](https://docs.pytest.org/en/8.0.x/).

You can run tests with

```bash
pytest -vv
```

You can run a benchmark against the YD-41 results from WinVPP by running the `benchmark.py` script.

```bash
$ python benchmark/benchmark.py -g -o
```

with `save`, `graph` and `output` as optional keyboard arguments and `output` only working in combination with `save`.

## Using the code

To use the code, first clone or download this repository onto your own machine. The main file that are used are `runVPP.py` and `righting_moment.json`. These have to be filled with the data of your boat. By default they are using the YD-41 (from Principle of Yacht Design). To run the code simply type

```bash
$ python runVPP.py
```

into your console, and the code should run. Once the code has run, it should generate the following figure (or a similar one)

<p align="center">
    <img src="Figure.png" alt="YD-41 VPP results" width="1024">
</p>

See the [documentation](https://marinlauber.github.io/Python-VPP/).

### Input variable

This is a crude list of all the input variables and their meaning, as well as the units they are expected to be in.

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


## Authors

* **[Otto Villani](https://www.linkedin.com/in/otto-villani-552760108/)** - *Initial idea, model selection* - [github](https://github.com/ottovillani)
* **[Marin Lauber](https://www.linkedin.com/in/marin-lauber/)** - *Initial idea, developement* - [github](https://github.com/marinlauber)
* **[Thomas Dickson](https://tajd.co.uk/about)** - *Developer* - [github](http://github.com/TAJD)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration

## Modifications

1. Formatted using [Black](https://github.com/psf/black).
1. Added a "name" to the Yacht class which can be passed to plotting function.
1. Renamed instances of Keel and Rudder objects in the example function.
