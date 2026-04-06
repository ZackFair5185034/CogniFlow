"""Bounding box annotation tool."""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@dataclass
class BoundingBox:
    """Bounding box annotation."""
    x1: int
    y1: int
    x2: int
    y2: int
    label: str
    label_id: int = 0
    difficulty: bool = False

    @property
    def area(self) -> int:
        """Compute box area."""
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[int, int]:
        """Compute box center."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def to_coco(self) -> List[float]:
        """Convert to COCO format [x, y, width, height]."""
        return [self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1]

    def to_yolo(self, img_width: int, img_height: int) -> List[float]:
        """Convert to YOLO format [class_id, x_center, y_center, width, height] (normalized)."""
        x_center = (self.x1 + self.x2) / 2 / img_width
        y_center = (self.y1 + self.y2) / 2 / img_height
        width = (self.x2 - self.x1) / img_width
        height = (self.y2 - self.y1) / img_height
        return [self.label_id, x_center, y_center, width, height]


class BoundingBoxAnnotator:
    """Interactive bounding box annotation tool.

    Supports:
    - Click and drag to create boxes
    - Multiple class labels
    - Box editing and deletion
    """

    def __init__(self, labels: List[str]):
        """Initialize annotator.

        Args:
            labels: List of class labels.
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV is required for annotation")

        self.labels = labels
        self.boxes: List[BoundingBox] = []

        # Drawing state
        self._drawing = False
        self._current_start: Optional[Tuple[int, int]] = None
        self._current_end: Optional[Tuple[int, int]] = None
        self._selected_box_idx: Optional[int] = None

        # Colors for different classes (BGR)
        self._colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]

    def add_box(self, box: BoundingBox) -> None:
        """Add a bounding box."""
        self.boxes.append(box)

    def remove_box(self, index: int) -> None:
        """Remove a bounding box by index."""
        if 0 <= index < len(self.boxes):
            self.boxes.pop(index)

    def get_box_at_point(self, x: int, y: int) -> Optional[int]:
        """Get box index at point, or None."""
        for i, box in enumerate(self.boxes):
            if box.x1 <= x <= box.x2 and box.y1 <= y <= box.y2:
                return i
        return None

    def draw_boxes(self, image: np.ndarray) -> np.ndarray:
        """Draw all boxes on image.

        Args:
            image: Input image (H, W, 3).

        Returns:
            Image with boxes drawn.
        """
        img = image.copy()

        for i, box in enumerate(self.boxes):
            color = self._colors[box.label_id % len(self._colors)]

            # Draw box
            cv2.rectangle(img, (box.x1, box.y1), (box.x2, box.y2), color, 2)

            # Draw label
            label_text = box.label
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1

            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
            cv2.rectangle(img, (box.x1, box.y1 - text_h - 4), (box.x1 + text_w, box.y1), color, -1)
            cv2.putText(img, label_text, (box.x1, box.y1 - 2), font, font_scale, (255, 255, 255), thickness)

            # Highlight selected box
            if i == self._selected_box_idx:
                cv2.rectangle(img, (box.x1 - 2, box.y1 - 2), (box.x2 + 2, box.y2 + 2), (0, 255, 0), 2)

        # Draw current box being created
        if self._drawing and self._current_start and self._current_end:
            cv2.rectangle(img, self._current_start, self._current_end, (128, 128, 128), 1)

        return img

    def on_mouse_event(
        self,
        event: int,
        x: int,
        y: int,
        flags: int,
    ) -> Optional[str]:
        """Handle mouse events for interactive annotation.

        Args:
            event: Mouse event type (cv2.EVENT_*).
            x: Mouse x position.
            y: Mouse y position.
            flags: Event flags.

        Returns:
            Event description or None.
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check if clicking on existing box
            box_idx = self.get_box_at_point(x, y)
            if box_idx is not None:
                self._selected_box_idx = box_idx
                return "box_selected"
            else:
                # Start drawing new box
                self._drawing = True
                self._current_start = (x, y)
                self._current_end = (x, y)
                self._selected_box_idx = None
                return "drawing_started"

        elif event == cv2.EVENT_MOUSEMOVE:
            if self._drawing:
                self._current_end = (x, y)
                return "drawing"

        elif event == cv2.EVENT_LBUTTONUP:
            if self._drawing:
                self._drawing = False
                if self._current_start and self._current_end:
                    x1 = min(self._current_start[0], self._current_end[0])
                    y1 = min(self._current_start[1], self._current_end[1])
                    x2 = max(self._current_start[0], self._current_end[0])
                    y2 = max(self._current_start[1], self._current_end[1])

                    if x2 - x1 > 5 and y2 - y1 > 5:  # Minimum size
                        box = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2, label="")
                        self.boxes.append(box)
                        self._selected_box_idx = len(self.boxes) - 1
                        return "box_created"

                self._current_start = None
                self._current_end = None
                return "drawing_cancelled"

        elif event == cv2.EVENT_RBUTTONDOWN:
            # Delete box at point
            box_idx = self.get_box_at_point(x, y)
            if box_idx is not None:
                self.remove_box(box_idx)
                self._selected_box_idx = None
                return "box_deleted"

        return None

    def export_coco(self, image_id: int) -> List[Dict[str, Any]]:
        """Export boxes in COCO format.

        Args:
            image_id: Image ID for COCO format.

        Returns:
            List of COCO annotations.
        """
        annotations = []
        for i, box in enumerate(self.boxes):
            x, y, w, h = box.to_coco()
            annotations.append({
                "id": i + 1,
                "image_id": image_id,
                "category_id": box.label_id,
                "bbox": [x, y, w, h],
                "area": box.area,
                "iscrowd": 0,
            })
        return annotations

    def export_yolo(self, img_width: int, img_height: int) -> List[str]:
        """Export boxes in YOLO format.

        Args:
            img_width: Image width.
            img_height: Image height.

        Returns:
            List of YOLO format strings.
        """
        lines = []
        for box in self.boxes:
            yolo_box = box.to_yolo(img_width, img_height)
            lines.append(" ".join(str(v) for v in yolo_box))
        return lines

    def clear(self) -> None:
        """Clear all boxes."""
        self.boxes.clear()
        self._selected_box_idx = None
        self._drawing = False
        self._current_start = None
        self._current_end = None
