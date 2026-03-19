"""
Electrode profile generators.

Each profile implements the same interface so the GUI and CLI
can work with any profile without knowing its equations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List
import numpy as np


class ProfileBase(ABC):
    """Abstract base class for electrode profiles."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for the GUI dropdown."""

    @property
    @abstractmethod
    def equations(self) -> str:
        """Human-readable equations for the Help dialog."""

    @property
    @abstractmethod
    def parameters(self) -> List[Dict[str, Any]]:
        """
        Parameter definitions for the GUI.

        Each entry is a dict with keys:
            name, label, default, min, max, step, type
        """

    @abstractmethod
    def generate_points(self, config: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate profile points from the given config.

        Returns:
            (x_points, y_points) arrays
        """

    def get_bounding_box(self, config: Dict[str, Any]) -> Dict[str, float]:
        """Calculate bounding box of the generated geometry."""
        x, y = self.generate_points(config)
        return {
            'min_x': float(np.min(x)),
            'max_x': float(np.max(x)),
            'min_y': float(np.min(y)),
            'max_y': float(np.max(y)),
        }

    def to_polyline_points(self, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Convert generated points to a list of (x, y) tuples."""
        x, y = self.generate_points(config)
        return list(zip(x.tolist(), y.tolist()))


# ---------------------------------------------------------------------------
# Rogowski
# ---------------------------------------------------------------------------
class RogowskiProfile(ProfileBase):
    """
    X = (s/pi) * (u + 1 + e^u * cos(v))
    Y = (s/pi) * (v + e^u * sin(v))
    v = pi/2
    """

    @property
    def name(self) -> str:
        return "Rogowski"

    @property
    def equations(self) -> str:
        return (
            "X = (s/\u03c0) \u00b7 (u + 1 + e\u1d58 \u00b7 cos(v))\n"
            "Y = (s/\u03c0) \u00b7 (v + e\u1d58 \u00b7 sin(v))\n"
            "v = \u03c0/2 (constant)\n\n"
            "s = electrode gap (scales the profile)\n"
            "u = variable parameter\n\n"
            "As u \u2192 \u2212\u221e, Y \u2192 s/2\n"
            "The natural gap between two mirrored\n"
            "Rogowski curves is exactly s."
        )

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {'name': 'u_start',    'label': 'u start',                'default': -3.0, 'min': -6.0, 'max': 0.0, 'step': 0.1, 'type': float},
            {'name': 'u_end',      'label': 'u end',                  'default': 2.5,  'min': 0.1,  'max': 5.0, 'step': 0.1, 'type': float},
            {'name': 'num_points', 'label': 'Points',                 'default': 200,  'min': 20,   'max': 500, 'step': 10,  'type': int},
        ]

    def generate_points(self, config: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        s = config.get('s', 1.0)  # fed from assembly gap slider
        u_start = config.get('u_start', -3.0)
        u_end = config.get('u_end', 2.5)
        num_points = int(config.get('num_points', 200))
        v = np.pi / 2

        u = np.linspace(u_start, u_end, num_points)
        x = (s / np.pi) * (u + 1 + np.exp(u) * np.cos(v))
        y = (s / np.pi) * (v + np.exp(u) * np.sin(v))
        return x, y


# ---------------------------------------------------------------------------
# Chang
# ---------------------------------------------------------------------------
class ChangProfile(ProfileBase):
    """
    X = u + cos(v) * sinh(u)
    Y = v + k * sin(v) * cosh(u)
    v = pi/2,  u in [0, u_max],  k > 0 (compactness)
    """

    @property
    def name(self) -> str:
        return "Chang"

    @property
    def equations(self) -> str:
        return (
            "X = u + cos(v) \u00b7 sinh(u)\n"
            "Y = v + k \u00b7 sin(v) \u00b7 cosh(u)\n"
            "v = \u03c0/2 (constant)\n\n"
            "k > 0 controls profile compactness\n"
            "u \u2208 [0, u_max]  (u_max depends on electrode width)"
        )

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {'name': 'k',          'label': 'k (compactness)',         'default': 0.85, 'min': 0.01, 'max': 2.0, 'step': 0.01, 'type': float},
            {'name': 'u_end',      'label': 'u max (electrode width)', 'default': 2.0,  'min': 0.1,  'max': 5.0, 'step': 0.1,  'type': float},
            {'name': 'num_points', 'label': 'Points',                  'default': 200,  'min': 20,   'max': 500, 'step': 10,   'type': int},
        ]

    def generate_points(self, config: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        k = config.get('k', 0.85)
        u_end = config.get('u_end', 2.0)
        num_points = int(config.get('num_points', 200))
        v = np.pi / 2

        u = np.linspace(0.0, u_end, num_points)
        x = u + np.cos(v) * np.sinh(u)
        y = v + k * np.sin(v) * np.cosh(u)
        return x, y


# ---------------------------------------------------------------------------
# Ernst
# ---------------------------------------------------------------------------
class ErnstProfile(ProfileBase):
    """
    X = u + k0*cos(v)*sinh(u) + k1*cos(2v)*sinh(2u)
    Y = v + k0*sin(v)*cosh(u) + k1*sin(2v)*cosh(2u)
    v = pi/2,  u in [0, u_max],  k1 = k0^2 / 8

    Edge-effect relationships:
        k0 = 1.72 * e^(-h)          — k0 as function of profile width h
        h  = 3.5 * s                — profile width for edge-free design (s < 3)
        k0 = 1.72 * e^(-3.5 * s)   — combined: optimal k0 from electrode distance
    Edge effect becomes considerable at s ≈ 3.
    """

    @property
    def name(self) -> str:
        return "Ernst"

    @property
    def equations(self) -> str:
        return (
            "X = u + k\u2080\u00b7cos(v)\u00b7sinh(u) + k\u2081\u00b7cos(2v)\u00b7sinh(2u)\n"
            "Y = v + k\u2080\u00b7sin(v)\u00b7cosh(u) + k\u2081\u00b7sin(2v)\u00b7cosh(2u)\n"
            "v = \u03c0/2 (constant)\n"
            "k\u2081 = k\u2080\u00b2 / 8  (auto-calculated)\n\n"
            "Auto k\u2080 (no edge effect):\n"
            "  k\u2080 = 1.72 \u00b7 e\u207b\u00b3\u00b7\u2075\u02e2\n"
            "  h  = 3.5 \u00b7 s  (profile width)\n"
            "  Valid for s < 3 (edge effect appears at s \u2248 3)\n"
            "  Uses assembly gap as s"
        )

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {'name': 'k0',         'label': 'k\u2080 (shape constant)', 'default': 0.3,   'min': 0.001, 'max': 1.72, 'step': 0.01, 'type': float},
            {'name': 'u_end',      'label': 'u max (electrode width)',  'default': 3.0,   'min': 0.1,  'max': 10.0, 'step': 0.1,  'type': float},
            {'name': 'num_points', 'label': 'Points',                   'default': 200,   'min': 20,   'max': 500,  'step': 10,   'type': int},
        ]

    def generate_points(self, config: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        k0 = config.get('k0', 0.3)
        k1 = k0 ** 2 / 8.0
        u_end = config.get('u_end', 3.0)
        num_points = int(config.get('num_points', 200))
        v = np.pi / 2

        u = np.linspace(0.0, u_end, num_points)
        x = u + k0 * np.cos(v) * np.sinh(u) + k1 * np.cos(2 * v) * np.sinh(2 * u)
        y = v + k0 * np.sin(v) * np.cosh(u) + k1 * np.sin(2 * v) * np.cosh(2 * u)
        return x, y

    @staticmethod
    def optimal_k0(s: float) -> float:
        """k0 that eliminates edge effect for a given electrode distance s (valid for s < 3)."""
        return 1.72 * np.exp(-3.5 * s)

    @staticmethod
    def profile_width(s: float) -> float:
        """Profile width h for edge-free design: h = 3.5 * s."""
        return 3.5 * s

    @staticmethod
    def k0_from_width(h: float) -> float:
        """k0 as function of profile width: k0 = 1.72 * e^(-h)."""
        return 1.72 * np.exp(-h)


# ---------------------------------------------------------------------------
# Registry — the GUI and CLI read from this dict
# ---------------------------------------------------------------------------
PROFILES: Dict[str, ProfileBase] = {
    "Rogowski": RogowskiProfile(),
    "Chang": ChangProfile(),
    "Ernst": ErnstProfile(),
}
