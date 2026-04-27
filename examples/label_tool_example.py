"""标注工具测试示例 - 方便从 PyCharm 直接运行。

使用方法:
    1. 在 PyCharm 中右键点击此文件
    2. 选择 "Run 'label_tool_example'"
    3. 或在终端中运行: python examples/label_tool_example.py
"""

import os
import sys

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.annotation.tools import LabelTool


def main():
    """运行标注工具示例。"""
    # 创建标注工具实例
    tool = LabelTool(
        labels=["player", "enemy", "item", "npc", "ui"],
        output_dir="./test_annotations",
        output_format="coco",
    )

    # 打印快捷键说明
    print("=" * 50)
    print("CogniFlow 标注工具")
    print("=" * 50)
    print("快捷键:")
    print("  1-9    选择类别")
    print("  o      打开图片文件夹")
    print("  s      保存标注")
    print("  c      清除当前标注")
    print("  z      撤销上一个框")
    print("  space  下一张图")
    print("  左箭头  上一张图")
    print("  q/ESC  退出")
    print("=" * 50)

    # 运行工具
    tool.run()


if __name__ == "__main__":
    main()
