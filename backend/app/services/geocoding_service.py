"""GPS 逆地理编码服务（高德地图 API）"""
import httpx
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


class GeocodingService:
    """GPS 坐标转中文地址服务"""
    
    # 高德地图逆地理编码 API
    GEOCODE_REVERSE_URL = "https://restapi.amap.com/v3/geocode/regeo"
    
    def __init__(self):
        # 从配置读取高德 API Key，如果没有则使用空字符串
        self.api_key = getattr(settings, 'amap_api_key', '')
        self.client = httpx.AsyncClient(timeout=10.0)
        self._enabled = bool(self.api_key)
    
    @property
    def is_enabled(self) -> bool:
        """检查服务是否可用（需要配置 API Key）"""
        return self._enabled
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        将 GPS 坐标转换为中文地址
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            中文地址描述，如 "山东省青岛市金沙滩"，失败返回 None
        """
        if not self.is_enabled:
            logger.debug("Geocoding service not enabled (no API key)")
            return None
        
        try:
            params = {
                "key": self.api_key,
                "location": f"{longitude},{latitude}",  # 高德 API 格式：经度,纬度
                "extensions": "base",  # base 返回基本地址信息，all 返回详细信息
                "output": "json"
            }
            
            response = await self.client.get(self.GEOCODE_REVERSE_URL, params=params)
            
            if response.status_code != 200:
                logger.error(f"Amap API error: {response.status_code}")
                return None
            
            data = response.json()
            
            if data.get("status") != "1":
                logger.warning(f"Amap API returned error: {data.get('info', 'unknown')}")
                return None
            
            regeocode = data.get("regeocode", {})
            address_component = regeocode.get("addressComponent", {})
            
            # 构建地址描述
            address_parts = []
            
            # 省份
            province = address_component.get("province", "")
            if province and province not in ["[]", "", "中华人民共和国"]:
                address_parts.append(province)
            
            # 城市
            city = address_component.get("city", "")
            if city and city not in ["[]", ""]:
                # 处理直辖市情况
                if city != province:
                    address_parts.append(city)
            
            # 区县
            district = address_component.get("district", "")
            if district and district not in ["[]", ""]:
                address_parts.append(district)
            
            # 街道/乡镇
            township = address_component.get("township", "")
            if township and township not in ["[]", ""]:
                address_parts.append(township)
            
            # 标志性地点（POI）
            pois = regeocode.get("pois", [])
            if pois and len(pois) > 0:
                # 取最近的 POI
                nearest_poi = pois[0]
                poi_name = nearest_poi.get("name", "")
                if poi_name:
                    address_parts.append(poi_name)
            
            # 组合地址
            if address_parts:
                full_address = "".join(address_parts)
                logger.info(f"Reverse geocoded: ({latitude}, {longitude}) -> {full_address}")
                return full_address
            
            # 如果没有详细地址，返回格式化地址
            formatted_address = regeocode.get("formatted_address", "")
            if formatted_address:
                return formatted_address
            
            return None
            
        except Exception as e:
            logger.error(f"Reverse geocoding failed: {e}")
            return None
    
    def format_coordinate(self, coord_str: str) -> Optional[tuple]:
        """
        解析 EXIF 格式的坐标字符串
        
        Args:
            coord_str: 坐标字符串，如 "36.1234, 120.5678"
            
        Returns:
            (latitude, longitude) 元组，解析失败返回 None
        """
        try:
            # 处理 "36.1234, 120.5678" 格式
            parts = coord_str.replace(" ", "").split(",")
            if len(parts) == 2:
                lat = float(parts[0])
                lon = float(parts[1])
                return (lat, lon)
            return None
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse coordinate: {coord_str}, error: {e}")
            return None
    
    async def process_location(self, location_str: Optional[str]) -> Optional[str]:
        """
        处理位置信息，将坐标转换为地址
        
        Args:
            location_str: 位置字符串（坐标或地址）
            
        Returns:
            中文地址，如果已经是地址则直接返回
        """
        if not location_str:
            return None
        
        # 如果已经是中文地址（不含数字和逗号），直接返回
        if any(char in location_str for char in ["省", "市", "区", "县", "镇", "村"]):
            return location_str
        
        # 尝试解析坐标
        coords = self.format_coordinate(location_str)
        if coords:
            lat, lon = coords
            address = await self.reverse_geocode(lat, lon)
            if address:
                return address
        
        # 无法解析，返回原始值
        return location_str
    
    async def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        if not self.is_enabled:
            return {"status": "disabled", "message": "API key not configured"}
        
        try:
            # 使用一个已知坐标测试（北京天安门）
            test_result = await self.reverse_geocode(39.9042, 116.4074)
            if test_result:
                return {
                    "status": "healthy",
                    "message": "Service is working",
                    "sample_result": test_result
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "API call failed or returned no data"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e)
            }
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


# 全局服务实例
geocoding_service = GeocodingService()
