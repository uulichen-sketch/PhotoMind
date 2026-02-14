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
            
            # 构建请求 - 优化版提示词，激发更丰富的描述和评分
            prompt = """你是一位专业的摄影分析师，请详细分析这张照片，提供以下信息（用中文回复）：

1. **照片描述**：用2-3句话描述照片的内容、场景、主体和氛围。包括：
   - 主要拍摄对象（人物、建筑、风景、动物等）
   - 场景环境（室内/室外、自然环境、城市街景等）
   - 光线和氛围（明亮/昏暗、温暖/清冷、宁静/热闹等）
   - 拍摄角度和构图特点（特写、全景、俯视、仰拍等）

2. **分类标签**：列出5-8个最相关的标签，按重要性排序。标签类型包括：
   - 场景类型：风景、人像、街拍、建筑、美食、动物、植物等
   - 地点特征：海边、山顶、城市、公园、室内、古镇等
   - 时间特征：日出、日落、夜景、白天、清晨、黄昏等
   - 风格特征：复古、现代、文艺、简约、繁华等
   - 色彩特征：暖色调、冷色调、黑白、鲜艳、柔和等
   - 天气季节：晴天、阴天、雨天、雪景、春天、夏天等

3. **主体信息**：简要描述画面中的主要人物或物体（如有）

4. **情感氛围**：这张照片传达的情感或氛围（如：温馨、孤独、活力、宁静、浪漫、怀旧等）

5. **专业评分**（1-5星，保留1位小数）：作为专业摄影师，请从以下维度评分：
   - 构图评分：画面构图是否平衡、有层次、引导线是否清晰
   - 色彩评分：色彩搭配、饱和度、色调协调性
   - 光线评分：光线运用、曝光准确性、光影层次
   - 清晰度评分：对焦准确性、画面锐利度、细节保留
   - 整体评分：照片整体美感、创意性、视觉冲击力
   - 评分理由：简要说明评分依据

请严格按照以下 JSON 格式回复，确保所有字段都有值：
{
    "description": "详细的照片描述，2-3句话",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"],
    "subjects": "主要人物或物体的简要描述",
    "mood": "照片传达的情感氛围",
    "scores": {
        "composition": 4.5,
        "color": 4.0,
        "lighting": 4.5,
        "sharpness": 4.0,
        "overall": 4.2,
        "reason": "评分理由说明"
    }
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
                # 合并所有标签，包括场景、情感等
                tags = parsed.get("tags", [])
                mood = parsed.get("mood", "")
                subjects = parsed.get("subjects", "")
                
                # 将情感和主体也加入标签，方便搜索
                if mood and mood not in tags:
                    tags.append(mood)
                if subjects and subjects not in tags:
                    tags.append(subjects)
                
                # 构建更丰富的描述
                description = parsed.get("description", "")
                if subjects and subjects not in description:
                    description = f"{subjects}。{description}"
                if mood and mood not in description:
                    description = f"{description} 整体氛围{mood}。"
                
                # 提取评分数据
                scores_data = parsed.get("scores", {})
                scores = {
                    "composition": float(scores_data.get("composition", 0)),
                    "color": float(scores_data.get("color", 0)),
                    "lighting": float(scores_data.get("lighting", 0)),
                    "sharpness": float(scores_data.get("sharpness", 0)),
                    "overall": float(scores_data.get("overall", 0)),
                    "reason": scores_data.get("reason", "")
                }
                
                return {
                    "description": description,
                    "tags": tags,
                    "subjects": subjects,
                    "mood": mood,
                    "scores": scores
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
