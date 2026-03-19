"""
FEMM 4.2 Python integration for direct electrostatic simulation.

Uses pyfemm to drive FEMM directly from Python, enabling automated
simulation runs and parameter optimization.  Model building is
delegated to ``FEMMModelBuilder`` with the ``ComBackend``.
"""

import math
import os
import shutil
import tempfile

try:
    import femm
    HAS_FEMM = True
except ImportError:
    HAS_FEMM = False


class FEMMSimulator:
    """Controls FEMM 4.2 directly via pyfemm for electrostatic simulations."""

    def __init__(self):
        if not HAS_FEMM:
            raise RuntimeError(
                "pyfemm is not installed.\n"
                "Install with:  pip install pyfemm\n"
                "FEMM 4.2 must also be installed on this system.")
        self._is_open = False
        self._temp_dir = tempfile.mkdtemp(prefix="femm_opt_")

    def open(self, hide=True):
        """Launch FEMM."""
        femm.openfemm(1 if hide else 0)
        self._is_open = True

    def close(self):
        """Close FEMM and clean up."""
        if self._is_open:
            try:
                femm.closefemm()
            except Exception:
                pass
            self._is_open = False
        if os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass

    def build_and_solve(self, curves, config):
        """Build electrode model and run the solver."""
        from simulation.femm_model import ComBackend, FEMMModelBuilder

        backend = ComBackend()
        builder = FEMMModelBuilder(backend)
        builder.build(curves, config)

        fee = os.path.join(self._temp_dir, "model.fee")
        femm.ei_saveas(fee)
        femm.ei_analyze(1)
        femm.ei_loadsolution()

    def get_field_along_contour(self, contour_points, num_samples=500):
        """Sample |E| along a contour. Returns (distance[], |E|[]).

        Interpolates *num_samples* evenly-spaced points along the
        polyline defined by *contour_points* and queries the solved
        field at each one via ``eo_getpointvalues``.
        """
        # Deduplicate consecutive identical points
        pts = [contour_points[0]]
        for p in contour_points[1:]:
            if abs(p[0] - pts[-1][0]) > 1e-10 or abs(p[1] - pts[-1][1]) > 1e-10:
                pts.append(p)
        if len(pts) < 2:
            return [], []

        # Cumulative arc length along the polyline
        cum = [0.0]
        for i in range(1, len(pts)):
            dx = pts[i][0] - pts[i - 1][0]
            dy = pts[i][1] - pts[i - 1][1]
            cum.append(cum[-1] + math.hypot(dx, dy))
        total = cum[-1]
        if total < 1e-10:
            return [], []

        distances = []
        e_vals = []
        seg = 0
        for i in range(num_samples):
            d = total * i / (num_samples - 1)

            # Advance to the segment that contains distance d
            while seg < len(cum) - 2 and cum[seg + 1] < d:
                seg += 1

            # Interpolate within the segment
            seg_len = cum[seg + 1] - cum[seg]
            t = 0.0 if seg_len < 1e-10 else (d - cum[seg]) / seg_len
            x = pts[seg][0] + t * (pts[seg + 1][0] - pts[seg][0])
            y = pts[seg][1] + t * (pts[seg + 1][1] - pts[seg][1])

            vals = femm.eo_getpointvalues(x, y)
            if vals and len(vals) >= 5:
                e_mag = math.hypot(vals[3], vals[4])
            else:
                e_mag = 0.0

            distances.append(d)
            e_vals.append(e_mag)

        return distances, e_vals

    def select_contour(self, contour_points):
        """Select a contour in the post-processor for interactive plotting."""
        femm.eo_clearcontour()
        prev = None
        for x, y in contour_points:
            if prev and abs(x - prev[0]) < 1e-10 and abs(y - prev[1]) < 1e-10:
                continue
            femm.eo_addcontour(x, y)
            prev = (x, y)

    def show_field_plot(self):
        """Display |E| along the selected contour in FEMM's plot window."""
        femm.eo_makeplot(4, 500)

    def get_field_at_point(self, x, y):
        """Return (V, Dx, Dy, Ex, Ey, ex, ey, nrg) at a point."""
        return femm.eo_getpointvalues(x, y)
