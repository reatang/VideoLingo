# ----------------------------------------------------------------------------
# 下载模块异常定义
# ----------------------------------------------------------------------------

class DownloadError(Exception):
    """Download operation failed"""
    pass

class VideoNotFoundError(DownloadError):
    """Video not found or unavailable"""
    pass

class UnsupportedFormatError(DownloadError):
    """Unsupported video format"""
    pass

class NetworkError(DownloadError):
    """Network connection error"""
    pass

class AuthenticationError(DownloadError):
    """Authentication failed"""
    pass 