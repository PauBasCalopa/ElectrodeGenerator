"""CSV export for electrode profile curves."""

import csv


def export_csv(curves, path):
    """Write curve data to a CSV file.

    Args:
        curves: list of (x_coords, y_coords, label) tuples.
        path: Output file path.
    """
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["curve", "x", "y"])
        for cx, cy, label in curves:
            for xi, yi in zip(cx, cy):
                writer.writerow([label, f"{xi:.6f}", f"{yi:.6f}"])
