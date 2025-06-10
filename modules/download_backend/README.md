# Download Backend 模块

Download Backend 是 VideoLingo 项目的视频下载后端模块，使用适配器模式和策略模式支持多平台视频下载。

## 架构特点

- **适配器模式**：统一不同平台的下载接口
- **策略模式**：根据URL自动选择合适的下载策略  
- **工厂模式**：动态创建和管理下载引擎
- **三阶段生命周期**：初始化期、配置期、运行期
- **异常自处理**：模块内部异常处理，不依赖外部

## 支持的平台

- **YouTube** - 使用 yt-dlp，支持高质量下载和字幕
- **Bilibili** - 使用 bilibili_api，支持FLV/MP4流和混流
- **Generic** - 通用下载器，支持大部分视频网站
- **扩展支持** - TikTok、Twitter、Instagram、Vimeo等（占位符）

## 基本使用

### 快速开始

```python
from modules.download_backend import download_video, get_video_info

# 自动检测平台并下载
result = download_video(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    save_path="downloads",
    resolution="1080"
)

if result.success:
    print(f"下载成功: {result.video_path}")
    print(f"文件大小: {result.file_size}")
else:
    print(f"下载失败: {result.error_message}")

# 获取视频信息
video_info = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"标题: {video_info.title}")
print(f"时长: {video_info.duration}秒")
```

### 平台检测

```python
from modules.download_backend.utils import detect_platform, get_platform_info

# 自动检测平台
platform = detect_platform("https://www.bilibili.com/video/BV1AV411x7Gs")
print(f"检测到平台: {platform}")  # 输出: bilibili

# 获取平台信息
info = get_platform_info(platform)
print(f"平台名称: {info['name']}")
print(f"描述: {info['description']}")
```

### 工厂模式使用

```python
from modules.download_backend.factory import create_download_engine, get_engine_status

# 创建特定平台的下载引擎
engine = create_download_engine("youtube")

# 配置引擎
engine.configure({
    'save_path': 'downloads',
    'resolution': '1080',
    'download_thumbnail': True
})

# 执行下载
result = engine.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# 查看引擎状态
status = get_engine_status()
for platform, info in status.items():
    print(f"{platform}: 已注册={info['registered']}, 已初始化={info['initialized']}")
```

## 配置系统

### YouTube 配置

```python
from modules.download_backend.config import YoutubeConfig

config = YoutubeConfig(
    save_path="downloads",
    resolution="1080",
    cookies_path="youtube_cookies.txt",  # 可选：用于访问私有视频
    download_subtitles=True,
    subtitle_languages=['zh', 'en']
)
```

### Bilibili 配置

```python
from modules.download_backend.config import BilibiliConfig

config = BilibiliConfig(
    save_path="downloads", 
    resolution="1080",
    sessdata="your_sessdata",     # Bilibili认证信息
    bili_jct="your_bili_jct",     # 从浏览器cookie获取
    buvid3="your_buvid3",         # 用于高质量下载
    ffmpeg_path="ffmpeg"          # FFmpeg路径
)
```

## 异常处理

模块定义了完整的异常体系：

```python
from modules.download_backend.exceptions import (
    DownloadError,
    UnsupportedPlatformError,
    NetworkError,
    AuthenticationError,
    ConfigurationError
)

try:
    result = download_video("https://invalid-url.com")
except UnsupportedPlatformError as e:
    print(f"不支持的平台: {e}")
    print(f"可用平台: {e.available_platforms}")
except DownloadError as e:
    print(f"下载失败: {e}")
    print(f"错误详情: {e.to_dict()}")
except NetworkError as e:
    print(f"网络错误: {e}")
```

## 高级功能

### 批量下载

```python
from modules.download_backend.adapters.youtube_adapter import YoutubeAdapter

adapter = YoutubeAdapter()
adapter.initialize()
adapter.configure({'save_path': 'downloads'})

urls = [
    "https://www.youtube.com/watch?v=video1",
    "https://www.youtube.com/watch?v=video2",
    "https://www.youtube.com/watch?v=video3"
]

results = adapter.batch_download(urls)
successful = sum(1 for r in results if r.success)
print(f"批量下载完成: {successful}/{len(urls)} 成功")
```

### 自定义适配器

```python
from modules.download_backend.base import DownloadEngineAdapter
from modules.download_backend.factory import register_custom_engine

class CustomAdapter(DownloadEngineAdapter):
    def __init__(self):
        super().__init__("CustomDownloader", "custom")
    
    def initialize(self):
        # 初始化逻辑
        self._initialized = True
    
    def download(self, url):
        # 下载逻辑
        pass
    
    def get_video_info(self, url):
        # 获取视频信息逻辑
        pass
    
    def is_supported(self, url):
        return "custom.com" in url
    
    def get_supported_domains(self):
        return ["custom.com"]

# 注册自定义适配器
register_custom_engine("custom", CustomAdapter)
```

## 依赖要求

### 基础依赖
- `yt-dlp` - YouTube和通用下载
- `requests` - HTTP请求
- `pathlib` - 路径处理

### 平台特定依赖
- **Bilibili**: `bilibili_api`, `ffmpeg`
- **高级功能**: `colorama` (Windows颜色支持)

安装命令：
```bash
pip install yt-dlp requests bilibili_api colorama
```

## 测试

运行测试验证模块功能：

```bash
cd modules/download_backend
python test_download.py
```

## 日志配置

```python
from modules.commons.logger import setup_logger, set_global_level
import logging

# 设置调试级别
set_global_level(logging.DEBUG)

# 获取模块专用日志器
logger = setup_logger("my_downloader")
logger.info("开始下载")
```

## 文件结构

```
modules/download_backend/
├── __init__.py              # 主入口和便捷函数
├── base.py                  # 抽象基类和数据模型
├── factory.py               # 工厂模式实现
├── utils.py                 # 工具函数
├── config.py                # 配置数据模型
├── exceptions.py            # 异常定义
├── adapters/                # 适配器实现
│   ├── __init__.py
│   ├── youtube_adapter.py   # YouTube适配器
│   ├── bilibili_adapter.py  # Bilibili适配器
│   └── generic_adapter.py   # 通用适配器
├── test_download.py         # 测试文件
└── README.md               # 本文档
```

## 最佳实践

1. **使用异常处理**：总是包装下载调用在try-catch中
2. **配置验证**：使用配置类的validate()方法验证配置
3. **资源清理**：长期运行的应用应调用factory.shutdown()
4. **日志记录**：启用适当的日志级别进行调试
5. **网络优化**：配置重试次数和超时时间
6. **文件管理**：使用safe路径创建避免文件名冲突

## 向后兼容

模块提供了向后兼容的函数：

```python
# 原有的下载函数仍然可用
from modules.download_backend import download_video_ytdlp, find_video_files

download_video_ytdlp("https://youtube.com/watch?v=123", "output", "1080")
video_path = find_video_files("output")
``` 