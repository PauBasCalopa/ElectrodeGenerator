"""
Shared contour-building utilities for FEMM electrode simulations.

Used by both the Lua exporter and the live pyfemm simulator so
that the measuring contour is constructed identically in both paths.
"""

import math


def build_top_contour(curves, offset=1e-3):
    """Build an ordered measuring contour along the top electrode.

    Args:
        curves: list of (x_coords, y_coords, label) tuples that
                define the electrode geometry.
        offset: perpendicular distance to shift the contour into
                the dielectric gap (right-hand normal of the travel
                direction).  For the top electrode traversed
                left-to-right this moves the line downward, away
                from the boundary discontinuity.  Set to 0 to stay
                on the electrode surface.

    Returns:
        List of (x, y) tuples defining the measuring contour.
    """
    parts = {}
    for cx, cy, label in curves:
        if "Top" in label:
            parts[label] = list(zip(cx, cy))

    contour = []
    if "Top-Left" in parts:
        contour.extend(reversed(parts["Top-Left"]))
    if "Top Plate" in parts:
        contour.extend(parts["Top Plate"])
    if "Top-Right" in parts:
        contour.extend(parts["Top-Right"])

    # Drop the first and last vertex – they sit at the electrode
    # tips where the geometry creates an artificial singularity.
    if len(contour) > 2:
        contour = contour[1:-1]

    if not offset or len(contour) < 2:
        return contour

    # Deduplicate consecutive identical points
    pts = [contour[0]]
    for p in contour[1:]:
        if abs(p[0] - pts[-1][0]) > 1e-12 or abs(p[1] - pts[-1][1]) > 1e-12:
            pts.append(p)
    if len(pts) < 2:
        return contour

    # Right-hand unit normal for each segment
    seg_normals = []
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        seg_len = math.hypot(dx, dy)
        if seg_len > 1e-12:
            seg_normals.append((dy / seg_len, -dx / seg_len))
        else:
            seg_normals.append((0.0, 0.0))

    # Offset each vertex along the (averaged) normal
    offset_pts = []
    for i in range(len(pts)):
        if i == 0:
            nx, ny = seg_normals[0]
        elif i == len(pts) - 1:
            nx, ny = seg_normals[-1]
        else:
            nx = (seg_normals[i - 1][0] + seg_normals[i][0]) / 2
            ny = (seg_normals[i - 1][1] + seg_normals[i][1]) / 2
            n_len = math.hypot(nx, ny)
            if n_len > 1e-12:
                nx /= n_len
                ny /= n_len
        offset_pts.append((pts[i][0] + offset * nx,
                           pts[i][1] + offset * ny))

    return offset_pts
