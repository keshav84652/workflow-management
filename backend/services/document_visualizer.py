"""
Document Visualizer Service
Creates annotated visualizations of extracted fields on document images.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import os
import copy

from ..utils.config import settings

# Set up logging
logger = logging.getLogger(__name__)


class DocumentVisualizer:
    """Utility for visualizing extracted fields on document images"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the document visualizer
        
        Args:
            config: Configuration options for visualization
        """
        self.default_config = {
            'annotation_color': (0, 0, 255),  # Red in BGR
            'annotation_thickness': 2,
            'box_alpha': 0.3,
            'font_scale': 0.6,
            'font_thickness': 1,
            'output_suffix': '_annotated',
            'visualization_type': 'box',  # 'box' or 'tick'
            'tick_size': 15,
            'tick_position_offset': 8,
            'show_label': True,
            'show_tick_with_box': True
        }
        
        self.config = self.default_config.copy()
        if config:
            self.config.update(config)
            
        # Try to import OpenCV
        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
        except ImportError:
            self.cv2 = None
            self.np = None
            logger.warning("OpenCV (cv2) or NumPy is not installed. Visualization features will not work.")
    
    def _draw_bounding_box(self, image, polygon_coords, label=None):
        """Draw a bounding box with optional label on the image"""
        if not self.cv2 or not self.np:
            return image
            
        try:
            # Convert coordinates to a numpy array of points
            points = self.np.array(
                [(int(polygon_coords[i]), int(polygon_coords[i+1])) 
                 for i in range(0, len(polygon_coords), 2)], 
                self.np.int32
            )
            points = points.reshape((-1, 1, 2))
            
            # Get image dimensions
            img_h, img_w = image.shape[:2]
            
            # Create a mask for the polygon
            mask = self.np.zeros((img_h, img_w), dtype=self.np.uint8)
            self.cv2.fillPoly(mask, [points], 255)
            
            # Create a semi-transparent overlay
            overlay = image.copy()
            color = self.config['annotation_color']
            
            # Fill the polygon with semi-transparent color
            colored_mask = self.np.zeros_like(image)
            colored_mask[mask > 0] = color
            self.cv2.addWeighted(colored_mask, self.config['box_alpha'], overlay, 1, 0, overlay)
            
            # Draw the outline
            self.cv2.polylines(overlay, [points], True, color, 
                              self.config['annotation_thickness'], self.cv2.LINE_AA)
            
            # Add label if provided and show_label is True
            if label and self.config.get('show_label', True):
                # Find top-left point of polygon for label placement
                min_x = min(p[0][0] for p in points)
                min_y = min(p[0][1] for p in points)
                
                # Draw label background
                text_size = self.cv2.getTextSize(
                    label, self.cv2.FONT_HERSHEY_SIMPLEX, 
                    self.config['font_scale'], self.config['font_thickness']
                )[0]
                
                self.cv2.rectangle(
                    overlay, 
                    (min_x, min_y - text_size[1] - 5), 
                    (min_x + text_size[0], min_y), 
                    color, -1
                )
                
                # Draw label text
                self.cv2.putText(
                    overlay, label, (min_x, min_y - 5), 
                    self.cv2.FONT_HERSHEY_SIMPLEX, self.config['font_scale'], 
                    (255, 255, 255), self.config['font_thickness'], self.cv2.LINE_AA
                )
                
            return overlay
            
        except Exception as e:
            logger.error(f"Error drawing bounding box: {e}")
            return image
            
    def _draw_tick_mark(self, image, polygon_coords, field_name=None):
        """Draw a tick mark next to a field"""
        if not self.cv2 or not self.np:
            logger.warning("OpenCV or NumPy not available, skipping tick mark drawing.")
            return image

        try:
            points = self.np.array(
                [(int(polygon_coords[i]), int(polygon_coords[i+1]))
                 for i in range(0, len(polygon_coords), 2)],
                self.np.int32
            ).reshape((-1, 1, 2))  # Ensure it's a column of points

            if points.size == 0:
                logger.warning(f"Polygon coordinates are empty for field '{field_name}'. Cannot draw tick mark.")
                return image

            # Calculate the bounding box of the polygon
            rect_x, rect_y, rect_w, rect_h = self.cv2.boundingRect(points)

            # Determine the y-center for the tick mark
            anchor_y = rect_y + rect_h // 2  # Mid-point of the bounding rectangle's height

            # --- VERTICAL ADJUSTMENT FOR TICK MARK ---
            # Adjust this value (negative to move up, positive to move down)
            vertical_shift_adjustment = -int(rect_h * 0.10)  # Example: Shift up by 10% of field height
            # Or a fixed pixel shift: vertical_shift_adjustment = -4
            # --- END ADJUSTMENT ---

            tick_y_center = anchor_y + vertical_shift_adjustment

            # Determine initial x-position for the tick mark (right of the field)
            tick_x_start_base = rect_x + rect_w + self.config.get('tick_position_offset', 8)

            tick_size = self.config.get('tick_size', 15)
            color = self.config.get('annotation_color', (0, 0, 255))
            thickness = self.config.get('annotation_thickness', 2)

            # Define the tick mark points based on the adjusted tick_y_center
            # Shape: a simple check mark
            p1 = (int(tick_x_start_base), int(tick_y_center + tick_size // 3))
            p2 = (int(tick_x_start_base + tick_size // 3), int(tick_y_center + tick_size // 2 + tick_size // 3))  # Vertex lower
            p3 = (int(tick_x_start_base + tick_size), int(tick_y_center - tick_size // 2))  # End of longer leg higher

            # Clip points to ensure they are strictly within image dimensions
            img_h, img_w = image.shape[:2]
            def clip_point_to_image(pt_x, pt_y):
                return (max(0, min(pt_x, img_w - 1)), max(0, min(pt_y, img_h - 1)))

            p1_c = clip_point_to_image(p1[0], p1[1])
            p2_c = clip_point_to_image(p2[0], p2[1])
            p3_c = clip_point_to_image(p3[0], p3[1])

            result_image = image  # Assuming image is already a writable copy

            if p1_c != p2_c:  # Avoid drawing a dot if points collapse
                self.cv2.line(result_image, p1_c, p2_c, color, thickness, self.cv2.LINE_AA)
            if p2_c != p3_c:  # Avoid drawing a dot if points collapse
                self.cv2.line(result_image, p2_c, p3_c, color, thickness, self.cv2.LINE_AA)

            return result_image

        except Exception as e:
            logger.error(f"Error drawing tick mark for field '{field_name}' (polygon: {polygon_coords}): {e}")
            return image

    def _draw_field_annotation(self, image, field_data, field_name):
        """Draw annotation for a field on the image"""
        if not self.cv2 or not isinstance(field_data, dict):
            return image
            
        bounding_regions = field_data.get('boundingRegions')
        if not bounding_regions or not isinstance(bounding_regions, list):
            return image
            
        result_image = image 
        
        for region in bounding_regions:
            if not isinstance(region, dict) or 'polygon' not in region:
                continue
                
            polygon_coords = region.get('polygon')
            # Azure polygons typically have 8 coords (4 points). Min 6 for a triangle.
            if not polygon_coords or not isinstance(polygon_coords, list) or len(polygon_coords) < 6:
                continue
                
            if self.config.get('visualization_type') == 'box':
                result_image = self._draw_bounding_box(result_image, polygon_coords, field_name if self.config.get('show_label') else None)
                if self.config.get('show_tick_with_box', True):
                    result_image = self._draw_tick_mark(result_image, polygon_coords, field_name)
            elif self.config.get('visualization_type') == 'tick':
                result_image = self._draw_tick_mark(result_image, polygon_coords, field_name)
            
        return result_image
    
    def _traverse_and_annotate(self, image, fields_dict, parent_path=""):
        """Recursively traverse fields and annotate them on the image"""
        if not self.cv2 or not isinstance(fields_dict, dict):
            return image
            
        result_image = image.copy()
        
        for field_name, field_data in fields_dict.items():
            if not isinstance(field_data, dict):
                continue
                
            full_path = f"{parent_path}.{field_name}" if parent_path else field_name
            
            # Annotate this field if it has bounding regions
            if 'boundingRegions' in field_data:
                result_image = self._draw_field_annotation(result_image, field_data, full_path)
                
            # Recurse into valueObject
            if field_data.get('type') == 'object' and 'valueObject' in field_data and field_data['valueObject']:
                result_image = self._traverse_and_annotate(
                    result_image, field_data['valueObject'], full_path
                )
                
            # Recurse into valueArray items
            elif field_data.get('type') == 'array' and 'valueArray' in field_data and field_data['valueArray']:
                for idx, item in enumerate(field_data['valueArray']):
                    if not isinstance(item, dict):
                        continue
                        
                    # Annotate the array item itself if it has bounding regions
                    if 'boundingRegions' in item:
                        item_label = f"{full_path}[{idx}]"
                        result_image = self._draw_field_annotation(result_image, item, item_label)
                        
                    # Recurse into object items in the array
                    if item.get('type') == 'object' and 'valueObject' in item and item['valueObject']:
                        array_path = f"{full_path}[{idx}]"
                        result_image = self._traverse_and_annotate(
                            result_image, item['valueObject'], array_path
                        )
                        
        return result_image
    
    def create_visualization(self, image_path: str, api_result: Dict[str, Any], 
                           doc_index: int = 0, output_path: Optional[str] = None) -> Optional[str]:
        """
        Create a visualization of the extracted fields on the original document image
        
        Args:
            image_path: Path to the original document image
            api_result: Raw API result dictionary with field data
            doc_index: Index of the document to visualize (for multi-document results)
            output_path: Path to save the annotated image (None for auto-generated path)
            
        Returns:
            Path to the saved annotated image, or None if failed
        """
        if not self.cv2:
            logger.error("OpenCV (cv2) is not installed. Cannot perform visualization.")
            return None
            
        try:
            # Read the image
            image = self.cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image from {image_path}")
                return None
                
            # Get the document to visualize
            documents = []
            if "documents" in api_result and isinstance(api_result["documents"], list):
                documents = api_result["documents"]
            elif "analyzeResult" in api_result and isinstance(api_result["analyzeResult"], dict):
                if "documents" in api_result["analyzeResult"] and isinstance(api_result["analyzeResult"]["documents"], list):
                    documents = api_result["analyzeResult"]["documents"]
                    
            if not documents or doc_index >= len(documents):
                logger.error(f"Document index {doc_index} is out of range or no documents found")
                return None
                
            document = documents[doc_index]
            if not isinstance(document, dict) or "fields" not in document or not isinstance(document["fields"], dict):
                logger.error(f"Invalid document structure at index {doc_index}")
                return None
                
            # Annotate fields
            annotated_image = self._traverse_and_annotate(image, document["fields"])
            
            # Determine output path
            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}{self.config['output_suffix']}{ext}"
                
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Save the annotated image
            self.cv2.imwrite(output_path, annotated_image)
            logger.info(f"Annotated image saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return None

    def create_visualization_from_processed_document(self, image_path: str, processed_document, 
                                                   output_path: Optional[str] = None) -> Optional[str]:
        """
        Create visualization from a ProcessedDocument object
        
        Args:
            image_path: Path to the original document image
            processed_document: ProcessedDocument with Azure results
            output_path: Path to save the annotated image (None for auto-generated path)
            
        Returns:
            Path to the saved annotated image, or None if failed
        """
        if not processed_document.azure_result:
            logger.error("No Azure result available for visualization")
            return None
            
        # Use the raw Azure response for visualization
        return self.create_visualization(
            image_path, 
            processed_document.azure_result.raw_response, 
            0, 
            output_path
        )
