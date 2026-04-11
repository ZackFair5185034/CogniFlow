# -*- coding: utf-8 -*-
"""图集 API 测试。"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from app import app

# 测试数据库
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库。"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前后创建和清理数据库。"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """测试客户端。"""
    return TestClient(app)


def test_health_check(client):
    """测试健康检查端点。"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_atlas(client):
    """测试创建图集。"""
    response = client.post(
        "/api/atlas",
        json={"name": "测试图集", "description": "测试描述"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "测试图集"
    assert data["description"] == "测试描述"
    assert "id" in data


def test_list_atlases(client):
    """测试获取图集列表。"""
    # 创建两个图集
    client.post("/api/atlas", json={"name": "图集1"})
    client.post("/api/atlas", json={"name": "图集2"})

    response = client.get("/api/atlas")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_atlas(client):
    """测试获取单个图集。"""
    # 创建图集
    create_response = client.post("/api/atlas", json={"name": "测试图集"})
    atlas_id = create_response.json()["id"]

    # 获取图集
    response = client.get(f"/api/atlas/{atlas_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "测试图集"


def test_get_atlas_not_found(client):
    """测试获取不存在的图集。"""
    response = client.get("/api/atlas/9999")
    assert response.status_code == 404


def test_update_atlas(client):
    """测试更新图集。"""
    # 创建图集
    create_response = client.post("/api/atlas", json={"name": "旧名称"})
    atlas_id = create_response.json()["id"]

    # 更新图集
    response = client.put(f"/api/atlas/{atlas_id}", json={"name": "新名称"})
    assert response.status_code == 200
    assert response.json()["name"] == "新名称"


def test_delete_atlas(client):
    """测试删除图集。"""
    # 创建图集
    create_response = client.post("/api/atlas", json={"name": "待删除"})
    atlas_id = create_response.json()["id"]

    # 删除图集
    response = client.delete(f"/api/atlas/{atlas_id}")
    assert response.status_code == 204

    # 确认删除
    get_response = client.get(f"/api/atlas/{atlas_id}")
    assert get_response.status_code == 404
