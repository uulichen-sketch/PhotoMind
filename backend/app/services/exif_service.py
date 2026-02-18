"""EXIF 信息提取服务"""
import os
from typing import Optional, Dict, Any
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
import logging

# exifread 是可选依赖
try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    exifread = None
    EXIFREAD_AVAILABLE = False
    logging.getLogger(__name__).warning("exifread not installed. Install with: pip install exifread")

from app.services.geocoding_service import geocoding_service

logger = logging.getLogger(__name__)


class EXIFService:
    """EXIF 信息提取服务"""
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.heic', '.cr2', '.nef', '.arw'}
    
    @staticmethod
    def is_supported(filepath: str) -> bool:
        """检查文件格式是否支持"""
        ext = os.path.splitext(filepath)[1].lower()
        return ext in EXIFService.SUPPORTED_FORMATS
    
    @staticmethod
    def extract(filepath: str) -> Dict[str, Any]:
        """
        提取照片的 EXIF 信息
        
        Args:
            filepath: 照片文件路径
            
        Returns:
            包含 EXIF 信息的字典
        """
        result = {
            "datetime": None,
            "location": None,
            "camera": None,
            "lens": None,
            "iso": None,
            "aperture": None,
            "shutter": None,
            "focal_length": None,
            "width": None,
            "height": None,
            "file_size": None
        }
        
        try:
            # 获取文件大小
            result["file_size"] = os.path.getsize(filepath)
            
            # 使用 Pillow 获取基本信息
            with Image.open(filepath) as img:
                result["width"], result["height"] = img.size
                
                # 尝试获取 EXIF
                exif_data = img._getexif()
                if exif_data:
                    exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
                    
                    # 拍摄时间
                    if "DateTimeOriginal" in exif:
                        dt_str = str(exif["DateTimeOriginal"])
                        try:
                            dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                            result["datetime"] = dt.isoformat()
                        except:
                            result["datetime"] = dt_str
                    
                    # 相机型号
                    if "Model" in exif:
                        make = exif.get("Make", "")
                        model = exif["Model"]
                        if make and not model.startswith(make):
                            result["camera"] = f"{make} {model}"
                        else:
                            result["camera"] = model
                    
                    # ISO
                    if "ISOSpeedRatings" in exif:
                        result["iso"] = int(exif["ISOSpeedRatings"])
                    
                    # 光圈
                    if "FNumber" in exif:
                        fnum = exif["FNumber"]
                        if hasattr(fnum, 'numerator'):
                            result["aperture"] = f"f/{fnum.numerator / fnum.denominator:.1f}"
                    
                    # 快门速度
                    if "ExposureTime" in exif:
                        exp = exif["ExposureTime"]
                        if hasattr(exp, 'numerator'):
                            if exp.numerator >= exp.denominator:
                                result["shutter"] = f"{exp.numerator / exp.denominator:.1f}s"
                            else:
                                result["shutter"] = f"1/{exp.denominator // exp.numerator}s"
                    
                    # 焦距
                    if "FocalLength" in exif:
                        fl = exif["FocalLength"]
                        if hasattr(fl, 'numerator'):
                            result["focal_length"] = f"{fl.numerator / fl.denominator:.0f}mm"
                    
                    # GPS 信息
                    if "GPSInfo" in exif:
                        gps_info = exif["GPSInfo"]
                        lat = EXIFService._get_gps_value(gps_info, 2)
                        lon = EXIFService._get_gps_value(gps_info, 4)
                        lat_ref = gps_info.get(1)
                        lon_ref = gps_info.get(3)
                        if lat is not None and str(lat_ref).upper() == "S":
                            lat = -lat
                        if lon is not None and str(lon_ref).upper() == "W":
                            lon = -lon
                        if lat is not None and lon is not None:
                            result["location"] = f"{lat:.4f}, {lon:.4f}"
                            result["gps_latitude"] = lat
                            result["gps_longitude"] = lon
            
            # 使用 exifread 获取更多信息（如镜头）- 可选
            if EXIFREAD_AVAILABLE:
                try:
                    with open(filepath, 'rb') as f:
                        tags = exifread.process_file(f, details=False)
                        
                        # 镜头信息
                        lens_tags = ['LensModel', 'LensSpec', 'LensType']
                        for tag in lens_tags:
                            if tag in tags:
                                result["lens"] = str(tags[tag])
                                break
                                
                except Exception as e:
                    logger.debug(f"exifread failed for {filepath}: {e}")
                
        except Exception as e:
            logger.error(f"Failed to extract EXIF from {filepath}: {e}")
        
        return result
    
    @staticmethod
    def _get_gps_value(gps_info: Dict, key: int) -> Optional[float]:
        """从 GPS 信息中提取经纬度"""
        if key not in gps_info:
            return None

        value = gps_info[key]

        # Decimal degrees (already a float/int)
        if isinstance(value, (int, float)):
            return float(value)

        # DMS tuple/list, e.g. (40.0, 3.0, 7.152099)
        if isinstance(value, (tuple, list)) and len(value) >= 3:
            def _to_float(v):
                if hasattr(v, 'numerator') and hasattr(v, 'denominator') and v.denominator:
                    return v.numerator / v.denominator
                return float(v)

            try:
                degrees = _to_float(value[0])
                minutes = _to_float(value[1])
                seconds = _to_float(value[2])
                return degrees + minutes / 60.0 + seconds / 3600.0
            except Exception:
                return None

        # Rational value
        if hasattr(value, 'numerator') and hasattr(value, 'denominator') and value.denominator:
            return value.numerator / value.denominator

        return None
    
    @staticmethod
    def format_datetime(iso_datetime: Optional[str]) -> str:
        """
        将 ISO 格式时间转为友好格式
        
        Args:
            iso_datetime: ISO 格式的时间字符串
            
        Returns:
            友好格式的时间，如"2025年7月15日 下午3:20"
        """
        if not iso_datetime:
            return "未知时间"
        
        try:
            dt = datetime.fromisoformat(iso_datetime)
            hour = dt.hour
            period = "上午" if hour < 12 else "下午"
            hour_12 = hour if hour <= 12 else hour - 12
            return f"{dt.year}年{dt.month}月{dt.day}日 {period}{hour_12}:{dt.minute:02d}"
        except:
            return iso_datetime
