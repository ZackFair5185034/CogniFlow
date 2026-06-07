"""CogniFlow 数据集管理器模块 - 管理训练和评估数据集。"""

from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import json
import sqlite3
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class Sample:
    """数据集中的单个样本。"""
    id: str
    image_path: str
    annotation_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    split: str = "train"  # train, val, test


class DatasetManager:
    """管理训练和评估数据集。

    提供功能：
    - 样本存储和检索
    - 训练/验证/测试集划分管理
    - 元数据跟踪
    """

    def __init__(
        self,
        root_dir: Path,
        db_path: Optional[Path] = None,
    ):
        """初始化数据集管理器。

        Args:
            root_dir: 数据集存储根目录。
            db_path: SQLite 数据库路径 (None = 使用默认路径)。
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            db_path = self.root_dir / "dataset.db"

        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self) -> None:
        """初始化 SQLite 数据库。"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                id TEXT PRIMARY KEY,
                image_path TEXT NOT NULL,
                annotation_path TEXT,
                metadata TEXT,
                split TEXT DEFAULT 'train',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS splits (
                name TEXT PRIMARY KEY,
                sample_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_sample(
        self,
        sample_id: str,
        image_path: Path,
        annotation_path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
        split: str = "train",
    ) -> Sample:
        """添加样本到数据集。

        Args:
            sample_id: 唯一样本标识符。
            image_path: 图像文件路径。
            annotation_path: 标注文件路径。
            metadata: 附加元数据。
            split: 数据集划分。

        Returns:
            创建的 Sample 对象。
        """
        sample = Sample(
            id=sample_id,
            image_path=str(image_path),
            annotation_path=str(annotation_path) if annotation_path else None,
            metadata=metadata,
            split=split,
        )

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO samples (id, image_path, annotation_path, metadata, split)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sample.id, sample.image_path, sample.annotation_path,
             json.dumps(sample.metadata), sample.split)
        )

        conn.commit()
        conn.close()

        return sample

    def get_sample(self, sample_id: str) -> Optional[Sample]:
        """通过 ID 获取样本。

        Args:
            sample_id: 样本标识符。

        Returns:
            Sample 对象，如果未找到则返回 None。
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, image_path, annotation_path, metadata, split FROM samples WHERE id = ?",
            (sample_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return Sample(
            id=row[0],
            image_path=row[1],
            annotation_path=row[2],
            metadata=json.loads(row[3]) if row[3] else None,
            split=row[4],
        )

    def get_samples(self, split: Optional[str] = None) -> List[Sample]:
        """获取所有样本，可按划分过滤。

        Args:
            split: 按划分过滤 (None = 获取全部)。

        Returns:
            Sample 对象列表。
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if split:
            cursor.execute(
                "SELECT id, image_path, annotation_path, metadata, split FROM samples WHERE split = ?",
                (split,)
            )
        else:
            cursor.execute(
                "SELECT id, image_path, annotation_path, metadata, split FROM samples"
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            Sample(
                id=row[0],
                image_path=row[1],
                annotation_path=row[2],
                metadata=json.loads(row[3]) if row[3] else None,
                split=row[4],
            )
            for row in rows
        ]

    def split_dataset(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> Tuple[List[Sample], List[Sample], List[Sample]]:
        """将数据集划分为训练/验证/测试集。

        Args:
            train_ratio: 训练集比例。
            val_ratio: 验证集比例。
            test_ratio: 测试集比例。
            seed: 随机种子。

        Returns:
            (train_samples, val_samples, test_samples) 元组。
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6

        all_samples = self.get_samples()
        np.random.seed(seed)
        indices = np.random.permutation(len(all_samples))

        n_train = int(len(all_samples) * train_ratio)
        n_val = int(len(all_samples) * val_ratio)

        train_indices = indices[:n_train]
        val_indices = indices[n_train:n_train + n_val]
        test_indices = indices[n_train + n_val:]

        train_samples = [all_samples[i] for i in train_indices]
        val_samples = [all_samples[i] for i in val_indices]
        test_samples = [all_samples[i] for i in test_indices]

        # 更新数据库中的划分
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        for i in train_indices:
            cursor.execute("UPDATE samples SET split = ? WHERE id = ?", ("train", all_samples[i].id))
        for i in val_indices:
            cursor.execute("UPDATE samples SET split = ? WHERE id = ?", ("val", all_samples[i].id))
        for i in test_indices:
            cursor.execute("UPDATE samples SET split = ? WHERE id = ?", ("test", all_samples[i].id))

        conn.commit()
        conn.close()

        return train_samples, val_samples, test_samples

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据集统计信息。

        Returns:
            包含统计信息的字典。
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM samples")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT split, COUNT(*) FROM samples GROUP BY split")
        split_counts = dict(cursor.fetchall())

        conn.close()

        return {
            "total_samples": total,
            "split_counts": split_counts,
        }

    def export_annotations(self, output_path: Path, format: str = "coco") -> None:
        """以指定格式导出标注。

        Args:
            output_path: 输出文件路径。
            format: 导出格式 ('coco' 或 'yolo')。
        """
        samples = self.get_samples()

        if format == "coco":
            self._export_coco(samples, output_path)
        elif format == "yolo":
            self._export_yolo(samples, output_path)
        else:
            raise ValueError(f"未知格式: {format}")

    def _export_coco(self, samples: List[Sample], output_path: Path) -> None:
        """以 COCO 格式导出。"""
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": [],
        }

        for idx, sample in enumerate(samples):
            coco_data["images"].append({
                "id": idx,
                "file_name": Path(sample.image_path).name,
                "width": 224,
                "height": 224,
            })

            # 添加占位标注
            if sample.annotation_path:
                with open(sample.annotation_path, "r") as f:
                    ann_data = json.load(f)
                    for ann in ann_data:
                        ann["id"] = len(coco_data["annotations"])
                        ann["image_id"] = idx
                        coco_data["annotations"].append(ann)

        with open(output_path, "w") as f:
            json.dump(coco_data, f, indent=2)

    def _export_yolo(self, samples: List[Sample], output_path: Path) -> None:
        """以 YOLO 格式导出。"""
        output_path.mkdir(parents=True, exist_ok=True)

        for sample in samples:
            if sample.annotation_path:
                dest_path = output_path / f"{Path(sample.image_path).stem}.txt"
                # 复制标注文件
                import shutil
                shutil.copy(sample.annotation_path, dest_path)
