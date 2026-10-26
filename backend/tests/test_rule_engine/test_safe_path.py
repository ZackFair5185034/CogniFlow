# -*- coding: utf-8 -*-
"""安全路径拼接测试 - 阻断路径穿越。"""
import os
import tempfile

import pytest

from backend.utils.safe_path import safe_join


class TestSafeJoin:
    """safe_join 的越界防护。"""

    def test_normal_path_is_allowed(self):
        """正常路径原样返回。"""
        base = tempfile.gettempdir()
        result = safe_join(base, "images", "a.png")
        assert os.path.normpath(result).startswith(os.path.normpath(base))

    def test_parent_traversal_is_rejected(self):
        """.. 穿越必须被拒绝。"""
        base = tempfile.gettempdir()
        with pytest.raises(ValueError) as excinfo:
            safe_join(base, "..", "..", "etc", "passwd")
        assert "越界" in str(excinfo.value)

    def test_absolute_path_is_rejected(self):
        """绝对路径注入必须被拒绝。"""
        base = tempfile.gettempdir()
        with pytest.raises(ValueError):
            safe_join(base, os.path.abspath(os.sep))

    def test_windows_drive_letter_is_rejected(self):
        """Windows 盘符路径必须被拒绝。"""
        base = tempfile.gettempdir()
        with pytest.raises(ValueError):
            safe_join(base, "C:\\Windows\\System32")

    def test_embedded_traversal_is_rejected(self):
        """路径中间夹带 .. 也必须被拒绝。"""
        base = tempfile.gettempdir()
        with pytest.raises(ValueError):
            safe_join(base, "images", "..", "..", "outside.txt")

    def test_sibling_prefix_is_not_confused(self):
        """同名前缀的兄弟目录不算越界(base 与 base2 必须区分)。"""
        base = os.path.join(tempfile.gettempdir(), "cf_safe_base")
        with pytest.raises(ValueError):
            safe_join(base, "..", "cf_safe_base_evil", "x.txt")


class TestAtlasDirectoryHelper:
    """图集目录拼接辅助函数。"""

    def test_normal_directory_is_allowed(self):
        """正常子目录允许。"""
        from backend.routers.atlas import _safe_atlas_dir

        result = _safe_atlas_dir(1, "sub")
        assert result.replace("/", os.sep).endswith(os.path.join("1", "sub"))

    def test_traversal_directory_is_rejected(self):
        """含 .. 的目录名必须被拒绝(否则可越界创建/删除目录)。"""
        from backend.routers.atlas import _safe_atlas_dir

        with pytest.raises(ValueError):
            _safe_atlas_dir(1, "..", "..", "evil")

    def test_nested_directory_is_allowed(self):
        """多级子目录仍然可用。"""
        from backend.routers.atlas import _safe_atlas_dir

        result = _safe_atlas_dir(1, "sub", "deeper")
        assert result.replace("/", os.sep).endswith(os.path.join("1", "sub", "deeper"))


class TestRouteRejectsTraversal:
    """路由层必须把穿越请求转成 400, 而不是 500 或静默成功。"""

    @pytest.fixture
    def atlas_id(self):
        """创建一个临时图集, 测试结束后删除(含测试产生的物理目录)。"""
        import shutil

        from backend.database import Atlas, SessionLocal, init_db
        from backend.routers.atlas import IMAGE_STORAGE_DIR

        init_db()
        db = SessionLocal()
        name = "cf_safe_path_test_atlas"
        atlas = db.query(Atlas).filter(Atlas.name == name).first()
        if atlas is None:
            atlas = Atlas(name=name, description="路径穿越测试用图集")
            db.add(atlas)
            db.commit()
            db.refresh(atlas)
        aid = atlas.id
        yield aid
        # 清理测试产生的物理目录(正常目录用例会真的建目录)
        atlas_dir = os.path.join(IMAGE_STORAGE_DIR, str(aid))
        if os.path.isdir(atlas_dir):
            shutil.rmtree(atlas_dir, ignore_errors=True)
        db.query(Atlas).filter(Atlas.id == aid).delete()
        db.commit()
        db.close()

    def test_create_directory_rejects_traversal(self, atlas_id):
        """POST /atlas/{id}/directories?directory=../../evil -> 400 非法路径。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app

        client = TestClient(fastapi_app)
        resp = client.post(
            f"/api/atlas/{atlas_id}/directories", params={"directory": "../../evil"}
        )
        assert resp.status_code == 400, resp.text

    def test_delete_directory_rejects_traversal(self, atlas_id):
        """DELETE /atlas/{id}/directories?directory=../../evil -> 400 非法路径。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app

        client = TestClient(fastapi_app)
        resp = client.delete(
            f"/api/atlas/{atlas_id}/directories", params={"directory": "../../evil"}
        )
        assert resp.status_code == 400, resp.text

    def test_normal_directory_is_accepted(self, atlas_id):
        """正常子目录仍应创建成功(修复不能把功能一起挡掉)。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app

        client = TestClient(fastapi_app)
        resp = client.post(
            f"/api/atlas/{atlas_id}/directories", params={"directory": "safe_sub"}
        )
        assert resp.status_code == 200, resp.text
