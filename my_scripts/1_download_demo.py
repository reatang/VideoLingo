from modules.download_backend.manager import DownloadManager
from modules.download_backend.models import DownloadConfig
from pathlib import Path
import sys

"""
# ----------------------------------------------------------------------------
# Download Backend 测试模块
# 
# 测试下载后端的基本功能
# 验证平台检测、引擎创建等核心功能
# ----------------------------------------------------------------------------
"""

def main():
    """主测试函数"""
    print("开始测试 Download Backend 模块")
    print("=" * 50)
    config = DownloadConfig()
    config.save_path = Path("output")

    download_url = sys.argv[1]

    try:
        # 创建管理器（现在使用 JSON 存储）
        manager = DownloadManager(config)

        # 下载视频
        manager.download_video(download_url)

        # 所有查询功能保持不变
        videos = manager.find_downloaded_videos(title_filter="music")
        stats = manager.get_download_statistics()
        
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 