"""
Electrode assembly geometry construction.

Pure geometry functions — no UI or I/O dependencies.
"""

import math


def build_assembly_curves(x, y, gap, plate_length, is_axi=False):
    """Build electrode assembly curves from profile points.

    Returns list of (x_coords, y_coords, label) tuples.
    """
    x0, y0 = float(x[0]), float(y[0])
    xn = [float(v) - x0 for v in x]
    yn = [float(v) - y0 for v in y]
    d = plate_length
    has_plate = d > 1e-10

    curves = []

    # Top electrode
    curves.append(([xi + d / 2 for xi in xn],
                   [yi + gap / 2 for yi in yn], "Top-Right"))
    if is_axi:
        if has_plate:
            curves.append(([0, d / 2], [gap / 2, gap / 2], "Top Plate"))
    else:
        curves.append(([-xi - d / 2 for xi in xn],
                       [yi + gap / 2 for yi in yn], "Top-Left"))
        if has_plate:
            curves.append(([-d / 2, d / 2], [gap / 2, gap / 2], "Top Plate"))

    # Bottom electrode
    curves.append(([xi + d / 2 for xi in xn],
                   [-yi - gap / 2 for yi in yn], "Bot-Right"))
    if is_axi:
        if has_plate:
            curves.append(([0, d / 2], [-gap / 2, -gap / 2], "Bot Plate"))
    else:
        curves.append(([-xi - d / 2 for xi in xn],
                       [-yi - gap / 2 for yi in yn], "Bot-Left"))
        if has_plate:
            curves.append(([-d / 2, d / 2], [-gap / 2, -gap / 2], "Bot Plate"))

    # Closing caps
    _add_caps(curves, xn, yn, gap, d, is_axi)

    return curves


# ------------------------------------------------------------------
# Arc helpers
# ------------------------------------------------------------------

def _arc_points(cx, cy, R, theta_start, theta_end, top, num_pts=30):
    """Generate polyline for a circular arc, sweeping away from y = 0."""
    sweep_ccw = (theta_end - theta_start) % (2 * math.pi)
    sweep_cw = -((theta_start - theta_end) % (2 * math.pi))

    mid_y_ccw = cy + R * math.sin(theta_start + sweep_ccw / 2)
    mid_y_cw = cy + R * math.sin(theta_start + sweep_cw / 2)

    if top:
        sweep = sweep_ccw if mid_y_ccw > mid_y_cw else sweep_cw
    else:
        sweep = sweep_ccw if mid_y_ccw < mid_y_cw else sweep_cw

    xs, ys = [], []
    for i in range(num_pts + 1):
        a = theta_start + sweep * i / num_pts
        xs.append(cx + R * math.cos(a))
        ys.append(cy + R * math.sin(a))
    return xs, ys


def _cap_planar(p_right, p_left, tangent, top, num_pts=30):
    """Arc from p_right to p_left, tangent to the profile at p_right."""
    xr, yr = p_right
    xl, yl = p_left
    tx, ty = tangent
    tl = math.hypot(tx, ty)
    if tl < 1e-12:
        return [xr, xl], [yr, yl]
    tx, ty = tx / tl, ty / tl

    det = tx * (yl - yr) - ty * (xl - xr)
    if abs(det) < 1e-12:
        return [xr, xl], [yr, yl]

    b1 = tx * xr + ty * yr
    b2 = (xl ** 2 - xr ** 2 + yl ** 2 - yr ** 2) / 2
    cx = (b1 * (yl - yr) - b2 * ty) / det
    cy = (tx * b2 - (xl - xr) * b1) / det
    R = math.hypot(xr - cx, yr - cy)

    t0 = math.atan2(yr - cy, xr - cx)
    t1 = math.atan2(yl - cy, xl - cx)
    return _arc_points(cx, cy, R, t0, t1, top, num_pts)


def _cap_axi(p_start, tangent, top, num_pts=30):
    """Arc from p_start to the axis (r = 0).

    Tangent to the profile at start, perpendicular to the axis at end
    (centre on the axis).
    """
    xr, yr = p_start
    tx, ty = tangent
    tl = math.hypot(tx, ty)
    if tl < 1e-12:
        return [xr, 0.0], [yr, yr]
    tx, ty = tx / tl, ty / tl

    if abs(ty) < 1e-12:
        return [xr, 0.0], [yr, yr]

    yc = yr + xr * tx / ty
    R = math.hypot(xr, yc - yr)

    ye = (yc + R) if (top == ((yc + R) > (yc - R))) else (yc - R)

    t0 = math.atan2(yr - yc, xr)
    t1 = math.atan2(ye - yc, 0.0)
    return _arc_points(0, yc, R, t0, t1, top, num_pts)


def _add_caps(curves, xn, yn, gap, d, is_axi):
    """Add one closing cap per electrode."""
    if len(xn) < 2:
        return

    tx = xn[-1] - xn[-2]
    ty = yn[-1] - yn[-2]
    tip_x = xn[-1] + d / 2
    tip_y = yn[-1] + gap / 2

    if is_axi:
        xs, ys = _cap_axi((tip_x, tip_y), (tx, ty), top=True)
        curves.append((xs, ys, "Top-Cap"))
        xs, ys = _cap_axi((tip_x, -tip_y), (tx, -ty), top=False)
        curves.append((xs, ys, "Bot-Cap"))
    else:
        left_x = -xn[-1] - d / 2
        xs, ys = _cap_planar((tip_x, tip_y), (left_x, tip_y),
                             (tx, ty), top=True)
        curves.append((xs, ys, "Top-Cap"))
        xs, ys = _cap_planar((tip_x, -tip_y), (left_x, -tip_y),
                             (tx, -ty), top=False)
        curves.append((xs, ys, "Bot-Cap"))
