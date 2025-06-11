# 现代化视频下载后端 (Download Backend)

这是一个基于 `yt-dlp` 的现代化视频下载系统，提供了类型安全、功能丰富的下载管理功能。

## 🚀 主要特性

### 🎯 核心功能
- **类型安全**: 使用 Python 类型提示和 dataclass
- **现代架构**: 采用面向对象设计，单一职责原则
- **配置灵活**: 支持多种分辨率、格式和下载选项
- **错误处理**: 完善的异常处理机制
- **进度追踪**: 实时下载进度回调

### 📊 数据管理
- **JSON 文件存储**: 轻量级持久化存储下载历史
- **智能查询**: 支持多维度查询已下载视频
- **统计分析**: 详细的下载统计和存储使用情况
- **数据导出**: 支持导出下载历史到 JSON

### 🔍 查询功能
- 按标题、上传者过滤
- 按下载状态过滤
- 按时间范围查询
- 限制返回数量
- 获取详细统计信息

## 📦 模块结构

```
modules/download_backend/
├── __init__.py          # 模块导入
├── models.py            # 数据模型定义
├── exceptions.py        # 异常类定义
├── downloader.py        # 核心下载器
├── manager.py           # 下载管理器
├── example.py          # 使用示例
└── README.md           # 文档说明
```

## 🛠️ 快速开始

### 1. 基础使用

```python
from pathlib import Path
from modules.download_backend import (
    DownloadManager, DownloadConfig, ResolutionType
)

# 创建配置
config = DownloadConfig(
    resolution=ResolutionType.HIGH_1080P,
    save_path=Path("downloads"),
    enable_thumbnail=True
)

# 创建管理器
manager = DownloadManager(config)

# 下载视频
result = manager.download_video("https://www.youtube.com/watch?v=xxx")
print(f"下载结果: {result.status}")
```

### 2. 获取视频信息

```python
# 获取视频信息（不下载）
video_info = manager.get_video_info("https://www.youtube.com/watch?v=xxx")
print(f"标题: {video_info.title}")
print(f"时长: {video_info.duration_formatted}")
print(f"上传者: {video_info.uploader}")
```

### 3. 查询已下载视频

```python
# 查询所有已下载视频
all_videos = manager.find_downloaded_videos()

# 按条件查询
recent_videos = manager.find_downloaded_videos(
    title_filter="music",           # 标题包含"music"
    days_ago=7,                     # 最近7天
    limit=10                        # 最多10个结果
)

# 根据URL查找
video = manager.find_downloaded_video_by_url("https://...")
```

### 4. 获取统计信息

```python
# 下载统计
stats = manager.get_download_statistics()
print(f"总下载数: {stats['total_downloads']}")
print(f"成功率: {stats['success_rate']*100:.1f}%")

# 存储使用情况
storage = manager.get_storage_usage()
print(f"总大小: {storage['total_size_formatted']}")
```

## 📋 配置选项

### DownloadConfig 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `resolution` | ResolutionType | HIGH_1080P | 目标分辨率 |
| `save_path` | Path | Path("output") | 保存路径 |
| `allowed_formats` | List[str] | ["mp4", "avi", ...] | 允许的格式 |
| `cookies_path` | Optional[Path] | None | Cookie文件路径 |
| `enable_thumbnail` | bool | True | 是否下载缩略图 |
| `enable_subtitle` | bool | False | 是否下载字幕 |
| `max_retries` | int | 3 | 最大重试次数 |
| `timeout` | int | 300 | 超时时间(秒) |

### 分辨率选项

```python
from modules.download_backend import ResolutionType

ResolutionType.BEST        # 最佳质量
ResolutionType.HIGH_1080P  # 1080p
ResolutionType.HIGH_720P   # 720p
ResolutionType.MEDIUM_480P # 480p
ResolutionType.LOW_360P    # 360p
```

## 🔍 查询功能详解

### find_downloaded_videos() 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `title_filter` | Optional[str] | 标题模糊匹配 |
| `uploader_filter` | Optional[str] | 上传者模糊匹配 |
| `status_filter` | Optional[DownloadStatus] | 按状态过滤 |
| `days_ago` | Optional[int] | 最近N天 |
| `limit` | Optional[int] | 限制结果数量 |

### 使用示例

```python
# 查询失败的下载
failed_downloads = manager.find_downloaded_videos(
    status_filter=DownloadStatus.FAILED
)

# 查询特定上传者的视频
uploader_videos = manager.find_downloaded_videos(
    uploader_filter="TED"
)

# 查询最近的音乐视频
music_videos = manager.find_downloaded_videos(
    title_filter="music",
    days_ago=30,
    limit=20
)
```

## 📊 统计信息

### get_download_statistics() 返回值

```python
{
    "total_downloads": 150,           # 总下载数
    "successful_downloads": 145,      # 成功下载数
    "failed_downloads": 5,            # 失败下载数
    "total_size_bytes": 5368709120,   # 总大小(字节)
    "success_rate": 0.967,            # 成功率
    "recent_downloads_7days": 12,     # 最近7天下载数
    "top_uploaders": [                # 热门上传者
        {"uploader": "TED", "count": 25},
        {"uploader": "MIT", "count": 15}
    ]
}
```

## 🛡️ 错误处理

### 异常类型

```python
from modules.download_backend.exceptions import (
    DownloadError,          # 通用下载错误
    VideoNotFoundError,     # 视频不存在
    NetworkError,           # 网络错误
    AuthenticationError     # 认证错误
)

try:
    result = manager.download_video(url)
except VideoNotFoundError as e:
    print(f"视频不存在: {e}")
except NetworkError as e:
    print(f"网络错误: {e}")
except DownloadError as e:
    print(f"下载失败: {e}")
```

## 🔧 进阶功能

### 1. 进度回调

```python
def progress_callback(progress: float):
    print(f"下载进度: {progress*100:.1f}%")

result = manager.download_video(url, progress_callback)
```

### 2. 数据导出

```python
# 导出下载历史
export_path = Path("history.json")
success = manager.export_download_history(export_path)
```

### 3. 清理功能

```python
# 清理失败的下载记录
cleaned_count = manager.cleanup_failed_downloads()
print(f"清理了 {cleaned_count} 条失败记录")
```

## 🔄 与原模块的对比

| 特性 | 原模块 | 新模块 |
|------|--------|--------|
| 架构设计 | 函数式 | 面向对象 |
| 类型安全 | ❌ | ✅ |
| 数据持久化 | ❌ | ✅ (JSON) |
| 查询功能 | ❌ | ✅ |
| 统计分析 | ❌ | ✅ |
| 进度追踪 | ❌ | ✅ |
| 错误处理 | 基础 | 完善 |
| 配置管理 | 基础 | 灵活 |

## 📝 注意事项

1. **依赖要求**: 需要安装 `yt-dlp` 库
2. **数据存储**: 自动创建 JSON 文件存储历史记录
3. **文件权限**: 确保有写入保存目录的权限
4. **网络环境**: 某些视频可能需要代理或Cookie
5. **存储空间**: 注意检查可用存储空间

## 🚀 运行示例

```bash
# 运行完整示例
python modules/download_backend/example.py
```

这个现代化的下载后端提供了完整的视频下载解决方案，不仅保留了原有功能，还大大增强了可维护性、可扩展性和用户体验。 