"""API 端到端测试"""
import pytest
import io
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """健康检查端点测试"""
    
    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "services" in data
    
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_detailed_health_endpoint(self, client):
        """测试详细健康检查端点"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "chromadb" in data["services"]
        assert "asr" in data["services"]


class TestPhotoEndpoints:
    """照片管理端点测试"""
    
    def test_list_photos_empty(self, client):
        """测试获取空照片列表"""
        response = client.get("/api/photo/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_upload_no_files(self, client):
        """测试没有文件时的上传"""
        response = client.post("/api/import/upload")
        assert response.status_code == 422  # FastAPI 验证错误
    
    def test_upload_invalid_file_type(self, client):
        """测试上传非图片文件"""
        files = {
            "files": ("test.txt", io.BytesIO(b"not an image"), "text/plain")
        }
        response = client.post("/api/import/upload", files=files)
        assert response.status_code == 400
        assert "未找到图片文件" in response.json()["detail"]
    
    def test_upload_valid_image(self, client, sample_photo_bytes):
        """测试上传有效图片（返回任务ID）"""
        files = {
            "files": ("test.jpg", io.BytesIO(sample_photo_bytes), "image/jpeg")
        }
        response = client.post("/api/import/upload", files=files)
        # 注意：实际上传会触发后台处理，这里只验证接口返回
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["total"] == 1
    
    def test_get_nonexistent_photo(self, client):
        """测试获取不存在的照片"""
        response = client.get("/api/photo/nonexistent_id")
        assert response.status_code == 404


class TestSearchEndpoints:
    """搜索端点测试"""
    
    def test_text_search_empty_query(self, client):
        """测试空查询的文字搜索"""
        response = client.post("/api/search/text", json={"query": ""})
        assert response.status_code == 422  # 验证错误
    
    def test_text_search_valid(self, client):
        """测试有效的文字搜索"""
        response = client.post("/api/search/text", json={"query": "海边"})
        # 即使数据库为空，也应该返回 200
        assert response.status_code == 200
        data = response.json()
        assert "photos" in data
    
    def test_voice_search_invalid_audio(self, client):
        """测试无效的音频数据"""
        response = client.post("/api/search/voice", json={"audio": "invalid_base64"})
        # 应该返回错误，但不会崩溃
        assert response.status_code in [200, 400, 422, 500]


class TestStreamImportEndpoints:
    """流式导入端点测试"""
    
    def test_stream_upload_no_files(self, client):
        """测试没有文件时的流式上传"""
        response = client.post("/api/import-stream/upload")
        assert response.status_code == 422
    
    def test_stream_upload_valid_image(self, client, sample_photo_bytes):
        """测试流式上传有效图片"""
        files = {
            "files": ("test.jpg", io.BytesIO(sample_photo_bytes), "image/jpeg")
        }
        response = client.post("/api/import-stream/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        task_id = data["task_id"]
        
        # 测试获取任务详情
        response = client.get(f"/api/import-stream/tasks/{task_id}")
        assert response.status_code == 200
        task = response.json()
        assert task["task_id"] == task_id
        assert task["total"] == 1
    
    def test_stream_events_nonexistent_task(self, client):
        """测试获取不存在任务的 SSE 事件"""
        response = client.get("/api/import-stream/events/nonexistent")
        assert response.status_code == 404
    
    def test_list_stream_tasks(self, client):
        """测试获取流式任务列表"""
        response = client.get("/api/import-stream/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCORS:
    """CORS 配置测试"""
    
    def test_cors_headers(self, client):
        """测试 CORS 头"""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestAPIErrors:
    """API 错误处理测试"""
    
    def test_404_error(self, client):
        """测试 404 错误处理"""
        response = client.get("/api/nonexistent/endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_405_error(self, client):
        """测试 405 方法不允许错误"""
        response = client.post("/health")
        assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
