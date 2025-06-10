"""
# ----------------------------------------------------------------------------
# Download Backend 测试模块
# 
# 测试下载后端的基本功能
# 验证平台检测、引擎创建等核心功能
# ----------------------------------------------------------------------------
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.download_backend import (
    download_video,
    get_video_info,
    get_supported_platforms,
    find_video_files
)
from modules.download_backend.utils import detect_platform, get_platform_info
from modules.download_backend.factory import get_engine_status
from modules.download_backend.exceptions import (
    DownloadBackendError,
    UnsupportedPlatformError,
    DownloadError
)


def test_platform_detection():
    """测试平台检测功能"""
    print("=== 测试平台检测 ===")
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ", 
        "https://www.bilibili.com/video/BV1AV411x7Gs",
        "https://b23.tv/BV1AV411x7Gs",
        "https://example.com/video.mp4"
    ]
    
    for url in test_urls:
        try:
            platform = detect_platform(url)
            platform_info = get_platform_info(platform)
            print(f"URL: {url}")
            print(f"  检测到平台: {platform}")
            print(f"  平台信息: {platform_info['name']} - {platform_info['description']}")
            print()
        except Exception as e:
            print(f"URL: {url} - 错误: {str(e)}")
            print()


def test_engine_status():
    """测试引擎状态"""
    print("=== 测试引擎状态 ===")
    
    try:
        platforms = get_supported_platforms()
        print(f"支持的平台: {platforms}")
        print()
        
        status = get_engine_status()
        for platform, info in status.items():
            print(f"平台: {platform}")
            print(f"  已注册: {info['registered']}")
            print(f"  已创建: {info['created']}")
            print(f"  已初始化: {info['initialized']}")
            print(f"  类名: {info['class_name']}")
            print()
    except Exception as e:
        print(f"获取引擎状态失败: {str(e)}")


def test_video_info():
    """测试获取视频信息（无需实际下载）"""
    print("=== 测试获取视频信息 ===")
    
    # 仅测试URL解析，不实际访问网络
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.bilibili.com/video/BV1AV411x7Gs"
    ]
    
    for url in test_urls:
        try:
            platform = detect_platform(url)
            print(f"URL: {url}")
            print(f"  检测到平台: {platform}")
            print(f"  状态: URL解析成功")
            print()
        except UnsupportedPlatformError as e:
            print(f"URL: {url} - 不支持的平台: {str(e)}")
            print()
        except Exception as e:
            print(f"URL: {url} - 其他错误: {str(e)}")
            print()


def test_exceptions():
    """测试异常处理"""
    print("=== 测试异常处理 ===")
    
    try:
        # 测试不支持的平台
        detect_platform("")
    except UnsupportedPlatformError as e:
        print(f"捕获UnsupportedPlatformError: {e}")
        print(f"错误详情: {e.to_dict()}")
        print()
    
    try:
        # 测试下载错误
        raise DownloadError("测试下载错误", url="http://example.com", platform="test")
    except DownloadError as e:
        print(f"捕获DownloadError: {e}")
        print(f"错误详情: {e.to_dict()}")
        print()


def main():
    """主测试函数"""
    print("开始测试 Download Backend 模块")
    print("=" * 50)
    
    try:
        test_platform_detection()
        test_engine_status()
        test_video_info()
        test_exceptions()
        
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 