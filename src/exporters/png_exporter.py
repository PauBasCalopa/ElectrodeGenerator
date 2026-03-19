"""PNG export for matplotlib figures."""


def export_png(fig, path, dpi=150):
    """Save a matplotlib Figure to a PNG file.

    Args:
        fig: matplotlib Figure instance.
        path: Output file path.
        dpi: Resolution in dots per inch.
    """
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
