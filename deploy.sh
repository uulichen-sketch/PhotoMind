#!/bin/bash

# PhotoMind 一键部署脚本
# 使用方法: ./deploy.sh

set -e

echo "🦞 PhotoMind 一键部署脚本"
echo "=========================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "📝 创建 .env 配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入你的 GLM_API_KEY"
    echo "   获取 API Key: https://open.bigmodel.cn/"
    exit 1
fi

# 检查 GLM_API_KEY
if grep -q "your-api-key-here" .env; then
    echo "❌ 请先在 .env 文件中配置 GLM_API_KEY"
    exit 1
fi

echo "✅ 配置文件检查通过"

# 构建镜像
echo "🔧 构建 Docker 镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo "🏥 检查服务状态..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务正常"
else
    echo "❌ 后端服务启动失败，请检查日志：docker-compose logs backend"
    exit 1
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 前端服务正常"
else
    echo "⚠️  前端服务可能还在启动中，请稍后访问"
fi

echo ""
echo "🎉 部署完成！"
echo "=========================="
echo "📱 前端地址: http://localhost:3000"
echo "🔧 后端地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""
echo "💡 常用命令："
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose down"
echo "  重启服务: docker-compose restart"
