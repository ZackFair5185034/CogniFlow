"""VisionGame 标注工具 GUI - 图形界面版边界框标注工具。

使用方法:
    python -m visiongame.annotation.tools.label_tool

快捷键:
    1-9        选择类别
    s          保存标注
    o          打开图片
    c          清除当前标注
    z          撤销上一个框
    q          退出
    space      下一张图
    left       上一张图
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Tuple
import argparse

import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("错误: 需要安装 OpenCV。运行: pip install opencv-python")
    sys.exit(1)

# 中文字体支持
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: 未安装 PIL，中文可能显示为方框。请运行: pip install pillow")


# 全局字体设置
def get_font(size: int = 20):
    """获取中文字体。"""
    if not PIL_AVAILABLE:
        return None
    # 尝试系统字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class LabelTool:
    """图像标注工具主类。"""

    def __init__(
        self,
        labels: List[str],
        output_dir: str = "./annotations",
        output_format: str = "coco",
    ):
        """初始化标注工具。

        Args:
            labels: 类别标签列表。
            output_dir: 标注输出目录。
            output_format: 输出格式 ('coco' 或 'yolo')。
        """
        self.labels = labels
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_format = output_format

        # UI 布局参数
        self.info_bar_height = 50
        self.help_panel_width = 180

        # 标注状态
        self.current_image_path: Optional[Path] = None
        self.current_image: Optional[np.ndarray] = None
        self.image_files: List[Path] = []
        self.current_index: int = 0

        # 边界框
        self.boxes: List[dict] = []
        self.current_class_id: int = 0

        # 绘制状态
        self.drawing: bool = False
        self.start_point: Optional[Tuple[int, int]] = None
        self.current_point: Optional[Tuple[int, int]] = None
        self.selected_box_idx: Optional[int] = None

        # 显示缩放参数（用于坐标转换）
        self.display_scale: float = 1.0
        self.display_offset_x: int = 0
        self.display_offset_y: int = 0

        # 颜色映射 (BGR)
        self.colors = [
            (255, 0, 0),      # 红色
            (0, 255, 0),      # 绿色
            (0, 0, 255),      # 蓝色
            (255, 255, 0),    # 青色
            (255, 0, 255),    # 洋红色
            (0, 255, 255),    # 黄色
            (128, 0, 0),      # 深红色
            (0, 128, 0),     # 深绿色
            (0, 0, 128),     # 深蓝色
        ]

        # 窗口名称
        self.window_name = "VisionGame Annotation Tool"
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        # 字体
        self.font = get_font(16)
        self.font_small = get_font(14)

    def _draw_chinese(self, img: np.ndarray, text: str, pos: Tuple[int, int],
                      font_size: int = 16, color: Tuple[int, int, int] = (255, 255, 255)):
        """在图像上绘制中文。

        Args:
            img: 目标图像 (numpy array)。
            text: 文本内容。
            pos: 位置 (x, y)。
            font_size: 字体大小。
            color: 颜色 (B, G, R)。
        """
        if not PIL_AVAILABLE:
            # 回退到英文（只取前几个字符）
            cv2.putText(img, text[:10], pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            return

        # 转换 numpy array 到 PIL Image
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        # 获取字体
        font = get_font(font_size)

        # 绘制文本
        draw.text(pos, text, font=font, fill=(color[2], color[1], color[0]))

        # 转换回 numpy array
        result = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        # 更新原图像（需要复制回去）
        img[:] = result

    def _mouse_callback(self, event: int, x: int, y: int, flags: int, param):
        """鼠标事件回调。"""
        # 坐标转换：显示坐标 -> 实际图像坐标
        # 显示坐标需要减去UI偏移量，再除以缩放比例
        mouse_x = int((x - self.display_offset_x) / self.display_scale)
        mouse_y = int((y - self.display_offset_y) / self.display_scale)

        # 检查鼠标是否在图像区域内
        if self.current_image is not None:
            h, w = self.current_image.shape[:2]
            if not (0 <= mouse_x < w and 0 <= mouse_y < h):
                return

        if event == cv2.EVENT_LBUTTONDOWN:
            # 检查是否点击了现有框
            clicked_idx = self._get_box_at_point(mouse_x, mouse_y)
            if clicked_idx is not None:
                self.selected_box_idx = clicked_idx
                self.drawing = False
            else:
                # 开始绘制新框
                self.drawing = True
                self.start_point = (mouse_x, mouse_y)
                self.current_point = (mouse_x, mouse_y)
                self.selected_box_idx = None

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.current_point = (mouse_x, mouse_y)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing and self.start_point:
                x1 = min(self.start_point[0], mouse_x)
                y1 = min(self.start_point[1], mouse_y)
                x2 = max(self.start_point[0], mouse_x)
                y2 = max(self.start_point[1], mouse_y)

                # 最小尺寸检查
                if x2 - x1 > 5 and y2 - y1 > 5:
                    self.boxes.append({
                        "x1": int(x1),
                        "y1": int(y1),
                        "x2": int(x2),
                        "y2": int(y2),
                        "class_id": self.current_class_id,
                        "class_name": self.labels[self.current_class_id] if self.labels else "",
                    })
                    self.selected_box_idx = len(self.boxes) - 1

                self.drawing = False
                self.start_point = None
                self.current_point = None

        elif event == cv2.EVENT_RBUTTONDOWN:
            # 右键删除框
            clicked_idx = self._get_box_at_point(mouse_x, mouse_y)
            if clicked_idx is not None:
                self.boxes.pop(clicked_idx)
                self.selected_box_idx = None

    def _get_box_at_point(self, x: int, y: int) -> Optional[int]:
        """获取指定点处的框索引。"""
        for i, box in enumerate(self.boxes):
            if box["x1"] <= x <= box["x2"] and box["y1"] <= y <= box["y2"]:
                return i
        return None

    def load_folder(self, folder_path: str):
        """加载图片文件夹。

        Args:
            folder_path: 文件夹路径。
        """
        folder = Path(folder_path)
        if not folder.exists():
            print(f"文件夹不存在: {folder}")
            return

        # 支持的图片格式
        extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
        self.image_files = sorted([
            f for f in folder.iterdir()
            if f.suffix.lower() in extensions
        ])

        if not self.image_files:
            print(f"文件夹中没有找到图片: {folder}")
            return

        self.current_index = 0
        self.load_image(self.image_files[0])
        print(f"已加载 {len(self.image_files)} 张图片")

    def load_image(self, image_path: Path):
        """加载单张图片。

        Args:
            image_path: 图片路径。
        """
        self.current_image_path = image_path
        self.current_image = cv2.imread(str(image_path))
        if self.current_image is None:
            print(f"无法读取图片: {image_path}")
            return

        # 尝试加载对应的标注文件
        self.boxes = self._load_annotation(image_path)
        print(f"已加载图片: {image_path.name}, 标注数: {len(self.boxes)}")

    def _load_annotation(self, image_path: Path) -> List[dict]:
        """加载标注文件。"""
        annotation_path = self.output_dir / f"{image_path.stem}.json"
        if annotation_path.exists():
            try:
                with open(annotation_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("boxes", [])
            except Exception as e:
                print(f"加载标注失败: {e}")
        return []

    def save_annotation(self):
        """保存当前标注。"""
        if self.current_image_path is None:
            print("没有加载图片")
            return

        annotation_path = self.output_dir / f"{self.current_image_path.stem}.json"
        data = {
            "image_path": str(self.current_image_path),
            "image_shape": self.current_image.shape,
            "boxes": self.boxes,
            "format": self.output_format,
        }

        try:
            with open(annotation_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"已保存: {annotation_path}")
        except Exception as e:
            print(f"保存失败: {e}")

    def undo_last_box(self):
        """撤销上一个框。"""
        if self.boxes:
            self.boxes.pop()
            self.selected_box_idx = None
            print("已撤销上一个框")

    def clear_boxes(self):
        """清除所有框。"""
        self.boxes.clear()
        self.selected_box_idx = None
        print("已清除所有标注")

    def next_image(self):
        """加载下一张图片。"""
        if not self.image_files:
            print("没有加载图片文件夹")
            return

        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image(self.image_files[self.current_index])
        else:
            print("已是最后一张图片")

    def prev_image(self):
        """加载上一张图片。"""
        if not self.image_files:
            print("没有加载图片文件夹")
            return

        if self.current_index > 0:
            self.current_index -= 1
            self.load_image(self.image_files[self.current_index])
        else:
            print("已是第一张图片")

    def set_class(self, class_id: int):
        """设置当前类别。

        Args:
            class_id: 类别 ID (0-8)。
        """
        if 0 <= class_id < len(self.labels):
            self.current_class_id = class_id
            print(f"已选择类别: {self.labels[class_id]}")

    def _draw_frame(self) -> np.ndarray:
        """绘制当前帧。

        Returns:
            绘制后的图像。
        """
        if self.current_image is None:
            # 创建空白图像
            frame = np.zeros((600, 800, 3), dtype=np.uint8)
            cv2.putText(frame, "Press 'o' to open image folder", (200, 300),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return frame

        frame = self.current_image.copy()
        h, w = frame.shape[:2]

        # 绘制所有框（在图像区域）
        for i, box in enumerate(self.boxes):
            color = self.colors[box["class_id"] % len(self.colors)]
            x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]

            # 绘制矩形
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 绘制标签背景
            label = box.get("class_name", self.labels[box["class_id"]] if self.labels else "")
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - text_h - 6), (x1 + text_w, y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 高亮选中框
            if i == self.selected_box_idx:
                cv2.rectangle(frame, (x1 - 3, y1 - 3), (x2 + 3, y2 + 3), (0, 255, 0), 2)

        # 绘制正在创建的框
        if self.drawing and self.start_point and self.current_point:
            cv2.rectangle(frame, self.start_point, self.current_point, (128, 128, 128), 1)

        # 绘制顶部信息栏
        info_bar = np.zeros((self.info_bar_height, w, 3), dtype=np.uint8)
        info_text = f"{self.current_image_path.name if self.current_image_path else 'None'} | "
        info_text += f"Boxes: {len(self.boxes)} | "
        info_text += f"Class: {self.labels[self.current_class_id] if self.labels else 'None'} | "
        info_text += f"{self.current_index + 1}/{len(self.image_files)}"
        cv2.putText(info_bar, info_text, (10, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # 绘制类别指示器
        for i, label in enumerate(self.labels[:9]):
            color = self.colors[i]
            cv2.rectangle(info_bar, (620 + i * 35, 10), (645 + i * 35, 40), color, -1)
            cv2.putText(info_bar, str(i + 1), (625 + i * 35, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 合并
        frame = np.vstack([info_bar, frame])

        # 绘制左侧帮助信息面板
        help_lines = [
            "=== HOTKEYS ===",
            "1-9: Select class",
            "s: Save",
            "o: Open folder",
            "c: Clear",
            "z: Undo",
            "Space: Next",
            "Left: Previous",
            "q: Quit",
            "",
            f"Current: {self.labels[self.current_class_id] if self.labels else 'None'}",
        ]

        help_panel = np.zeros((frame.shape[0], self.help_panel_width, 3), dtype=np.uint8)
        for i, line in enumerate(help_lines):
            y_pos = 30 + i * 22
            if y_pos < frame.shape[0]:
                cv2.putText(help_panel, line, (10, y_pos),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        frame = np.hstack([help_panel, frame])

        return frame

    def run(self):
        """运行主循环。"""
        print("=" * 50)
        print("VisionGame Annotation Tool")
        print("=" * 50)
        print("Press 'o' to open image folder")
        print("Press 'q' to quit")
        print("=" * 50)

        while True:
            frame = self._draw_frame()

            # 限制窗口大小
            max_width = 1400
            max_height = 900
            h, w = frame.shape[:2]
            scale = 1.0
            if w > max_width or h > max_height:
                scale = min(max_width / w, max_height / h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))

            # 更新显示参数（用于坐标转换）
            # 缩放后的偏移量 = 原偏移量 * 缩放比例
            self.display_scale = scale
            self.display_offset_x = self.help_panel_width * scale
            self.display_offset_y = self.info_bar_height * scale

            cv2.imshow(self.window_name, frame)

            # 检查窗口是否被关闭（点击了X按钮）
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                print("Window closed")
                break

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q') or key == 27:  # q 或 ESC 退出
                print("Exit annotation tool")
                break
            elif key == ord('o'):
                # 打开文件夹
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()
                folder = filedialog.askdirectory(title="Select Image Folder")
                root.destroy()

                if folder:
                    self.load_folder(folder)
            elif key == ord('s'):
                self.save_annotation()
            elif key == ord('c'):
                self.clear_boxes()
            elif key == ord('z'):
                self.undo_last_box()
            elif key == ord(' '):  # space
                self.next_image()
            elif key in [ord(str(i)) for i in range(1, 10)]:
                # 数字键 1-9 选择类别
                class_id = key - ord('1')
                if class_id < len(self.labels):
                    self.set_class(class_id)
            elif key == 83 or key == 2555904:  # 右箭头
                self.next_image()
            elif key == 81 or key == 2424832:  # 左箭头
                self.prev_image()

        cv2.destroyAllWindows()


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="VisionGame Annotation Tool")
    parser.add_argument(
        "--labels",
        nargs="+",
        default=["player", "enemy", "item", "npc", "ui"],
        help="Class labels",
    )
    parser.add_argument(
        "--output-dir",
        default="./annotations",
        help="Output directory",
    )
    parser.add_argument(
        "--format",
        choices=["coco", "yolo"],
        default="coco",
        help="Output format",
    )
    args = parser.parse_args()

    tool = LabelTool(
        labels=args.labels,
        output_dir=args.output_dir,
        output_format=args.format,
    )
    tool.run()


if __name__ == "__main__":
    main()
