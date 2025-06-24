"""
Document Visualization Service
Creates annotated document images with field extraction highlights
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Create dummy classes to avoid NameError
    class ImageDraw:
        class Draw:
            pass
    logging.warning("PIL/Pillow not available - document visualization disabled")


class VisualizationService:
    """Service for creating document visualizations with field highlights"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.font = None
        
        if PIL_AVAILABLE:
            try:
                # Try to load a system font, fallback to default
                self.font = ImageFont.truetype("arial.ttf", 15)
            except (IOError, OSError):
                try:
                    # Try alternative font paths
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/System/Library/Fonts/Arial.ttf",
                        "/Windows/Fonts/arial.ttf"
                    ]
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            self.font = ImageFont.truetype(font_path, 15)
                            break
                except (IOError, OSError):
                    pass
                
                if not self.font:
                    self.font = ImageFont.load_default()
    
    def is_available(self) -> bool:
        """Check if visualization services are available"""
        return PIL_AVAILABLE
    
    def create_field_visualization(
        self, 
        document_path: str, 
        analysis_results: Dict[str, Any], 
        output_path: str
    ) -> bool:
        """
        Create a visualization of the document with field extraction highlights
        
        Args:
            document_path: Path to original document image
            analysis_results: Analysis results containing field locations
            output_path: Path where visualization should be saved
            
        Returns:
            True if visualization was created successfully
        """
        if not self.is_available():
            self.logger.error("PIL not available - cannot create visualization")
            return False
        
        if not os.path.exists(document_path):
            self.logger.error(f"Document file not found: {document_path}")
            return False
        
        try:
            # Open and convert the image
            with Image.open(document_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create a copy to draw on
                viz_img = img.copy()
                draw = ImageDraw.Draw(viz_img)
                
                # Extract field locations from Azure results
                fields_highlighted = self._draw_azure_fields(draw, analysis_results, viz_img.size)
                
                # Add legend
                self._draw_legend(draw, viz_img.size, fields_highlighted)
                
                # Save the visualization
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                viz_img.save(output_path, "PNG", quality=95)
                
                self.logger.info(f"Visualization saved to: {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error creating visualization: {e}")
            return False
    
    def _draw_azure_fields(self, draw: ImageDraw.Draw, analysis_results: Dict[str, Any], image_size: Tuple[int, int]) -> int:
        """Draw field highlights from Azure analysis results"""
        fields_count = 0
        
        # Get Azure results
        azure_results = analysis_results.get('azure_results', {})
        if not azure_results:
            return fields_count
        
        documents = azure_results.get('documents', [])
        if not documents:
            return fields_count
        
        doc = documents[0]
        fields = doc.get('fields', {})
        
        # Colors for different types of fields
        colors = {
            'default': 'green',
            'amount': 'blue',
            'name': 'red',
            'date': 'purple',
            'tax': 'orange'
        }
        
        for field_name, field_data in fields.items():
            if not isinstance(field_data, dict):
                continue
            
            # Get bounding regions
            bounding_regions = field_data.get('boundingRegions', [])
            if not bounding_regions:
                continue
            
            # Determine field color based on name
            color = self._get_field_color(field_name, colors)
            
            for region in bounding_regions:
                polygon = region.get('polygon', [])
                if len(polygon) >= 8:  # Need at least 4 points (x,y pairs)
                    # Convert polygon to list of (x, y) tuples
                    points = []
                    for i in range(0, len(polygon), 2):
                        if i + 1 < len(polygon):
                            x = int(polygon[i] * image_size[0]) if polygon[i] <= 1 else int(polygon[i])
                            y = int(polygon[i + 1] * image_size[1]) if polygon[i + 1] <= 1 else int(polygon[i + 1])
                            points.append((x, y))
                    
                    if len(points) >= 2:
                        # Draw bounding box
                        self._draw_field_highlight(draw, points, color, field_name)
                        fields_count += 1
        
        return fields_count
    
    def _get_field_color(self, field_name: str, colors: Dict[str, str]) -> str:
        """Determine color for field based on its name"""
        field_lower = field_name.lower()
        
        if any(keyword in field_lower for keyword in ['amount', 'wage', 'tax', 'withh', 'tip', 'compensation']):
            return colors['amount']
        elif any(keyword in field_lower for keyword in ['name', 'employee', 'employer', 'payer', 'recipient']):
            return colors['name']
        elif any(keyword in field_lower for keyword in ['date', 'year']):
            return colors['date']
        elif any(keyword in field_lower for keyword in ['tax', 'ein', 'tin', 'ssn']):
            return colors['tax']
        else:
            return colors['default']
    
    def _draw_field_highlight(self, draw: ImageDraw.Draw, points: list, color: str, field_name: str):
        """Draw highlight for a single field"""
        if len(points) < 2:
            return
        
        # Find bounding rectangle
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        
        # Draw rectangle outline
        draw.rectangle([min_x, min_y, max_x, max_y], outline=color, width=2)
        
        # Draw checkmark at top-right corner
        check_x = max_x + 5
        check_y = min_y
        self._draw_checkmark(draw, check_x, check_y, color)
    
    def _draw_checkmark(self, draw: ImageDraw.Draw, x: int, y: int, color: str):
        """Draw a small checkmark at the specified position"""
        # Simple checkmark: two lines forming a check
        draw.line([(x, y + 3), (x + 3, y + 6)], fill=color, width=2)
        draw.line([(x + 3, y + 6), (x + 8, y - 1)], fill=color, width=2)
    
    def _draw_legend(self, draw: ImageDraw.Draw, image_size: Tuple[int, int], fields_count: int):
        """Draw a legend showing what was highlighted"""
        # Position legend in bottom-right corner
        legend_width = 200
        legend_height = 60
        legend_x = image_size[0] - legend_width - 10
        legend_y = image_size[1] - legend_height - 10
        
        # Draw background
        draw.rectangle(
            [legend_x, legend_y, legend_x + legend_width, legend_y + legend_height],
            fill='white',
            outline='black',
            width=1
        )
        
        # Draw title
        title_text = f"Fields Highlighted: {fields_count}"
        if self.font:
            draw.text((legend_x + 5, legend_y + 5), title_text, fill='black', font=self.font)
        else:
            draw.text((legend_x + 5, legend_y + 5), title_text, fill='black')
        
        # Draw color indicators
        colors = [
            ('green', 'General'),
            ('blue', 'Amounts'),
            ('red', 'Names'),
            ('purple', 'Dates')
        ]
        
        y_offset = 25
        for i, (color, label) in enumerate(colors):
            if i >= 2:  # Only show first 2 colors to fit in legend
                break
            
            # Draw color square
            square_size = 8
            square_x = legend_x + 5
            square_y = legend_y + y_offset + (i * 15)
            draw.rectangle(
                [square_x, square_y, square_x + square_size, square_y + square_size],
                fill=color,
                outline='black'
            )
            
            # Draw label
            label_x = square_x + square_size + 5
            if self.font:
                draw.text((label_x, square_y - 2), label, fill='black', font=self.font)
            else:
                draw.text((label_x, square_y - 2), label, fill='black')