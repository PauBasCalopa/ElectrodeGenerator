import ezdxf
from ezdxf import colors
from typing import Dict, Any, List, Tuple
import os


class DXFExporter:
    """
    Exports Rogowski geometry to DXF format using ezdxf library.
    """
    
    def __init__(self):
        """Initialize DXF exporter."""
        self.doc = None
        self.msp = None
        
    def create_new_document(self, dxfversion: str = 'R2000') -> None:
        """
        Create a new DXF document.

        Args:
            dxfversion: DXF version to use (default: R2000 for max CAD compatibility)
        """
        self.doc = ezdxf.new(dxfversion=dxfversion)
        self.msp = self.doc.modelspace()
        
    def add_polyline(self, points: List[Tuple[float, float]],
                     layer_name: str = 'PROFILE',
                     color: int = colors.BLUE) -> None:
        """
        Add a polyline from a list of (x, y) points.

        Args:
            points: List of (x, y) coordinate tuples
            layer_name: Layer name for the curve
            color: Color index for the curve
        """
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
        """
        Add a spline curve through the given (x, y) fit points.

        Splines are preferred over polylines for smooth curves because
        CAD programs (e.g. SolidWorks) import them as editable spline
        entities rather than segmented line strips.

        Args:
            points: List of (x, y) coordinate tuples (fit points)
            layer_name: Layer name for the curve
            color: Color index for the curve
        """
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")

        if layer_name not in self.doc.layers:
            self.doc.layers.add(layer_name, color=color)

        fit_points = [(x, y, 0) for x, y in points]
        spline = self.msp.add_spline(fit_points)
        spline.dxf.layer = layer_name
        spline.dxf.color = color

    def add_rogowski_curve(self, geometry,
                          layer_name: str = 'ROGOWSKI', 
                          color: int = colors.BLUE) -> None:
        """
        Add a curve to the DXF document as a polyline.

        Args:
            geometry: Object with a to_polyline_points() method
            layer_name: Layer name for the curve
            color: Color index for the curve
        """
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")
        self.add_polyline(geometry.to_polyline_points(), layer_name, color)

    def add_bounding_box(self, geometry,
                        layer_name: str = 'BBOX',
                        color: int = colors.RED) -> None:
        """
        Add bounding box rectangle to the DXF document.

        Args:
            geometry: Object with a get_bounding_box() method
            layer_name: Layer name for the bounding box
            color: Color index for the bounding box
        """
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")
            
        # Create layer if it doesn't exist
        if layer_name not in self.doc.layers:
            self.doc.layers.add(layer_name, color=color)
        
        # Get bounding box
        bbox = geometry.get_bounding_box()
        
        # Create rectangle points
        rect_points = [
            (bbox['min_x'], bbox['min_y'], 0),
            (bbox['max_x'], bbox['min_y'], 0),
            (bbox['max_x'], bbox['max_y'], 0),
            (bbox['min_x'], bbox['max_y'], 0)
        ]
        
        # Create closed polyline for rectangle
        rectangle = self.msp.add_lwpolyline(rect_points)
        rectangle.close()  # Close the polyline
        rectangle.dxf.layer = layer_name
        rectangle.dxf.color = color
        
    def add_text_annotation(self, text: str, position: Tuple[float, float],
                           height: float = 0.5, layer_name: str = 'TEXT',
                           color: int = colors.YELLOW) -> None:
        """
        Add text annotation to the DXF document.
        
        Args:
            text: Text content
            position: (x, y) position for the text
            height: Text height
            layer_name: Layer name for the text
            color: Color index for the text
        """
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")
            
        # Create layer if it doesn't exist
        if layer_name not in self.doc.layers:
            self.doc.layers.add(layer_name, color=color)
            
        # Add text entity
        text_entity = self.msp.add_text(text)
        text_entity.dxf.insert = (position[0], position[1], 0)
        text_entity.dxf.height = height
        text_entity.dxf.layer = layer_name
        text_entity.dxf.color = color
        
    def save_to_file(self, filepath: str) -> None:
        """
        Save the DXF document to file.
        
        Args:
            filepath: Output file path
        """
        if self.doc is None:
            raise ValueError("Document not created. Call create_new_document() first.")
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Save document
        self.doc.saveas(filepath)
        print(f"DXF file saved to: {filepath}")
        
    def get_document_info(self) -> Dict[str, Any]:
        """
        Get information about the current document.
        
        Returns:
            Dictionary with document information
        """
        if self.doc is None:
            return {"error": "No document created"}
            
        return {
            "dxf_version": self.doc.dxfversion,
            "layer_count": len(self.doc.layers),
            "entity_count": len(list(self.msp)),
            "layers": [layer.dxf.name for layer in self.doc.layers]
        }