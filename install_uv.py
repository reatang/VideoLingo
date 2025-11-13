"""
# ----------------------------------------------------------------------------
# VideoLingo Modern Installer - 基于UV的现代化依赖管理工具
# 
# 特性：
# 1. 使用uv进行超快依赖安装和管理
# 2. 智能环境检测和依赖分类
# 3. 可选依赖和模块化安装
# 4. 完善的错误处理和恢复机制
# 5. 跨平台兼容和优化
# 6. 用户友好的交互界面
# ----------------------------------------------------------------------------
"""

import os
import sys
import json
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import tempfile
import urllib.request
import hashlib

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ASCII Logo
ascii_logo = """
__     ___     _            _     _                    
\ \   / (_) __| | ___  ___ | |   (_)_ __   __ _  ___  
 \ \ / /| |/ _` |/ _ \/ _ \| |   | | '_ \ / _` |/ _ \ 
  \ V / | | (_| |  __/ (_) | |___| | | | | (_| | (_) |
   \_/  |_|\__,_|\___|\___/|_____|_|_| |_|\__, |\___/ 
                                          |___/        
🚀 Modern UV-based Installer v2.0
"""


class InstallationMode(Enum):
    """安装模式枚举"""
    MINIMAL = "minimal"      # 最小化安装
    STANDARD = "standard"    # 标准安装
    FULL = "full"           # 完整安装
    DEVELOPMENT = "dev"     # 开发者模式


