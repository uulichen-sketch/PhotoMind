"""Image analysis service (GLM-4V)."""
import base64
import json
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class VisionService:
    """Image analysis service."""

    def __init__(self):
        self.api_key = settings.zhipu_api_key
        self.base_url = settings.zhipu_base_url
        self.model = settings.zhipu_vision_model
        self.client = httpx.AsyncClient(timeout=60.0)

    @staticmethod
    def _safe_score(value: object, default: float = 2.8) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = default
        return round(min(max(score, 1.0), 5.0), 1)

    @staticmethod
    def _build_camera_context(capture_params: Optional[Dict[str, Any]]) -> str:
        if not capture_params:
            return "未提供拍摄参数。"
        fields = [
            ("camera", "相机"),
            ("lens", "镜头"),
            ("iso", "ISO"),
            ("aperture", "光圈"),
            ("shutter", "快门"),
            ("focal_length", "焦距"),
            ("datetime", "拍摄时间"),
            ("location", "拍摄地点"),
            ("width", "宽度"),
            ("height", "高度"),
        ]
        parts = []
        for key, label in fields:
            value = capture_params.get(key)
            if value not in (None, "", []):
                parts.append(f"{label}: {value}")
        return "；".join(parts) if parts else "未提供拍摄参数。"

    @staticmethod
    def _normalize_suggestions(value: object) -> List[str]:
        if isinstance(value, list):
            result = [str(v).strip() for v in value if str(v).strip()]
            return result[:5]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            parts = [p.strip("-• \t") for p in text.split("\n") if p.strip()]
            return parts[:5]
        return []

    @staticmethod
    def _fallback_suggestions(
        composition: float,
        color: float,
        lighting: float,
        sharpness: float,
        capture_params: Optional[Dict[str, Any]],
    ) -> List[str]:
        tips: List[str] = []
        if composition < 3.6:
            tips.append("拍摄前先确定主体并简化背景，使用三分法或引导线提升画面组织。")
        if color < 3.6:
            tips.append("尝试在黄金时段拍摄并统一白平衡，避免杂色光源导致色彩混乱。")
        if lighting < 3.6:
            tips.append("优先选择侧逆光或柔和散射光，必要时用曝光补偿保护高光与阴影细节。")
        if sharpness < 3.6:
            tips.append("提高快门速度或稳定机位，按焦距安全快门原则减少抖动和拖影。")

        if capture_params:
            iso = capture_params.get("iso")
            shutter = str(capture_params.get("shutter") or "")
            try:
                if iso is not None and int(iso) >= 1600:
                    tips.append("当前 ISO 偏高，建议优先补光或上三脚架，把 ISO 控制在更低区间。")
            except Exception:
                pass
            if shutter and "1/" in shutter:
                try:
                    denom = int(shutter.split("1/")[1].split("s")[0])
                    if denom < 100:
                        tips.append("快门偏慢，拍摄运动目标建议至少使用 1/250s 以上冻结动作。")
                except Exception:
                    pass

        if not tips:
            tips.append("可尝试变化机位高度与拍摄距离，强化主体层次和叙事感。")
        return tips[:5]

    @classmethod
    def _compute_overall(
        cls,
        composition: object,
        color: object,
        lighting: object,
        sharpness: object,
        creativity: object = None,
    ) -> float:
        c1 = cls._safe_score(composition)
        c2 = cls._safe_score(color)
        c3 = cls._safe_score(lighting)
        c4 = cls._safe_score(sharpness)
        cr = cls._safe_score(creativity, default=(c1 + c2 + c3 + c4) / 4.0)
        overall = c1 * 0.25 + c2 * 0.2 + c3 * 0.25 + c4 * 0.2 + cr * 0.1
        return round(min(max(overall, 1.0), 5.0), 1)

    @staticmethod
    def _prepare_image_base64(image_path: str) -> str:
        """
        Convert source image to a standard JPEG payload for vision API.
        This avoids unsupported container formats such as MPO and reduces payload size.
        """
        max_side = 2048
        with Image.open(image_path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            elif img.mode == "L":
                img = img.convert("RGB")

            w, h = img.size
            long_side = max(w, h)
            if long_side > max_side:
                scale = max_side / long_side
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=90, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

    async def analyze_photo(
        self,
        image_path: str,
        capture_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a photo and return structured metadata."""
        try:
            image_data = self._prepare_image_base64(image_path)
            camera_context = self._build_camera_context(capture_params)

            prompt = """你是一位专业摄影评委和商业修图总监。请结合照片内容与拍摄参数进行严格评分，并仅输出 JSON，不要输出 markdown 代码块。

拍摄参数（可能不完整）：
<<CAMERA_CONTEXT>>

要求：
1. description: 2-3句中文描述，包含主体、场景、光线和氛围。
2. tags: 5-8个中文标签，按相关性排序。
3. subjects: 主体简述。
4. mood: 情绪/氛围。
5. scores: 1.0-5.0，保留1位小数，包含 composition/color/lighting/sharpness/reason/suggestions。
6. creativity: 1.0-5.0，可选，用于整体分计算。
7. 分数必须有差异化，不能模板化，禁止所有维度都给高分。
8. 评分应偏严格：普通记录照通常 2.8-3.8；明显优秀作品才 4.2 以上；4.6+ 仅限专业级作品。
9. 请参考拍摄参数判断技术质量，例如：
   - ISO 过高可能带来噪点，清晰度和色彩应扣分；
   - 快门过慢可能导致运动模糊，清晰度应扣分；
   - 光圈与焦距会影响景深和主体分离，构图和清晰度应相应评价。
10. suggestions 必须给出 3-5 条可执行建议，避免空泛表达，尽量包含参数级建议（快门/ISO/光圈/焦距/机位/光线）。

返回 JSON 结构：
{
  "description": "<string>",
  "tags": ["<tag1>", "<tag2>"],
  "subjects": "<string>",
  "mood": "<string>",
  "scores": {
    "composition": <1.0-5.0>,
    "color": <1.0-5.0>,
    "lighting": <1.0-5.0>,
    "sharpness": <1.0-5.0>,
    "reason": "<string>",
    "suggestions": ["<建议1>", "<建议2>", "<建议3>"]
  },
  "creativity": <1.0-5.0>
}
"""
            prompt = prompt.replace("<<CAMERA_CONTEXT>>", camera_context)

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                    "max_tokens": 500,
                },
            )

            if response.status_code != 200:
                logger.error("GLM-4V API error: %s - %s", response.status_code, response.text)
                return {"description": "无法识别", "tags": []}

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            try:
                if "```json" in content:
                    json_str = content.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in content:
                    json_str = content.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    json_str = content.strip()

                parsed = json.loads(json_str)
                tags = parsed.get("tags", [])
                if not isinstance(tags, list):
                    tags = []

                mood = parsed.get("mood", "")
                subjects = parsed.get("subjects", "")

                if mood and mood not in tags:
                    tags.append(mood)
                if subjects and subjects not in tags:
                    tags.append(subjects)

                description = parsed.get("description", "") or ""
                if subjects and subjects not in description:
                    description = f"{subjects}。{description}"
                if mood and mood not in description:
                    description = f"{description} 整体氛围{mood}。"

                scores_data = parsed.get("scores", {})
                composition = self._safe_score(scores_data.get("composition"))
                color = self._safe_score(scores_data.get("color"))
                lighting = self._safe_score(scores_data.get("lighting"))
                sharpness = self._safe_score(scores_data.get("sharpness"))
                overall = self._compute_overall(
                    composition,
                    color,
                    lighting,
                    sharpness,
                    parsed.get("creativity"),
                )
                suggestions = self._normalize_suggestions(scores_data.get("suggestions"))
                if len(suggestions) < 3:
                    suggestions = self._fallback_suggestions(
                        composition,
                        color,
                        lighting,
                        sharpness,
                        capture_params,
                    )

                scores = {
                    "composition": composition,
                    "color": color,
                    "lighting": lighting,
                    "sharpness": sharpness,
                    "overall": overall,
                    "reason": scores_data.get("reason", ""),
                    "suggestions": suggestions,
                }

                return {
                    "description": description,
                    "tags": tags,
                    "subjects": subjects,
                    "mood": mood,
                    "scores": scores,
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse GLM-4V response: %s", content)
                return {"description": content, "tags": []}

        except Exception as e:
            logger.error("Failed to analyze photo %s: %s", image_path, e)
            return {"description": "分析失败", "tags": []}

    async def batch_analyze(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Batch analyze photos."""
        results: List[Dict[str, Any]] = []
        for path in image_paths:
            results.append(await self.analyze_photo(path))
        return results

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


vision_service = VisionService()
