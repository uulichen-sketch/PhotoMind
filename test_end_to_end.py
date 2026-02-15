#!/usr/bin/env python3
"""
PhotoMind 端到端测试脚本
在 Docker 容器运行后执行此脚本测试 API
"""

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, data=None, expected_status=200):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    try:
        if data:
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method=method
            )
        else:
            req = urllib.request.Request(url, method=method)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = response.read().decode('utf-8')
            try:
                body_json = json.loads(body)
            except:
                body_json = body
            
            success = status == expected_status
            icon = "✅" if success else "❌"
            print(f"{icon} {method} {path} - Status: {status}")
            if not success:
                print(f"   Expected: {expected_status}, Got: {status}")
            return success, body_json
    except urllib.error.HTTPError as e:
        status = e.code
        success = status == expected_status
        icon = "✅" if success else "❌"
        print(f"{icon} {method} {path} - Status: {status}")
        if not success:
            print(f"   Expected: {expected_status}, Got: {status}")
        return success, None
    except Exception as e:
        print(f"❌ {method} {path} - Error: {e}")
        return False, None

def main():
    print("=" * 60)
    print("PhotoMind 端到端 API 测试")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print()
    
    passed = 0
    failed = 0
    
    # 1. 健康检查测试
    print("【健康检查测试】")
    success, _ = test_endpoint("GET", "/health")
    if success: passed += 1
    else: failed += 1
    
    success, _ = test_endpoint("GET", "/health/detailed")
    if success: passed += 1
    else: failed += 1
    print()
    
    # 2. 照片列表测试
    print("【照片管理测试】")
    success, _ = test_endpoint("GET", "/api/photo/")
    if success: passed += 1
    else: failed += 1
    
    # 获取不存在的照片应该返回 404
    success, _ = test_endpoint("GET", "/api/photo/nonexistent", expected_status=404)
    if success: passed += 1
    else: failed += 1
    print()
    
    # 3. 搜索测试
    print("【搜索功能测试】")
    success, data = test_endpoint("POST", "/api/search/text", 
                                   data={"query": "海边"})
    if success: 
        passed += 1
        if data and "photos" in data:
            print(f"   搜索结果: {len(data['photos'])} 张照片")
    else: 
        failed += 1
    
    # 空查询应该返回 422
    success, _ = test_endpoint("POST", "/api/search/text", 
                               data={"query": ""}, expected_status=422)
    if success: passed += 1
    else: failed += 1
    print()
    
    # 4. 导入任务测试
    print("【导入功能测试】")
    success, _ = test_endpoint("GET", "/api/import/tasks")
    if success: passed += 1
    else: failed += 1
    
    # 上传无文件应该返回 422
    success, _ = test_endpoint("POST", "/api/import/upload", 
                               expected_status=422)
    if success: passed += 1
    else: failed += 1
    print()
    
    # 5. 流式导入测试
    print("【流式导入测试】")
    success, _ = test_endpoint("GET", "/api/import-stream/tasks")
    if success: passed += 1
    else: failed += 1
    
    # 不存在的任务应该返回 404
    success, _ = test_endpoint("GET", "/api/import-stream/events/nonexistent",
                               expected_status=404)
    if success: passed += 1
    else: failed += 1
    print()
    
    # 6. CORS 测试 (OPTIONS 请求)
    print("【CORS 配置测试】")
    req = urllib.request.Request(
        f"{BASE_URL}/health",
        method="OPTIONS",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            cors_header = response.headers.get('Access-Control-Allow-Origin')
            if cors_header:
                print(f"✅ CORS - Access-Control-Allow-Origin: {cors_header}")
                passed += 1
            else:
                print("❌ CORS - Missing Access-Control-Allow-Origin header")
                failed += 1
    except Exception as e:
        print(f"❌ CORS - Error: {e}")
        failed += 1
    print()
    
    # 汇总
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 所有测试通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()
