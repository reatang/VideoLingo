# ----------------------------------------------------------------------------
# 现代化下载后端使用示例
# ----------------------------------------------------------------------------

from pathlib import Path
from modules.download_backend import (
    DownloadManager, DownloadConfig, ResolutionType, DownloadStatus
)

def progress_callback(progress: float):
    """Progress callback function"""
    print(f"下载进度: {progress*100:.1f}%")

def main():
    """主函数 - 展示各种功能的使用方法"""
    
    print("🚀 现代化视频下载后端示例")
    print("=" * 50)
    
    # ----------------------------------------------------------------------------
    # 1. 创建下载配置
    # ----------------------------------------------------------------------------
    config = DownloadConfig(
        resolution=ResolutionType.HIGH_1080P,
        save_path=Path("downloads"),
        allowed_formats=["mp4", "avi", "mkv", "mov", "flv", "webm"],
        enable_thumbnail=True,
        enable_subtitle=False,
        max_retries=3
    )
    
    # 创建下载管理器
    manager = DownloadManager(config)
    
    print(f"📁 下载目录: {config.save_path}")
    print(f"🎯 目标分辨率: {config.resolution.value}")
    print(f"🖼️  启用缩略图: {'是' if config.enable_thumbnail else '否'}")
    print()
    
    # ----------------------------------------------------------------------------
    # 2. 获取视频信息（不下载）
    # ----------------------------------------------------------------------------
    print("📋 获取视频信息示例:")
    
    try:
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # 示例URL
        video_info = manager.get_video_info(test_url)
        
        print(f"  📺 标题: {video_info.title}")
        print(f"  ⏱️  时长: {video_info.duration_formatted}")
        print(f"  👤 上传者: {video_info.uploader}")
        print(f"  👁️  观看次数: {video_info.view_count:,}")
        print(f"  📊 可用格式: {', '.join(video_info.format_available)}")
        print()
        
    except Exception as e:
        print(f"  ❌ 获取信息失败: {e}")
        print()
    
    # ----------------------------------------------------------------------------
    # 3. 下载视频
    # ----------------------------------------------------------------------------
    print("⬇️  下载视频示例:")
    
    try:
        result = manager.download_video(test_url, progress_callback)
        
        if result.status == DownloadStatus.COMPLETED:
            print(f"  ✅ 下载成功!")
            print(f"  📁 文件路径: {result.file_path}")
            print(f"  📏 文件大小: {result.file_size_formatted}")
            print(f"  ⏰ 下载耗时: {result.download_time:.2f}秒")
            if result.thumbnail_path:
                print(f"  🖼️  缩略图: {result.thumbnail_path}")
        else:
            print(f"  ❌ 下载失败: {result.error_message}")
        print()
        
    except Exception as e:
        print(f"  💥 下载过程中发生错误: {e}")
        print()
    
    # ----------------------------------------------------------------------------
    # 4. 查询已下载的视频
    # ----------------------------------------------------------------------------
    print("🔍 查询已下载视频示例:")
    
    # 查询所有已下载的视频
    all_videos = manager.find_downloaded_videos()
    print(f"  📊 总共下载了 {len(all_videos)} 个视频")
    
    # 查询成功下载的视频
    successful_videos = manager.find_downloaded_videos(
        status_filter=DownloadStatus.COMPLETED
    )
    print(f"  ✅ 成功下载: {len(successful_videos)} 个")
    
    # 查询最近7天的下载
    recent_videos = manager.find_downloaded_videos(days_ago=7, limit=5)
    print(f"  📅 最近7天下载: {len(recent_videos)} 个")
    
    # 按标题搜索
    search_results = manager.find_downloaded_videos(title_filter="music")
    print(f"  🎵 包含'music'的视频: {len(search_results)} 个")
    
    # 显示最近的几个下载
    if recent_videos:
        print("  📝 最近下载的视频:")
        for video in recent_videos[:3]:
            print(f"    • {video.video_info.title[:50]}...")
            print(f"      📁 {video.file_path}")
            print(f"      📅 {video.created_at.strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # ----------------------------------------------------------------------------
    # 5. 获取下载统计
    # ----------------------------------------------------------------------------
    print("📊 下载统计信息:")
    
    stats = manager.get_download_statistics()
    if stats:
        print(f"  📈 总下载数: {stats['total_downloads']}")
        print(f"  ✅ 成功下载: {stats['successful_downloads']}")
        print(f"  ❌ 失败下载: {stats['failed_downloads']}")
        print(f"  📊 成功率: {stats['success_rate']*100:.1f}%")
        print(f"  💾 总大小: {stats['total_size_bytes'] / (1024**3):.2f} GB")
        print(f"  📅 最近7天: {stats['recent_downloads_7days']} 个下载")
        
        if stats['top_uploaders']:
            print("  🏆 热门上传者:")
            for uploader in stats['top_uploaders']:
                print(f"    • {uploader['uploader']}: {uploader['count']} 个视频")
    print()
    
    # ----------------------------------------------------------------------------
    # 6. 存储使用情况
    # ----------------------------------------------------------------------------
    print("💾 存储使用情况:")
    
    storage = manager.get_storage_usage()
    if storage:
        print(f"  📁 存储路径: {storage['save_path']}")
        print(f"  📄 文件数量: {storage['total_files']}")
        print(f"  📏 总大小: {storage['total_size_formatted']}")
    print()
    
    # ----------------------------------------------------------------------------
    # 7. 导出下载历史
    # ----------------------------------------------------------------------------
    print("📤 导出下载历史:")
    
    export_path = Path("download_history_export.json")
    if manager.export_download_history(export_path):
        print(f"  ✅ 历史记录已导出到: {export_path}")
    else:
        print(f"  ❌ 导出失败")
    print()
    
    # ----------------------------------------------------------------------------
    # 8. 清理失败的下载
    # ----------------------------------------------------------------------------
    print("🧹 清理失败的下载:")
    
    cleaned_count = manager.cleanup_failed_downloads()
    print(f"  🗑️  清理了 {cleaned_count} 条失败记录")
    print()
    
    print("🎉 示例演示完成!")

if __name__ == "__main__":
    main() 