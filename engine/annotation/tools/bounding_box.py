"""CogniFlow 边界框标注工具模块。"""

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
    """边界框标注。"""
    x1: int
    y1: int
    x2: int
    y2: int
    label: str
    label_id: int = 0
    difficulty: bool = False

    @property
    def area(self) -> int:
        """计算框面积。"""
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[int, int]:
        """计算框中心点。"""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def to_coco(self) -> List[float]:
        """转换为 COCO 格式 [x, y, width, height]。"""
        return [self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1]

    def to_yolo(self, img_width: int, img_height: int) -> List[float]:
        """转换为 YOLO 格式 [class_id, x_center, y_center, width, height]（归一化）。"""
        x_center = (self.x1 + self.x2) / 2 / img_width
        y_center = (self.y1 + self.y2) / 2 / img_height
        width = (self.x2 - self.x1) / img_width
        height = (self.y2 - self.y1) / img_height
        return [self.label_id, x_center, y_center, width, height]


class BoundingBoxAnnotator:
    """交互式边界框标注工具。

    支持功能：
    - 点击拖拽创建框
    - 多类别标签
    - 框的编辑和删除
    """

    def __init__(self, labels: List[str]):
        """初始化标注器。

        Args:
            labels: 类别标签列表。
        """
        if not CV2_AVAILABLE:
            raise ImportError("标注需要安装 OpenCV")

        self.labels = labels
        self.boxes: List[BoundingBox] = []

        # 绘图状态
        self._drawing = False
        self._current_start: Optional[Tuple[int, int]] = None
        self._current_end: Optional[Tuple[int, int]] = None
        self._selected_box_idx: Optional[int] = None

        # 不同类别的颜色 (BGR)
        self._colors = [
            (255, 0, 0),    # 红色
            (0, 255, 0),    # 绿色
            (0, 0, 255),    # 蓝色
            (255, 255, 0),  # 青色
            (255, 0, 255),  # 洋红色
            (0, 255, 255),  # 黄色
        ]

    def add_box(self, box: BoundingBox) -> None:
        """添加边界框。"""
        self.boxes.append(box)

    def remove_box(self, index: int) -> None:
        """根据索引移除边界框。"""
        if 0 <= index < len(self.boxes):
            self.boxes.pop(index)

    def get_box_at_point(self, x: int, y: int) -> Optional[int]:
        """获取指定点处的框索引。"""
        for i, box in enumerate(self.boxes):
            if box.x1 <= x <= box.x2 and box.y1 <= y <= box.y2:
                return i
        return None

    def draw_boxes(self, image: np.ndarray) -> np.ndarray:
        """在图像上绘制所有框。

        Args:
            image: 输入图像 (H, W, 3)。

        Returns:
            绘制了框的图像。
        """
        img = image.copy()

        for i, box in enumerate(self.boxes):
            color = self._colors[box.label_id % len(self._colors)]

            # 绘制框
            cv2.rectangle(img, (box.x1, box.y1), (box.x2, box.y2), color, 2)

            # 绘制标签
            label_text = box.label
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1

            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
            cv2.rectangle(img, (box.x1, box.y1 - text_h - 4), (box.x1 + text_w, box.y1), color, -1)
            cv2.putText(img, label_text, (box.x1, box.y1 - 2), font, font_scale, (255, 255, 255), thickness)

            # 高亮选中的框
            if i == self._selected_box_idx:
                cv2.rectangle(img, (box.x1 - 2, box.y1 - 2), (box.x2 + 2, box.y2 + 2), (0, 255, 0), 2)

        # 绘制正在创建的框
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
        """处理交互式标注的鼠标事件。

        Args:
            event: 鼠标事件类型 (cv2.EVENT_*)。
            x: 鼠标 x 坐标。
            y: 鼠标 y 坐标。
            flags: 事件标志。

        Returns:
            事件描述或 None。
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            # 检查是否点击了现有框
            box_idx = self.get_box_at_point(x, y)
            if box_idx is not None:
                self._selected_box_idx = box_idx
                return "box_selected"
            else:
                # 开始绘制新框
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

                    if x2 - x1 > 5 and y2 - y1 > 5:  # 最小尺寸
                        box = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2, label="")
                        self.boxes.append(box)
                        self._selected_box_idx = len(self.boxes) - 1
                        return "box_created"

                self._current_start = None
                self._current_end = None
                return "drawing_cancelled"

        elif event == cv2.EVENT_RBUTTONDOWN:
            # 删除点击处的框
            box_idx = self.get_box_at_point(x, y)
            if box_idx is not None:
                self.remove_box(box_idx)
                self._selected_box_idx = None
                return "box_deleted"

        return None

    def export_coco(self, image_id: int) -> List[Dict[str, Any]]:
        """以 COCO 格式导出框。

        Args:
            image_id: COCO 格式的图片 ID。

        Returns:
            COCO 格式标注列表。
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
        """以 YOLO 格式导出框。

        Args:
            img_width: 图像宽度。
            img_height: 图像高度。

        Returns:
            YOLO 格式字符串列表。
        """
        lines = []
        for box in self.boxes:
            yolo_box = box.to_yolo(img_width, img_height)
            lines.append(" ".join(str(v) for v in yolo_box))
        return lines

    def clear(self) -> None:
        """清除所有框。"""
        self.boxes.clear()
        self._selected_box_idx = None
        self._drawing = False
        self._current_start = None
        self._current_end = None
