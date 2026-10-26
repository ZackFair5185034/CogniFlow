# -*- coding: utf-8 -*-
"""模型类别 API 测试。

yolo_trigger / ObjectExistsCondition 的 class_names 是 multiselect 控件，
需要从用户所选模型的 metrics.categories 动态加载，而非硬编码 COCO 7 类。

此端点供前端在 model_id 变化时拉取真实类别填充下拉选项。
"""
import json
import pytest
import sys
sys.path.insert(0, '/home/coding/PRIVATE_WORKSPACE/CogniFlow')

from backend.database import Model, SessionLocal, init_db


@pytest.fixture
def db_with_model():
    """创建一个带 6 个真实类别的测试模型，测试后清理。"""
    init_db()
    db = SessionLocal()
    categories = [
        {"id": 0, "name": "猫"},
        {"id": 1, "name": "马里奥"},
        {"id": 2, "name": "蘑菇(敌)"},
        {"id": 3, "name": "金币数"},
        {"id": 4, "name": "问号"},
        {"id": 5, "name": "鸭子(敌人)"},
    ]
    metrics = json.dumps({
        "num_classes": 6,
        "categories": categories,
    })
    test_model = Model(
        name="test_dynamic_cats",
        file_path="/tmp/fake.pt",
        format="yolo_pt",
        metrics=metrics,
    )
    db.add(test_model)
    db.commit()
    db.refresh(test_model)
    yield db, test_model.id
    db.delete(test_model)
    db.commit()
    db.close()


class TestModelCategoriesAPI:
    """GET /api/models/{id}/categories 应返回模型的真实类别列表。"""

    def test_returns_categories_from_metrics(self, db_with_model):
        from fastapi.testclient import TestClient
        from app import app
        db, model_id = db_with_model
        client = TestClient(app)
        resp = client.get(f"/api/models/{model_id}/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert data == ["猫", "马里奥", "蘑菇(敌)", "金币数", "问号", "鸭子(敌人)"]

    def test_404_for_missing_model(self, db_with_model):
        from fastapi.testclient import TestClient
        from app import app
        client = TestClient(app)
        resp = client.get("/api/models/999999/categories")
        assert resp.status_code == 404

    def test_empty_list_when_metrics_is_null(self, db_with_model):
        """模型无 metrics 字段时返回空列表（前端降级为手动输入）。"""
        from fastapi.testclient import TestClient
        from app import app
        db, _ = db_with_model
        no_metrics_model = Model(
            name="test_no_metrics",
            file_path="/tmp/fake2.pt",
            format="yolo_pt",
            metrics=None,
        )
        db.add(no_metrics_model)
        db.commit()
        db.refresh(no_metrics_model)
        try:
            client = TestClient(app)
            resp = client.get(f"/api/models/{no_metrics_model.id}/categories")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            db.delete(no_metrics_model)
            db.commit()
            db.close()
