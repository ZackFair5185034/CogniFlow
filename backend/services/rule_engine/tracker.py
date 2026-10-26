# -*- coding: utf-8 -*-
"""SORT 目标跟踪器 - 轻量级多目标跟踪。

基于 Simple Online and Realtime Tracking (SORT) 算法：
1. 卡尔曼滤波预测每个目标的新位置
2. IoU 贪心关联匹配检测结果与已有轨迹
3. 未匹配的检测创建新轨迹，丢失过久的轨迹删除

仅依赖 numpy（通过 torch 间接安装）。
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore


class KalmanBoxTracker:
    """卡尔曼滤波器 - 单个目标的运动状态估计。

    状态向量: [cx, cy, s, r, d_cx, d_cy, d_s]
    - cx, cy: 中心坐标
    - s: 面积 (w * h)
    - r: 宽高比 (w / h)
    - d_cx, d_cy, d_s: 速度分量

    观测向量: [cx, cy, s, r]
    """

    _next_id = 0

    def __init__(self, bbox: list[float]):
        """初始化跟踪器。

        Args:
            bbox: [x1, y1, x2, y2] 格式的检测框
        """
        KalmanBoxTracker._next_id += 1
        self.track_id = KalmanBoxTracker._next_id
        self.hit_count = 1          # 匹配次数
        self.no_loss_count = 0      # 连续未匹配帧数
        self.age = 0                # 总存活帧数

        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0
        s = w * h
        r = w / h if h > 0 else 1.0

        # 状态向量 [cx, cy, s, r, d_cx, d_cy, d_s]
        self.x = np.array([[cx], [cy], [s], [r], [0], [0], [0]], dtype=np.float64)

        # 状态协方差矩阵
        self.P = np.eye(7, dtype=np.float64) * 10.0
        self.P[4:, 4:] *= 1000.0  # 速度分量初始不确定性更大

        # 状态转移矩阵
        dt = 1.0
        self.F = np.eye(7, dtype=np.float64)
        self.F[0, 4] = dt
        self.F[1, 5] = dt
        self.F[2, 6] = dt

        # 观测矩阵 (我们只观测 cx, cy, s, r)
        self.H = np.zeros((4, 7), dtype=np.float64)
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        self.H[2, 2] = 1.0
        self.H[3, 3] = 1.0

        # 测量噪声协方差
        self.R = np.eye(4, dtype=np.float64) * 1.0
        self.R[2:, 2:] *= 10.0  # 面积测量噪声更大

        # 过程噪声协方差
        self.Q = np.eye(7, dtype=np.float64)
        self.Q[4:, 4:] *= 0.01

    def predict(self):
        """预测下一帧的位置。返回预测框 [x1, y1, x2, y2]。"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.age += 1
        self.no_loss_count += 1
        return self.get_bbox()

    def update(self, bbox: list[float]):
        """用检测结果更新状态。

        Args:
            bbox: [x1, y1, x2, y2] 格式的检测框
        """
        self.no_loss_count = 0
        self.hit_count += 1

        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0
        s = w * h
        r = w / h if h > 0 else 1.0

        z = np.array([[cx], [cy], [s], [r]], dtype=np.float64)

        # 卡尔曼增益
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # 状态更新
        y = z - self.H @ self.x
        self.x = self.x + K @ y
        self.P = (np.eye(7, dtype=np.float64) - K @ self.H) @ self.P

    def get_bbox(self) -> list[float]:
        """获取当前状态下的检测框 [x1, y1, x2, y2]。"""
        # 索引 [i, 0] 因为状态是列向量 shape(7,1)
        cx, cy, s, r = float(self.x[0, 0]), float(self.x[1, 0]), float(self.x[2, 0]), float(self.x[3, 0])
        w = np.sqrt(s * r)
        h = s / w if w > 0 else 0
        return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def compute_iou(bbox1: list[float], bbox2: list[float]) -> float:
    """计算两个检测框的 IoU。"""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0

    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0.0


class SortTracker:
    """SORT 多目标跟踪器。

    使用示例:
        tracker = SortTracker(max_age=30, min_hits=3, iou_threshold=0.3)
        tracked = tracker.update(detections)
    """

    def __init__(self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3):
        """初始化跟踪器。

        Args:
            max_age: 目标最大丢失帧数
            min_hits: 目标最少命中次数才输出
            iou_threshold: IoU 关联阈值
        """
        if np is None:
            raise RuntimeError("SORT 跟踪器需要 numpy，请安装: pip install numpy")

        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: list[KalmanBoxTracker] = []
        self.frame_count = 0

    def update(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """更新跟踪状态。

        Args:
            detections: 检测结果列表，每项包含 'bbox': [x1,y1,x2,y2], 'confidence': float

        Returns:
            带 track_id 的跟踪结果列表
        """
        self.frame_count += 1

        # Step 1: 预测所有已有轨迹的新位置
        for trk in self.trackers:
            trk.predict()

        # Step 2: 关联检测与轨迹（贪心 IoU 匹配）
        matched, unmatched_dets, unmatched_trks = self._associate(detections)

        # Step 3: 更新已匹配的轨迹
        for trk_idx, det_idx in matched:
            self.trackers[trk_idx].update(detections[det_idx].get("bbox", [0, 0, 0, 0]))

        # Step 4: 创建新轨迹（未匹配的检测）
        for det_idx in unmatched_dets:
            trk = KalmanBoxTracker(detections[det_idx].get("bbox", [0, 0, 0, 0]))
            self.trackers.append(trk)

        # Step 5: 删除丢失过久的轨迹
        self.trackers = [t for t in self.trackers if t.no_loss_count <= self.max_age]

        # Step 6: 输出当前活跃轨迹
        results = []
        for trk in self.trackers:
            # 只输出满足最小命中次数的轨迹
            if trk.hit_count < self.min_hits and self.frame_count <= self.min_hits:
                continue
            bbox = trk.get_bbox()
            results.append({
                "track_id": trk.track_id,
                "bbox": bbox,
                "age": trk.age,
                "hit_count": trk.hit_count,
            })

        return results

    def _associate(
        self, detections: list[dict[str, Any]]
    ) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        """贪心 IoU 关联检测与轨迹。

        Returns:
            (matched_pairs, unmatched_detections, unmatched_trackers)
        """
        if not self.trackers or not detections:
            return [], list(range(len(detections))), list(range(len(self.trackers)))

        # 计算 IoU 矩阵 (trackers x detections)
        iou_matrix = np.zeros((len(self.trackers), len(detections)), dtype=np.float64)
        for t, trk in enumerate(self.trackers):
            pred_bbox = trk.get_bbox()
            for d, det in enumerate(detections):
                det_bbox = det.get("bbox", [0, 0, 0, 0])
                iou_matrix[t, d] = compute_iou(pred_bbox, det_bbox)

        # 贪心匹配：从最高 IoU 开始
        matched = []
        unmatched_trks = list(range(len(self.trackers)))
        unmatched_dets = list(range(len(detections)))

        # 按 IoU 降序排列所有候选对
        candidates = []
        for t, d in zip(*np.where(iou_matrix >= self.iou_threshold)):
            candidates.append((iou_matrix[t, d], t, d))
        candidates.sort(reverse=True, key=lambda x: x[0])

        # 贪心分配
        for _, t, d in candidates:
            if t in unmatched_trks and d in unmatched_dets:
                matched.append((t, d))
                unmatched_trks.remove(t)
                unmatched_dets.remove(d)

        return matched, unmatched_dets, unmatched_trks

    def reset(self):
        """重置跟踪器状态。"""
        self.trackers.clear()
        self.frame_count = 0
