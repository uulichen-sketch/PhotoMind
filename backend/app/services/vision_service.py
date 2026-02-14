"""图像识别服务（GLM-4V）"""
import base64
import httpx
import logging
from typing import Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class VisionService:
    """图像识别服务"""
    
    def __init__(self):
        self.api_key = settings.zhipu_api_key
        self.base_url = settings.zhipu_base_url
        self.model = settings.zhipu_vision_model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def analyze_photo(self, image_path: str) -> Dict[str, any]:
        """
        分析照片内容，生成描述和标签
        
        Args:
            image_path: 照片文件路径
            
        Returns:
            {
                "description": "照片描述",
                "tags": ["标签1", "标签2", ...]
            }
        """
        try:
            # 读取并编码图片
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 构建请求
            prompt = """请分析这张照片，提供以下信息（用中文回复）：
1. 照片描述：用1-2句话描述照片的内容和场景
2. 分类标签：列出3-5个最相关的标签

请严格按照以下 JSON 格式回复：
{
    "description": "你的描述",
    "tags": ["标签1", "标签2", "标签3"]
}"""

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }],
                    "max_tokens": 500
                }
            )
            
            if response.status_code != 200:
                logger.error(f"GLM-4V API error: {response.status_code} - {response.text}")
                return {"description": "无法识别", "tags": []}
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析 JSON 响应
            import json
            # 尝试提取 JSON 部分
            try:
                # 如果响应包含 markdown 代码块，提取 JSON
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                
                parsed = json.loads(json_str)
                return {
                    "description": parsed.get("description", "未知"),
                    "tags": parsed.get("tags", [])
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse GLM-4V response: {content}")
                # 回退：使用整个响应作为描述
                return {"description": content, "tags": []}
                
        except Exception as e:
            logger.error(f"Failed to analyze photo {image_path}: {e}")
            return {"description": "分析失败", "tags": []}
    
    async def batch_analyze(self, image_paths: List[str]) -> List[Dict[str, any]]:
        """
        批量分析照片
        
        Args:
            image_paths: 照片路径列表
            
        Returns:
            分析结果列表
        """
        results = []
        for path in image_paths:
            result = await self.analyze_photo(path)
            results.append(result)
        return results
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


# 全局服务实例
vision_service = VisionService()
