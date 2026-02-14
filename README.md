# PhotoMind - 智能照片管理系统

> 🦞 为摄影爱好者打造的本地化智能照片管理系统，支持语音搜索、AI识别、AI评分、大图浏览

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-green.svg)
![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)

## ✨ 核心特性

### 🎯 六大核心功能

| 功能 | 描述 |
|------|------|
| **🎤 语音搜索** | 按住说话 → 本地ASR识别 → 语义搜索返回相关照片 |
| **🖼️ 照片展示** | 现代化网格视图 + 大图浏览器 + 详情视图 |
| **📊 AI 评分** | 构图、色彩、光线、清晰度、整体五维度专业评分 |
| **🔍 大图浏览** | 支持缩放、拖拽、键盘导航、缩略图切换 |
| **📥 批量导入** | 文件夹选择/拖拽上传 → 提取信息 → AI识别 → 向量化存储 |
| **🤖 智能信息** | EXIF提取 + AI描述/标签 + GPS转中文地址 |

### 🔒 核心优势

- **完全本地化** - 所有数据本地存储，保护隐私
- **现代化 UI** - 紫蓝渐变配色，简洁优雅的界面设计
- **AI 评分** - 基于 GLM-4V 的专业摄影评分系统
- **大图浏览** - 沉浸式图片查看体验，支持缩放和拖拽
- **智能识别** - GLM-4V 自动生成丰富的照片描述、标签、情感和主体信息
- **GPS 转地址** - 自动将 GPS 坐标转为中文地址（山东省青岛市金沙滩）
- **语音搜索** - 本地 ASR 识别，无需联网
- **语义搜索** - 向量检索，支持自然语言搜索
- **一键部署** - Docker Compose 一键启动

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-username/photomind.git
cd photomind

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入：
# - GLM_API_KEY（必填）
# - AMAP_API_KEY（可选，用于 GPS 转地址）
# - ASR_MODEL_DIR（可选，语音识别模型路径）

# 3. 一键启动
docker-compose up -d

# 4. 访问系统
# 前端：http://localhost:3000
# 后端：http://localhost:8000
# API文档：http://localhost:8000/docs
```

### 方式二：源码部署

#### 后端部署

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export GLM_API_KEY="your-api-key"
export CHROMA_PERSIST_DIR="./data/chroma"

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

## 📖 使用指南

### 1. 导入照片

1. 点击「导入」页面
2. 点击选择文件夹，或将文件夹拖拽到上传区域
3. 确认文件列表后点击「开始导入」
4. 等待进度完成（系统会自动提取EXIF、生成AI描述和评分）

### 2. 浏览照片

- **首页**：查看所有照片的网格布局
- **点击照片**：打开大图浏览器
- **大图浏览器**：
  - 滚轮缩放 / 按钮缩放
  - 拖拽平移（放大后）
  - 左右箭头切换照片
  - 底部缩略图快速跳转
  - 查看 AI 评分详情

### 3. 搜索照片

#### 文字搜索
- 输入关键词：`海边`、`日落`、`2024年夏天`
- 或自然语言：`去年在海边拍的照片`

#### 语音搜索
- 点击麦克风按钮
- 说出搜索内容（如"去年在海边拍的照片"）
- 系统自动识别并搜索

> **注意**：首次使用语音搜索时，系统会自动下载 ASR 模型（约 50MB），请耐心等待。

### 4. 查看详情

点击任意照片卡片，查看：
- **AI 评分**：构图、色彩、光线、清晰度、整体五维度评分
- **AI 描述**：生成的照片描述
- **分类标签**：场景、地点、时间、风格等标签
- **拍摄信息**：时间、地点、相机、镜头、ISO、光圈、快门、焦距

## 🛠️ 技术架构

### 前端
- **框架**：Vue 3 + Vite
- **UI库**：Element Plus
- **特性**：现代化设计、响应式布局、图片浏览器组件

### 后端
- **框架**：FastAPI (Python 3.10+)
- **语音识别**：sherpa-onnx（本地）
- **图像识别**：GLM-4V API（智谱）
- **向量数据库**：ChromaDB（本地持久化）
- **EXIF提取**：Pillow + exifread

### 数据流程

```
照片导入 → EXIF提取 → GLM-4V识别(描述+标签+评分) → 向量化 → ChromaDB存储
                                              ↓
