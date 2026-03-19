"""DXF export using the ezdxf library."""

import os
from typing import List, Tuple

import ezdxf
from ezdxf import colors


class DXFExporter:
    """Exports electrode geometry to DXF format."""

    def __init__(self):
        self.doc = None
        self.msp = None

    def create_new_document(self, dxfversion: str = 'R2000') -> None:
        """Create a new DXF document.

        Args:
            dxfversion: DXF version (default: R2000 for max CAD compatibility).
        """
        self.doc = ezdxf.new(dxfversion=dxfversion)
        self.msp = self.doc.modelspace()

    def add_polyline(self, points: List[Tuple[float, float]],
                     layer_name: str = 'PROFILE',
                     color: int = colors.BLUE) -> None:
        """Add a polyline from a list of (x, y) points."""
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")

        if layer_name not in self.doc.layers:
            self.doc.layers.add(layer_name, color=color)

        points_3d = [(x, y, 0) for x, y in points]
        if self.doc.dxfversion == 'AC1009':  # R12
            polyline = self.msp.add_polyline2d(points_3d)
        else:
            polyline = self.msp.add_lwpolyline(points_3d)
        polyline.dxf.layer = layer_name
        polyline.dxf.color = color

    def add_spline(self, points: List[Tuple[float, float]],
                   layer_name: str = 'PROFILE',
                   color: int = colors.BLUE) -> None:
        """Add a spline curve through the given (x, y) fit points."""
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")

        if layer_name not in self.doc.layers:
            self.doc.layers.add(layer_name, color=color)

        fit_points = [(x, y, 0) for x, y in points]
        spline = self.msp.add_spline(fit_points)
        spline.dxf.layer = layer_name
        spline.dxf.color = color

    def add_text_annotation(self, text: str, position: Tuple[float, float],
                            height: float = 0.5, layer_name: str = 'TEXT',
                            color: int = colors.YELLOW) -> None:
        """Add text annotation to the DXF document."""
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")

        if layer_name not in self.doc.layers:
            self.doc.layers.add(layer_name, color=color)

        text_entity = self.msp.add_text(text)
        text_entity.dxf.insert = (position[0], position[1], 0)
        text_entity.dxf.height = height
        text_entity.dxf.layer = layer_name
        text_entity.dxf.color = color

    def save_to_file(self, filepath: str) -> None:
        """Save the DXF document to file."""
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        self.doc.saveas(filepath)