class SystemType(Enum):
    """系统类型枚举"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class HardwareInfo:
    """硬件信息数据类"""
    has_nvidia_gpu: bool = False
    gpu_names: List[str] = None
    cuda_version: str = ""
    total_memory_gb: float = 0.0
    cpu_cores: int = 0
    
    def __post_init__(self):
        if self.gpu_names is None:
            self.gpu_names = []


@dataclass
class SystemInfo:
    """系统信息数据类"""
    system_type: SystemType
    python_version: str
    architecture: str
    hardware: HardwareInfo
    has_ffmpeg: bool = False
    has_git: bool = False
    has_uv: bool = False
    package_managers: List[str] = None
    
    def __post_init__(self):
        if self.package_managers is None:
            self.package_managers = []


@dataclass
class DependencyGroup:
    """依赖组数据类"""
    name: str
    description: str
    packages: List[str]
    optional: bool = False
    system_requirements: List[str] = None
    install_order: int = 0
    
    def __post_init__(self):
        if self.system_requirements is None:
            self.system_requirements = []


class ModernInstaller:
    """基于UV的现代化安装器"""
    
    def __init__(self):
        self.console = None
        self.system_info = None
        self.dependency_groups = {}
        self.config_file = Path("config.yaml")
        self.install_log = []
        
        # 初始化依赖组定义
        self._init_dependency_groups()
    
    def _init_dependency_groups(self):
        """初始化依赖组定义"""
        self.dependency_groups = {
            "core": DependencyGroup(
                name="核心依赖",
                description="VideoLingo运行所需的基础依赖",
                packages=[
                    "requests>=2.32.0",
                    "rich>=13.0.0",
                    "ruamel.yaml>=0.17.0",
                    "inquirerpy>=0.3.0",
                    "pydantic>=2.0.0",
                    "click>=8.0.0",
                ],
                install_order=1
            ),
            
            "media": DependencyGroup(
                name="媒体处理",
                description="音视频处理相关依赖",
                packages=[
                    "opencv-python>=4.8.0",
                    "moviepy>=1.0.3",
                    "pydub>=0.25.1",
                    "librosa>=0.10.0",
                    "resampy>=0.4.0",
                    "yt-dlp>=2024.1.0",
                ],
                system_requirements=["ffmpeg"],
                install_order=2
            ),
            
            "ml_core": DependencyGroup(
                name="机器学习核心",
                description="机器学习基础库",
                packages=[
                    "numpy>=1.24.0",
                    "pandas>=2.0.0",
                    "transformers>=4.35.0",
                    "tokenizers>=0.14.0",
                ],
                install_order=3
            ),
            
            "pytorch_cpu": DependencyGroup(
                name="PyTorch CPU版本",
                description="PyTorch CPU版本 (适用于无GPU或macOS)",
                packages=[
                    "torch>=2.1.0,<2.2.0",
                    "torchaudio>=2.1.0,<2.2.0",
                ],
                optional=True,
                install_order=4
            ),
            
            "pytorch_cuda": DependencyGroup(
                name="PyTorch CUDA版本",
                description="PyTorch CUDA版本 (需要NVIDIA GPU)",
                packages=[
                    "torch>=2.0.0,<2.1.0",
                    "torchaudio>=2.0.0,<2.1.0",
                ],
                optional=True,
                system_requirements=["cuda"],
                install_order=4
            ),
            
            "whisper": DependencyGroup(
                name="语音识别",
                description="WhisperX和相关ASR依赖",
                packages=[
                    # Note: av is pre-installed using pip on Windows (better wheel availability)
                    # Listed here for dependency tracking but skipped during installation
                    "av>=15.1.0",
                    "faster-whisper>=1.2.1",
                    "whisperx>=3.7.4",
                    "ctranslate2>=4.0.0",
                    "syllables",
                    "pypinyin",
                    "g2p-en",
                ],
                optional=False,
                install_order=5
            ),
            
            "nlp": DependencyGroup(
                name="自然语言处理",
                description="spaCy和文本处理依赖",
                packages=[
                    "spacy>=3.7.0",
                    "autocorrect-py",
                    "xmltodict",
                    "json-repair",
                ],
                install_order=6
            ),
            
            "tts": DependencyGroup(
                name="语音合成",
                description="TTS和音频合成依赖",
                packages=[
                    "edge-tts>=6.0.0",
                    "openai>=1.50.0",
                    "replicate>=0.30.0",
                ],
                optional=False,
                install_order=7
            ),
            
            "demucs": DependencyGroup(
                name="音源分离",
                description="Demucs人声分离 (可选)",
                packages=[
                    "demucs[dev] @ git+https://github.com/adefossez/demucs",
                ],
                optional=True,
                install_order=8
            ),
            
            "web": DependencyGroup(
                name="Web界面",
                description="Streamlit Web界面依赖",
                packages=[
                    "streamlit>=1.35.0",
                    "openpyxl>=3.1.0",
                ],
                install_order=9
            ),
        }
    
    def _get_rich_console(self):
        """懒加载Rich Console"""
        if self.console is None:
            try:
                from rich.console import Console
                from rich.panel import Panel
                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
                from rich.table import Table
                from rich.box import DOUBLE
                self.console = Console()
                self.Panel = Panel
                self.Progress = Progress
                self.SpinnerColumn = SpinnerColumn
                self.TextColumn = TextColumn
                self.BarColumn = BarColumn
                self.Table = Table
                self.DOUBLE = DOUBLE
            except ImportError:
                # 如果Rich未安装，使用基础安装
                self._install_uv_package("rich>=13.0.0")
                from rich.console import Console
                from rich.panel import Panel
                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
                from rich.table import Table
                from rich.box import DOUBLE
                self.console = Console()
                self.Panel = Panel
                self.Progress = Progress
                self.SpinnerColumn = SpinnerColumn
                self.TextColumn = TextColumn
                self.BarColumn = BarColumn
                self.Table = Table
                self.DOUBLE = DOUBLE
        return self.console
    
    def _install_uv_package(self, package: str) -> bool:
        """使用uv安装单个包"""
        try:
            subprocess.run([
                "uv", "pip", "install", "--python", sys.executable, package
            ], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 回退到pip
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", package
                ], check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                return False
    
    def check_and_install_uv(self) -> bool:
        """检查并安装UV"""
        try:
            # 检查uv是否已安装
            result = subprocess.run(["uv", "--version"], 
                                 capture_output=True, text=True, 
                                 encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                print(f"✅ UV已安装: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        
        print("📦 正在安装UV包管理器...")
        
        try:
            # 安装uv
            subprocess.run([sys.executable, "-m", "pip", "install", "uv"], 
                         check=True, capture_output=True)
            
            # 验证安装
            result = subprocess.run(["uv", "--version"], 
                                 capture_output=True, text=True,
                                 encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                print(f"✅ UV安装成功: {result.stdout.strip()}")
                return True
            else:
                print("❌ UV安装验证失败")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ UV安装失败: {e}")
            return False
    
    def detect_system_info(self) -> SystemInfo:
        """检测系统信息"""
        print("🔍 正在检测系统环境...")
        
        # 检测系统类型
        system = platform.system()
        if system == "Windows":
            system_type = SystemType.WINDOWS
        elif system == "Darwin":
            system_type = SystemType.MACOS
        elif system == "Linux":
            system_type = SystemType.LINUX
        else:
            system_type = SystemType.UNKNOWN
        
        # Python版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # 架构
        architecture = platform.machine()
        
        # 硬件信息
        hardware = self._detect_hardware()
        
        # 检查系统工具
        has_ffmpeg = self._check_command("ffmpeg")
        has_git = self._check_command("git")
        has_uv = self._check_command("uv")

        # 包管理器
        package_managers = self._detect_package_managers()
        
        self.system_info = SystemInfo(
            system_type=system_type,
            python_version=python_version,
            architecture=architecture,
            hardware=hardware,
            has_ffmpeg=has_ffmpeg,
            has_git=has_git,
            has_uv=has_uv,
            package_managers=package_managers
        )
        
        return self.system_info
    
    def _detect_hardware(self) -> HardwareInfo:
        """检测硬件信息"""
        hardware = HardwareInfo()
        
        # 检测CPU核心数
        try:
            import multiprocessing
            hardware.cpu_cores = multiprocessing.cpu_count()
        except:
            hardware.cpu_cores = 1
        
        # 检测内存
        try:
            import psutil
            hardware.total_memory_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            pass
        
        # 检测NVIDIA GPU
        try:
            # 首先尝试nvidia-ml-py（更轻量）
            subprocess.run([sys.executable, "-m", "pip", "install", "nvidia-ml-py"], 
                         check=True, capture_output=True)
            
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                hardware.has_nvidia_gpu = True
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    hardware.gpu_names.append(name)
            
            pynvml.nvmlShutdown()
            
        except Exception:
            # 回退检测方法
            try:
                result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], 
                                      capture_output=True, text=True, 
                                      encoding='utf-8', errors='ignore', timeout=5)
                if result.returncode == 0:
                    hardware.has_nvidia_gpu = True
                    hardware.gpu_names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
            except:
                pass
        
        return hardware
    
    def _check_command(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run([command, "-h"], capture_output=True, check=True, timeout=5)
            return True
        except:
            return False
    
    def _check_command_module(self, module: str) -> bool:
        """检查Python模块命令是否可用"""
        try:
            subprocess.run([sys.executable, "-m", module, "--version"], 
                         capture_output=True, check=True, timeout=5)
            return True
        except:
            return False
    
    def _detect_package_managers(self) -> List[str]:
        """检测可用的包管理器"""
        managers = []
        
        # 检查常见包管理器
        candidates = {
            "apt": ["apt", "--version"],
            "yum": ["yum", "--version"],
            "dnf": ["dnf", "--version"],
            "brew": ["brew", "--version"],
            "choco": ["choco", "--version"],
            "pacman": ["pacman", "--version"],
            "conda": ["conda", "--version"],
            "mamba": ["mamba", "--version"],
        }
        
        for name, cmd in candidates.items():
            try:
                subprocess.run(cmd, capture_output=True, check=True, timeout=3)
                managers.append(name)
            except:
                pass
        
        return managers
    
    def display_system_info(self):
        """显示系统信息"""
        console = self._get_rich_console()
        
        # 创建系统信息表格
        table = self.Table(title="🖥️  系统环境信息", box=self.DOUBLE)
        table.add_column("项目", style="cyan", no_wrap=True)
        table.add_column("值", style="white")
        
        table.add_row("操作系统", self.system_info.system_type.value.title())
        table.add_row("Python版本", self.system_info.python_version)
        table.add_row("系统架构", self.system_info.architecture)
        table.add_row("CPU核心数", str(self.system_info.hardware.cpu_cores))
        
        if self.system_info.hardware.total_memory_gb > 0:
            table.add_row("系统内存", f"{self.system_info.hardware.total_memory_gb:.1f} GB")
        
        table.add_row("NVIDIA GPU", "✅ 是" if self.system_info.hardware.has_nvidia_gpu else "❌ 否")
        
        if self.system_info.hardware.gpu_names:
            for i, gpu_name in enumerate(self.system_info.hardware.gpu_names):
                table.add_row(f"GPU {i}", gpu_name)
        
        table.add_row("FFmpeg", "✅ 已安装" if self.system_info.has_ffmpeg else "❌ 未安装")
        table.add_row("Git", "✅ 已安装" if self.system_info.has_git else "❌ 未安装")
        table.add_row("UV", "✅ 已安装" if self.system_info.has_uv else "❌ 未安装")
        
        if self.system_info.package_managers:
            table.add_row("包管理器", ", ".join(self.system_info.package_managers))
        
        console.print(table)
        print()
    
    def get_installation_recommendations(self) -> Tuple[InstallationMode, List[str]]:
        """获取安装建议"""
        recommendations = []
        mode = InstallationMode.STANDARD
        
        # 基于硬件推荐
        if self.system_info.hardware.has_nvidia_gpu:
            recommendations.append("🎮 检测到NVIDIA GPU，推荐安装CUDA版本PyTorch以获得最佳性能")
            mode = InstallationMode.FULL
        else:
            recommendations.append("💻 未检测到NVIDIA GPU，将安装CPU版本PyTorch")
        
        # 基于内存推荐
        if self.system_info.hardware.total_memory_gb > 0:
            if self.system_info.hardware.total_memory_gb < 8:
                recommendations.append("⚠️  系统内存较小，建议选择最小化安装")
                mode = InstallationMode.MINIMAL
            elif self.system_info.hardware.total_memory_gb >= 16:
                recommendations.append("🚀 系统内存充足，可以选择完整安装")
        
        # 基于系统工具推荐
        if not self.system_info.has_ffmpeg:
            recommendations.append("❌ 需要安装FFmpeg以支持音视频处理")
        
        if not self.system_info.has_git:
            recommendations.append("⚠️  建议安装Git以获取最新功能更新")
        
        return mode, recommendations
    
    def install_system_dependencies(self):
        """安装系统依赖"""
        console = self._get_rich_console()
        
        if not self.system_info.has_ffmpeg:
            console.print(self.Panel("🔧 FFmpeg安装指南", style="yellow"))
            
            if self.system_info.system_type == SystemType.WINDOWS:
                if "choco" in self.system_info.package_managers:
                    console.print("推荐使用Chocolatey安装: [bold cyan]choco install ffmpeg[/bold cyan]")
                else:
                    console.print("请访问 https://ffmpeg.org/download.html 下载Windows版本")
                    
            elif self.system_info.system_type == SystemType.MACOS:
                if "brew" in self.system_info.package_managers:
                    console.print("推荐使用Homebrew安装: [bold cyan]brew install ffmpeg[/bold cyan]")
                else:
                    console.print("请先安装Homebrew: https://brew.sh/")
                    
            elif self.system_info.system_type == SystemType.LINUX:
                if "apt" in self.system_info.package_managers:
                    console.print("Ubuntu/Debian: [bold cyan]sudo apt install ffmpeg[/bold cyan]")
                elif "yum" in self.system_info.package_managers:
                    console.print("CentOS/RHEL: [bold cyan]sudo yum install ffmpeg[/bold cyan]")
                elif "dnf" in self.system_info.package_managers:
                    console.print("Fedora: [bold cyan]sudo dnf install ffmpeg[/bold cyan]")
                else:
                    console.print("请使用系统包管理器安装ffmpeg")
            
            # 检查用户是否要继续
            try:
                from InquirerPy import inquirer
                continue_install = inquirer.confirm(
                    message="FFmpeg未安装，是否继续安装Python依赖？",
                    default=True
                ).execute()
                
                if not continue_install:
                    console.print("❌ 安装已取消")
                    return False
            except ImportError:
                console.print("⚠️  继续安装Python依赖...")
        
        # Linux字体安装
        if (self.system_info.system_type == SystemType.LINUX and 
            ("apt" in self.system_info.package_managers or "yum" in self.system_info.package_managers)):
            
            console.print("🔤 正在安装Noto字体...")
            try:
                if "apt" in self.system_info.package_managers:
                    subprocess.run(["sudo", "apt-get", "install", "-y", "fonts-noto"], 
                                 check=True, timeout=120)
                elif "yum" in self.system_info.package_managers:
                    subprocess.run(["sudo", "yum", "install", "-y", "google-noto*"], 
                                 check=True, timeout=120)
                console.print("✅ Noto字体安装完成")
            except subprocess.CalledProcessError:
                console.print("⚠️  Noto字体安装失败，请手动安装")
        
        return True
    
    def install_dependency_group(self, group_name: str, use_uv: bool = True) -> bool:
        """安装依赖组"""
        if group_name not in self.dependency_groups:
            print(f"❌ 未知的依赖组: {group_name}")
            return False
        
        group = self.dependency_groups[group_name]
        console = self._get_rich_console()
        
        console.print(f"📦 正在安装 {group.name}: {group.description}")
        
        # 检查系统要求
        for req in group.system_requirements:
            if req == "ffmpeg" and not self.system_info.has_ffmpeg:
                console.print(f"⚠️  {group.name} 需要 FFmpeg")
            elif req == "cuda" and not self.system_info.hardware.has_nvidia_gpu:
                console.print(f"⚠️  {group.name} 需要 NVIDIA GPU")
        
        # Special pre-installation for av on Windows using pip
        # This works around the issue where av doesn't have wheels for Python 3.12 on PyPI
        if (group_name == "whisper" and 
            self.system_info.system_type == SystemType.WINDOWS):
            console.print("  🔧 Pre-installing av package with pip (works better on Windows)...")
            try:
                pip_cmd = [sys.executable, "-m", "pip", "install", "av"]
                result = subprocess.run(pip_cmd, capture_output=True, text=True,
                                      encoding='utf-8', errors='ignore', timeout=300)
                if result.returncode == 0:
                    console.print("  ✅ av pre-installed successfully")
                else:
                    console.print("  ⚠️  av pre-installation failed, will try with uv")
            except Exception as e:
                console.print(f"  ⚠️  av pre-installation error: {str(e)}")
        
        # 安装包
        success_count = 0
        total_count = len(group.packages)
        
        for package in group.packages:
            try:
                # Skip av if we pre-installed it
                is_av_package = package.startswith("av>=") or package.startswith("av==") or package == "av"
                if (is_av_package and group_name == "whisper" and 
                    self.system_info.system_type == SystemType.WINDOWS):
                    console.print(f"  ⏩ Skipping {package} (already pre-installed)")
                    success_count += 1
                    continue
                
                if use_uv:
                    cmd = ["uv", "pip", "install", "--python", sys.executable, package]
                else:
                    cmd = [sys.executable, "-m", "pip", "install", package]
                
                # 特殊处理PyTorch
                if "torch" in package and "index-url" not in package:
                    if group_name == "pytorch_cuda":
                        cmd.extend(["--index-url", "https://download.pytorch.org/whl/cu118"])
                
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      encoding='utf-8', errors='ignore', timeout=600)
                
                if result.returncode == 0:
                    success_count += 1
                    print(f"  ✅ {package}")
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    print(f"  ❌ {package}: {error_msg}")
                    
            except subprocess.TimeoutExpired:
                print(f"  ⏱️  {package}: 安装超时")
            except Exception as e:
                print(f"  ❌ {package}: {str(e)}")
        
        success_rate = success_count / total_count
        if success_rate >= 0.8:
            console.print(f"✅ {group.name} 安装完成 ({success_count}/{total_count})")
            return True
        else:
            console.print(f"⚠️  {group.name} 部分安装失败 ({success_count}/{total_count})")
            return False
    
    def run_installation(self, mode: InstallationMode = InstallationMode.STANDARD):
        """运行安装流程"""
        console = self._get_rich_console()
        
        # 显示欢迎信息
        console.print(self.Panel(ascii_logo, box=self.DOUBLE, 
                                title="[bold green]VideoLingo Modern Installer[/bold green]", 
                                border_style="bright_blue"))
        
        # 检测系统
        self.detect_system_info()
        self.display_system_info()
        
        # 获取建议
        recommended_mode, recommendations = self.get_installation_recommendations()
        
        if recommendations:
            console.print(self.Panel("\n".join(recommendations), 
                                   title="💡 安装建议", style="cyan"))
        
        # 选择安装模式
        try:
            from InquirerPy import inquirer
            
            mode_choices = {
                "最小化安装 (核心功能)": InstallationMode.MINIMAL,
                "标准安装 (推荐)": InstallationMode.STANDARD,
                "完整安装 (包含所有功能)": InstallationMode.FULL,
                "开发者模式": InstallationMode.DEVELOPMENT,
            }
            
            default_choice = list(mode_choices.keys())[1]  # 标准安装
            if recommended_mode == InstallationMode.MINIMAL:
                default_choice = list(mode_choices.keys())[0]
            elif recommended_mode == InstallationMode.FULL:
                default_choice = list(mode_choices.keys())[2]
            
            selected_mode_name = inquirer.select(
                message="请选择安装模式:",
                choices=list(mode_choices.keys()),
                default=default_choice
            ).execute()
            
            mode = mode_choices[selected_mode_name]
            
        except ImportError:
            mode = recommended_mode
        
        console.print(f"🎯 选择的安装模式: {mode.value}")
        
        # 检查并安装UV
        if not self.check_and_install_uv():
            console.print("⚠️  UV安装失败，将使用pip作为备用方案")
            use_uv = False
        else:
            use_uv = True
        
        # 安装系统依赖
        if not self.install_system_dependencies():
            return False
        
        # 确定要安装的依赖组
        # ----------------------------------------------------------------------------
        # MINIMAL: 核心 + 媒体 + ML基础 + Web界面 + PyTorch (仅基础功能)
        # STANDARD: MINIMAL + NLP + WhisperX + TTS (推荐，包含完整视频翻译功能)
        # FULL: STANDARD + Demucs人声分离 (完整功能)
        # DEVELOPMENT: FULL (开发者模式)
        # ----------------------------------------------------------------------------
        groups_to_install = ["core", "media", "ml_core"]
        
        # 根据模式添加组
        if mode == InstallationMode.MINIMAL:
            groups_to_install.extend(["web"])
            # 最小化安装也需要PyTorch
            if self.system_info.hardware.has_nvidia_gpu:
                groups_to_install.append("pytorch_cuda")
            else:
                groups_to_install.append("pytorch_cpu")
        elif mode == InstallationMode.STANDARD:
            groups_to_install.extend(["nlp", "whisper", "tts", "web"])
            # 根据GPU选择PyTorch版本
            if self.system_info.hardware.has_nvidia_gpu:
                groups_to_install.append("pytorch_cuda")
            else:
                groups_to_install.append("pytorch_cpu")
        elif mode == InstallationMode.FULL:
            groups_to_install.extend(["nlp", "whisper", "tts", "demucs", "web"])
            if self.system_info.hardware.has_nvidia_gpu:
                groups_to_install.append("pytorch_cuda")
            else:
                groups_to_install.append("pytorch_cpu")
        elif mode == InstallationMode.DEVELOPMENT:
            groups_to_install.extend(["nlp", "whisper", "tts", "demucs", "web"])
            groups_to_install.append("pytorch_cuda" if self.system_info.hardware.has_nvidia_gpu else "pytorch_cpu")
        
        # 按顺序安装依赖组
        sorted_group_items = sorted([(name, self.dependency_groups[name]) for name in groups_to_install], 
                                   key=lambda x: x[1].install_order)
        
        total_groups = len(sorted_group_items)
        successful_groups = 0
        
        for i, (group_key, group) in enumerate(sorted_group_items, 1):
            console.print(f"\n📦 [{i}/{total_groups}] 安装 {group.name}...")
            
            if self.install_dependency_group(group_key, use_uv):
                successful_groups += 1
        
        # 安装结果
        console.print(f"\n🎉 安装完成! ({successful_groups}/{total_groups} 个组安装成功)")
        
        if successful_groups == total_groups:
            console.print(self.Panel(
                "✅ 所有依赖安装成功!\n\n"
                "现在可以运行: [bold cyan]streamlit run st.py[/bold cyan]\n"
                "首次启动可能需要1-2分钟下载模型文件",
                title="🎊 安装完成", style="bold green"
            ))
        else:
            console.print(self.Panel(
                f"⚠️  部分依赖安装失败 ({total_groups - successful_groups} 个组)\n\n"
                "你可以稍后手动安装失败的依赖\n"
                "或重新运行此安装程序",
                title="安装警告", style="yellow"
            ))
        
        return successful_groups > 0


def main():
    """主函数"""
    installer = ModernInstaller()
    
    try:
        installer.run_installation()
    except KeyboardInterrupt:
        print("\n❌ 安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 安装过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 