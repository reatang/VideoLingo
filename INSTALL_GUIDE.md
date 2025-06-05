# VideoLingo 现代化安装指南

## 🚀 基于UV的新一代依赖管理

VideoLingo v3.0 引入了基于UV的现代化依赖管理系统，提供更快、更可靠的安装体验。

## 📋 安装方式对比

### 🆕 新安装器 (推荐)
```bash
# 使用现代化UV安装器
python install_uv.py
```

### 🔄 传统安装器 (兼容)
```bash
# 传统pip安装器
python install.py
```

## 🎯 安装模式选择

### 1. 最小化安装 (核心功能)
- **适用场景**: 仅需基础视频下载和处理功能
- **包含模块**: 视频下载、基础媒体处理、Web界面
- **依赖大小**: ~500MB
- **安装时间**: ~2分钟

```bash
# 自动选择 (低内存系统会推荐此模式)
python install_uv.py
```

### 2. 标准安装 (推荐)
- **适用场景**: 完整视频翻译和配音工作流
- **包含模块**: 所有核心功能 + NLP + PyTorch
- **依赖大小**: ~2GB (CPU) / ~3GB (GPU)
- **安装时间**: ~5分钟

```bash
# 默认推荐模式
python install_uv.py
# 选择 "标准安装 (推荐)"
```

### 3. 完整安装 (包含所有功能)
- **适用场景**: 专业用户，需要所有高级功能
- **包含模块**: 标准 + TTS + WhisperX + 音源分离
- **依赖大小**: ~4GB (CPU) / ~6GB (GPU)
- **安装时间**: ~10分钟

```bash
python install_uv.py
# 选择 "完整安装 (包含所有功能)"
```

### 4. 开发者模式
- **适用场景**: 参与VideoLingo开发
- **包含模块**: 完整安装 + 开发工具 + 测试框架
- **依赖大小**: ~7GB
- **安装时间**: ~15分钟

```bash
python install_uv.py
# 选择 "开发者模式"
```

## 🛠️ 系统要求检查

安装器会自动检测并显示：

### 硬件信息
- ✅ 操作系统和架构
- ✅ Python版本
- ✅ CPU核心数和内存大小
- ✅ NVIDIA GPU检测
- ✅ 可用包管理器

### 系统依赖
- ✅ FFmpeg (必需)
- ✅ Git (推荐)
- ✅ 字体支持 (Linux自动安装)

## 🎮 GPU加速支持

### NVIDIA GPU用户
```bash
# 自动检测GPU并安装CUDA版本PyTorch
python install_uv.py
# 安装器会自动推荐 "完整安装" 模式
```

### 无GPU或macOS用户
```bash
# 自动安装CPU版本PyTorch
python install_uv.py
# 安装器会提示性能注意事项
```

## 📦 UV包管理器优势

### 🚄 速度优势
- **安装速度**: 比pip快10-100倍
- **依赖解析**: 更智能的冲突解决
- **并行下载**: 多线程下载优化

### 🔒 可靠性提升
- **锁定文件**: 确保可重现的安装
- **依赖隔离**: 避免版本冲突
- **回滚支持**: 安装失败自动恢复

### 🎯 智能管理
- **自动选择**: 基于系统推荐最佳配置
- **增量安装**: 仅安装缺失的依赖
- **缓存优化**: 复用已下载的包

## 🔧 手动安装选项

### 使用UV直接安装
```bash
# 安装UV (如果未安装)
pip install uv

# 基础安装
uv pip install -e .

# GPU版本
uv pip install -e ".[full-gpu]"

# CPU版本
uv pip install -e ".[full]"

# 开发版本
uv pip install -e ".[dev]"
```

### 传统pip安装
```bash
# 基础安装
pip install -e .

# 带可选依赖
pip install -e ".[full]"
```

## 🚨 常见问题解决

### FFmpeg未安装
```bash
# Windows (使用Chocolatey)
choco install ffmpeg

# macOS (使用Homebrew)  
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

### CUDA版本问题
```bash
# 检查CUDA版本
nvidia-smi

# 手动安装特定CUDA版本的PyTorch
uv pip install torch==2.0.0+cu118 torchaudio==2.0.0+cu118 -f https://download.pytorch.org/whl/cu118/torch_stable.html
```

### 内存不足问题
```bash
# 选择最小化安装
python install_uv.py
# 选择 "最小化安装 (核心功能)"

# 或分步骤安装
uv pip install -e .
# 稍后根据需要安装可选组件
```

### 网络连接问题
```bash
# 使用国内镜像 (安装器会自动提示配置)
python install_uv.py
# 选择 "是" 配置PyPI镜像

# 手动配置UV镜像
uv pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -e .
```

## 📊 性能对比

| 安装方式 | 下载速度 | 安装时间 | 内存使用 | 可靠性 |
|---------|---------|---------|----------|--------|
| UV新安装器 | 🚀 极快 | ⚡ 2-10分钟 | 💾 优化 | 🔒 高 |
| 传统pip | 🐌 一般 | ⏰ 10-30分钟 | 💾 高 | ⚠️ 中 |

## 🎊 安装完成后

### 验证安装
```bash
# 运行基础测试
python modules/simple_test.py

# 启动Web界面
streamlit run st.py
```

### 首次启动注意事项
- 🕐 首次启动可能需要1-2分钟下载模型文件
- 📁 检查config.yaml配置文件
- 🔧 根据需要配置API密钥

### 更新依赖
```bash
# 重新运行安装器更新
python install_uv.py

# 或手动更新
uv pip install --upgrade -e .
```

## 🔄 从旧版本升级

### 备份配置
```bash
# 备份重要配置文件
cp config.yaml config.yaml.backup
cp -r output output_backup
```

### 清理旧依赖
```bash
# 可选：创建新的虚拟环境
python -m venv videolingo_new
source videolingo_new/bin/activate  # Linux/macOS
# 或
videolingo_new\Scripts\activate     # Windows
```

### 运行新安装器
```bash
python install_uv.py
```

## 📞 获取帮助

### 安装问题
- 🐛 [提交Issue](https://github.com/Huanshere/VideoLingo/issues)
- 💬 查看安装日志文件
- 🔍 搜索常见问题解决方案

### 性能优化
- 🎮 确保GPU驱动程序最新
- 💾 检查可用磁盘空间 (至少10GB)
- 🌐 使用稳定的网络连接

---

**享受VideoLingo v3.0的现代化安装体验！** 🚀 