语音/文字搜索 → 向量检索 → 返回匹配照片 ← 查看大图/评分详情
```

## 📁 项目结构

```
photomind/
├── backend/                # 后端代码
│   ├── app/
│   │   ├── main.py        # 主入口
│   │   ├── models.py      # 数据模型
│   │   ├── routers/       # API路由
│   │   │   ├── photo_import.py  # 导入（支持文件夹和文件上传）
│   │   │   ├── search.py        # 搜索
│   │   │   └── photos.py        # 照片管理
│   │   └── services/      # 业务服务
│   │       ├── vector_service.py
│   │       ├── vision_service.py   # AI识别+评分
│   │       └── exif_service.py
│   ├── data/              # 数据存储
│   └── requirements.txt
├── frontend/              # 前端代码
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   │   ├── Home.vue
│   │   │   ├── Import.vue
│   │   │   ├── Search.vue
│   │   │   └── Detail.vue
│   │   ├── components/    # 通用组件
│   │   │   ├── ImageViewer.vue   # 图片浏览器
│   │   │   └── PhotoScore.vue    # 评分展示
│   │   ├── App.vue
│   │   └── main.js
│   └── package.json
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

## 🔧 配置说明

### 环境变量

```bash
# GLM-4V API（必填）
GLM_API_KEY=your-api-key-here

# 高德地图 API（可选，用于 GPS 坐标转地址）
AMAP_API_KEY=your-amap-api-key

# ASR 模型配置（可选）
ASR_MODEL_DIR=./models/asr          # 模型保存路径
ASR_MODEL_URL=                      # 自定义模型下载地址

# ChromaDB 配置
CHROMA_PERSIST_DIR=./data/chroma

# 服务端口（可选）
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### 支持的图片格式

- JPG / JPEG
- PNG
- WEBP
- GIF
- BMP
- TIFF

## 📊 API 文档

启动后端后访问：http://localhost:8000/docs

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 基础健康检查 |
| `/health/detailed` | GET | 详细健康检查（包含各服务状态） |
| `/api/import/start` | POST | 开始导入照片（文件夹路径） |
| `/api/import/upload` | POST | 上传照片文件 |
| `/api/import/status/{task_id}` | GET | 查询导入状态 |
| `/api/search/text` | POST | 文字搜索 |
| `/api/search/voice` | POST | 语音搜索 |
| `/api/photo/{photo_id}` | GET | 获取照片详情 |

## 🎨 界面预览

### 现代化设计
- **侧边栏导航**：清晰的页面切换
- **紫蓝渐变**：现代优雅的配色方案
- **卡片布局**：清晰的信息层级

### 图片浏览器
- **沉浸式体验**：全屏大图查看
- **便捷操作**：缩放、拖拽、键盘快捷键
- **信息展示**：底部显示拍摄信息和 AI 评分

### AI 评分展示
- **五维评分**：构图、色彩、光线、清晰度、整体
- **可视化**：进度条直观展示分数
- **评分理由**：AI 给出的评分依据

## 🔐 隐私保护

- ✅ 所有数据本地存储
- ✅ 仅 GLM-4V API 调用需要联网
- ✅ 照片文件不会上传到云端
- ✅ 用户完全掌控自己的数据

## 🗺️ 开发计划

- [x] 基础架构搭建
- [x] EXIF 信息提取
- [x] GLM-4V 图像识别（描述、标签、情感、主体）
- [x] ChromaDB 向量存储
- [x] 批量导入流程
- [x] 文字搜索功能
- [x] 语音搜索（sherpa-onnx 集成）
- [x] GPS 坐标转中文地址（高德地图）
- [x] 现代化 UI 设计
- [x] 大图浏览器功能
- [x] AI 照片评分系统
- [ ] 照片编辑功能
- [ ] 人脸识别 & 人物标签
- [ ] 移动端适配
- [ ] 相册管理功能

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [智谱 AI](https://open.bigmodel.cn/) - GLM-4V 视觉识别
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Element Plus](https://element-plus.org/) - UI 组件库
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架

## 📮 联系方式

- 项目主页：https://github.com/your-username/photomind
- 问题反馈：https://github.com/your-username/photomind/issues

---

🦞 Made with ❤️ by OpenClaw (AutoGLM)
