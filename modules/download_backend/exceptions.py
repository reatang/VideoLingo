"""
# ----------------------------------------------------------------------------
# Download Backend 异常模块
# 
# 定义下载后端的专用异常类
# 提供详细的错误信息和异常分类
# ----------------------------------------------------------------------------
"""

from typing import Optional, Dict, Any


class DownloadBackendError(Exception):
    """下载后端基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class DownloadError(DownloadBackendError):
    """下载失败异常"""
    
    def __init__(self, message: str, url: Optional[str] = None, platform: Optional[str] = None):
        super().__init__(message, "DOWNLOAD_FAILED")
        self.url = url
        self.platform = platform
        if url:
            self.details['url'] = url
        if platform:
            self.details['platform'] = platform


class UnsupportedPlatformError(DownloadBackendError):
    """不支持的平台异常"""
    
    def __init__(self, message: str, platform: Optional[str] = None, available_platforms: Optional[list] = None):
        super().__init__(message, "UNSUPPORTED_PLATFORM")
        self.platform = platform
        self.available_platforms = available_platforms or []
        if platform:
            self.details['platform'] = platform
        if available_platforms:
            self.details['available_platforms'] = available_platforms


class NetworkError(DownloadBackendError):
    """网络相关异常"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message, "NETWORK_ERROR")
        self.status_code = status_code
        self.response_text = response_text
        if status_code:
            self.details['status_code'] = status_code
        if response_text:
            self.details['response_text'] = response_text


class AuthenticationError(DownloadBackendError):
    """认证失败异常"""
    
    def __init__(self, message: str, platform: Optional[str] = None):
        super().__init__(message, "AUTH_FAILED")
        self.platform = platform
        if platform:
            self.details['platform'] = platform


class ConfigurationError(DownloadBackendError):
    """配置错误异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, expected_type: Optional[str] = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key
        self.expected_type = expected_type
        if config_key:
            self.details['config_key'] = config_key
        if expected_type:
            self.details['expected_type'] = expected_type


class VideoNotFoundError(DownloadBackendError):
    """视频未找到异常"""
    
    def __init__(self, message: str, url: Optional[str] = None, video_id: Optional[str] = None):
        super().__init__(message, "VIDEO_NOT_FOUND")
        self.url = url
        self.video_id = video_id
        if url:
            self.details['url'] = url
        if video_id:
            self.details['video_id'] = video_id


class QualityNotAvailableError(DownloadBackendError):
    """请求的质量不可用异常"""
    
    def __init__(self, message: str, requested_quality: Optional[str] = None, available_qualities: Optional[list] = None):
        super().__init__(message, "QUALITY_NOT_AVAILABLE")
        self.requested_quality = requested_quality
        self.available_qualities = available_qualities or []
        if requested_quality:
            self.details['requested_quality'] = requested_quality
        if available_qualities:
            self.details['available_qualities'] = available_qualities


class DependencyError(DownloadBackendError):
    """依赖缺失异常"""
    
    def __init__(self, message: str, dependency: Optional[str] = None, install_command: Optional[str] = None):
        super().__init__(message, "DEPENDENCY_ERROR")
        self.dependency = dependency
        self.install_command = install_command
        if dependency:
            self.details['dependency'] = dependency
        if install_command:
            self.details['install_command'] = install_command


class FileSystemError(DownloadBackendError):
    """文件系统相关异常"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, operation: Optional[str] = None):
        super().__init__(message, "FILESYSTEM_ERROR")
        self.file_path = file_path
        self.operation = operation
        if file_path:
            self.details['file_path'] = file_path
        if operation:
            self.details['operation'] = operation


class TimeoutError(DownloadBackendError):
    """超时异常"""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None, operation: Optional[str] = None):
        super().__init__(message, "TIMEOUT")
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        if timeout_seconds:
            self.details['timeout_seconds'] = timeout_seconds
        if operation:
            self.details['operation'] = operation


class FormatError(DownloadBackendError):
    """格式错误异常"""
    
    def __init__(self, message: str, format_name: Optional[str] = None, supported_formats: Optional[list] = None):
        super().__init__(message, "FORMAT_ERROR")
        self.format_name = format_name
        self.supported_formats = supported_formats or []
        if format_name:
            self.details['format_name'] = format_name
        if supported_formats:
            self.details['supported_formats'] = supported_formats


def handle_exception(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DownloadBackendError:
            # 重新抛出我们自己的异常
            raise
        except ImportError as e:
            raise DependencyError(f"缺少依赖: {str(e)}", install_command="pip install <missing_package>") from e
        except FileNotFoundError as e:
            raise FileSystemError(f"文件未找到: {str(e)}", operation="file_access") from e
        except PermissionError as e:
            raise FileSystemError(f"权限错误: {str(e)}", operation="file_permission") from e
        except ConnectionError as e:
            raise NetworkError(f"连接错误: {str(e)}") from e
        except Exception as e:
            # 捕获其他所有异常
            raise DownloadBackendError(f"未知错误: {str(e)}") from e
    
    return wrapper


# 导出所有异常类
__all__ = [
    'DownloadBackendError',
    'DownloadError',
    'UnsupportedPlatformError', 
    'NetworkError',
    'AuthenticationError',
    'ConfigurationError',
    'VideoNotFoundError',
    'QualityNotAvailableError',
    'DependencyError',
    'FileSystemError',
    'TimeoutError',
    'FormatError',
    'handle_exception'
] 