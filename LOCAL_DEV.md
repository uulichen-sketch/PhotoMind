# 本地开发环境设置指南

## 快速开始

### 1. 安装依赖

```bash
cd backend

# 安装核心依赖（如果还没有安装）
pip install fastapi uvicorn python-multipart pydantic pydantic-settings
pip install chromadb Pillow exifread httpx python-dotenv
```

### 2. 配置环境变量

确保项目根目录的 `.env` 文件已配置：

```bash
# 在项目根目录 D:\dev\PhotoMind\.env
ZHIPU_API_KEY=334a0d2da68f47bd93c43d0916508609.Lrk85xXB1i7Bb1W5
AMAP_API_KEY=a252f65b6ef7ec8387c990e63d0bfbd9
```

### 3. 启动后端服务

```bash
cd backend
python start_local.py
```

服务将启动在 http://localhost:8000

API 文档: http://localhost:8000/docs

### 4. 启动前端（可选）

```bash
cd frontend
npm install
npm run dev
```

前端将启动在 http://localhost:3000

---

## 目录结构

本地开发时数据存储在：

```
backend/
├── data/
│   ├── photos/      # 上传的照片
│   └── chroma/      # 向量数据库
├── models/
│   └── asr/         # ASR 模型（如需语音搜索）
└── ...
```

---

## 调试技巧

### 查看日志

后端启动后会实时显示日志，关注：

```
# AI 分析成功
Photo xxx processed successfully

# AI 分析失败
Failed to process photo xxx: ...

# API Key 错误
Illegal header value b'Bearer '  # 表示 API Key 未设置
```

### 测试 API

```bash
# 查看健康状态
curl http://localhost:8000/health

# 查看照片列表
curl http://localhost:8000/api/photos/

# 查看处理统计
curl http://localhost:8000/api/photos/processing-stats
```

### 重置数据库

如需清空所有数据重新开始：

```bash
# 删除数据目录
rm -rf backend/data/chroma

# 重新启动服务
python start_local.py
```

---

## 常见问题

### 1. API Key 未加载

**现象**: 日志显示 `Illegal header value b'Bearer '`

**解决**: 
- 检查 `.env` 文件是否存在且在项目根目录
- 确认 `ZHIPU_API_KEY` 已设置
- 重启后端服务

### 2. ChromaDB 连接错误

**现象**: `Collection not initialized`

**解决**:
```bash
# 删除旧数据，重新启动
rm -rf backend/data/chroma
python start_local.py
```

### 3. 端口被占用

**现象**: `[Errno 98] Address already in use`

**解决**:
```bash
# 查找并结束占用 8000 端口的进程
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F
```

---

## 开发模式特性

- **热重载**: 修改代码后服务自动重启
- **详细日志**: 显示 SQL 查询、API 请求等调试信息
- **API 文档**: 访问 http://localhost:8000/docs 查看自动生成的 API 文档
