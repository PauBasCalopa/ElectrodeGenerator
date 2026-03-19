"""
Electrode assembly geometry construction.

Pure geometry functions — no UI or I/O dependencies.
"""


def build_assembly_curves(x, y, gap, plate_length, is_axi=False):
    """Build electrode assembly curves from profile points.

    Args:
        x, y: Profile point coordinates (numpy arrays or sequences).
        gap: Distance between electrodes.
        plate_length: Length of the flat plate section.
        is_axi: If True, build axisymmetric geometry (no left-side curves).

    Returns:
        List of (x_coords, y_coords, label) tuples using plain Python lists.
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

    return curves
