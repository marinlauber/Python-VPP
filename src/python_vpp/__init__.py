"""Python-VPP: a 3-DOF velocity prediction program based on the ORC models."""

from importlib.metadata import PackageNotFoundError, version

from .SailMod import Jib, Kite, Main
from .VPPMod import VPP
from .YachtMod import Bulb, Keel, Rudder, ShortKeel, Yacht

try:
    __version__ = version("python-vpp")
except PackageNotFoundError:  # running from a source checkout
    __version__ = "unknown"

__all__ = ["VPP", "Yacht", "Keel", "ShortKeel", "Rudder", "Bulb", "Main", "Jib", "Kite"]
