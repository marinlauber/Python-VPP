"""Pluggable wind models for race simulation.

All wind models implement the same interface: given a timestep and RNG,
return the current (tws, twd) state.  This makes it straightforward to
swap in more sophisticated models (spatial fields, gusts, thermal
effects) without changing the race engine.

Usage
-----
>>> model = BrownianWind(tws=10.0, twd=0.0, dir_sigma=2.0)
>>> tws, twd = model.update(dt=1.0, rng=np.random.default_rng(42))
"""

from __future__ import annotations

import numpy as np


class WindModel:
    """Base class for wind models.

    Subclasses must implement :meth:`update` and :meth:`state`.
    """

    def __init__(self, tws: float, twd: float = 0.0):
        self.tws = tws
        self.twd = twd

    def update(self, dt: float, rng: np.random.Generator) -> tuple[float, float]:
        """Advance the wind state by *dt* seconds.

        Returns
        -------
        (tws, twd) : tuple of float
            Current true wind speed (knots) and direction (degrees).
        """
        return self.tws, self.twd

    def state(self) -> dict:
        """Serialisable snapshot for reproducibility."""
        return {"tws": self.tws, "twd": self.twd, "model": type(self).__name__}

    def reset(self, tws: float | None = None, twd: float = 0.0):
        """Reset to initial conditions."""
        if tws is not None:
            self.tws = tws
        self.twd = twd


class ConstantWind(WindModel):
    """Fixed wind — no variation at all."""
    pass


class BrownianWind(WindModel):
    """Brownian motion on wind direction only.

    Parameters
    ----------
    tws : float
        Constant true wind speed (knots).
    twd : float
        Initial wind direction (degrees).
    dir_sigma : float
        Direction volatility (deg / sqrt(min)).  Default 2.0.
    """

    def __init__(self, tws: float, twd: float = 0.0, dir_sigma: float = 2.0):
        super().__init__(tws, twd)
        self.dir_sigma = dir_sigma
        self._tws_base = tws

    def update(self, dt: float, rng: np.random.Generator) -> tuple[float, float]:
        self.twd += self.dir_sigma * np.sqrt(dt / 60.0) * rng.standard_normal()
        return self.tws, self.twd

    def state(self) -> dict:
        d = super().state()
        d["dir_sigma"] = self.dir_sigma
        return d

    def reset(self, tws: float | None = None, twd: float = 0.0):
        super().reset(tws, twd)
        if tws is not None:
            self._tws_base = tws


class MeanRevertingWind(WindModel):
    """Mean-reverting Brownian motion on both direction and speed.

    Direction: Ornstein-Uhlenbeck process around 0 (mean wind axis).
    Speed: Ornstein-Uhlenbeck around initial TWS.

    Parameters
    ----------
    tws : float
        Mean true wind speed (knots).
    twd : float
        Initial wind direction (degrees).
    dir_sigma : float
        Direction volatility (deg / sqrt(min)).
    dir_reversion : float
        Direction mean-reversion rate (1/min).  Default 0.05.
    tws_sigma : float
        Speed volatility (kts / sqrt(min)).  Default 0.0 (off).
    tws_reversion : float
        Speed mean-reversion rate (1/min).  Default 0.1.
    """

    def __init__(self, tws: float, twd: float = 0.0,
                 dir_sigma: float = 2.0, dir_reversion: float = 0.05,
                 tws_sigma: float = 0.0, tws_reversion: float = 0.1):
        super().__init__(tws, twd)
        self.dir_sigma = dir_sigma
        self.dir_reversion = dir_reversion
        self.tws_sigma = tws_sigma
        self.tws_reversion = tws_reversion
        self._tws_mean = tws
        self._twd_mean = twd

    def update(self, dt: float, rng: np.random.Generator) -> tuple[float, float]:
        dt_min = dt / 60.0

        # Direction: OU process
        self.twd += (
            self.dir_reversion * (self._twd_mean - self.twd) * dt_min
            + self.dir_sigma * np.sqrt(dt_min) * rng.standard_normal()
        )

        # Speed: OU process (only if tws_sigma > 0)
        if self.tws_sigma > 0:
            self.tws += (
                self.tws_reversion * (self._tws_mean - self.tws) * dt_min
                + self.tws_sigma * np.sqrt(dt_min) * rng.standard_normal()
            )
            self.tws = max(0.5, self.tws)  # floor at 0.5 kts

        return self.tws, self.twd

    def state(self) -> dict:
        d = super().state()
        d.update({
            "dir_sigma": self.dir_sigma,
            "dir_reversion": self.dir_reversion,
            "tws_sigma": self.tws_sigma,
            "tws_reversion": self.tws_reversion,
            "tws_mean": self._tws_mean,
        })
        return d

    def reset(self, tws: float | None = None, twd: float = 0.0):
        super().reset(tws, twd)
        if tws is not None:
            self._tws_mean = tws
        self._twd_mean = twd
