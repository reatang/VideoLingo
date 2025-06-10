"""
# ----------------------------------------------------------------------------
# 日志模块
# 
# 提供统一的日志配置和管理功能
# 支持控制台输出、文件输出、颜色显示等功能
# ----------------------------------------------------------------------------
"""

import os
import sys
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path
from logging.handlers import RotatingFileHandler
import threading

# 全局日志配置
_loggers: Dict[str, logging.Logger] = {}
_lock = threading.Lock()
_default_level = logging.INFO
_log_directory = "logs"
_console_handler: Optional[logging.Handler] = None
_file_handler: Optional[logging.Handler] = None


def setup_logger(
    name: str, 
    level: Optional[int] = None,
    log_file: Optional[str] = None,
    console: bool = True,
    file_logging: bool = True
) -> logging.Logger:
    """
    设置并获取日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件名
        console: 是否输出到控制台
        file_logging: 是否输出到文件
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    with _lock:
        # 如果已存在，直接返回
        if name in _loggers:
            return _loggers[name]
        
        # 创建日志记录器
        logger = logging.getLogger(name)
        logger.setLevel(level or _default_level)
        
        # 清除已有的处理器
        logger.handlers.clear()
        
        # 添加控制台处理器
        if console:
            console_handler = _get_console_handler()
            logger.addHandler(console_handler)
        
        # 添加文件处理器
        if file_logging:
            file_handler = _get_file_handler(log_file)
            logger.addHandler(file_handler)
        
        # 阻止日志传播到根日志记录器
        logger.propagate = False
        
        _loggers[name] = logger
        return logger


def _get_console_handler() -> logging.Handler:
    """获取控制台处理器"""
    global _console_handler
    
    if _console_handler is None:
        _console_handler = logging.StreamHandler(sys.stdout)
        
        # 控制台格式化器
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        _console_handler.setFormatter(console_formatter)
        _console_handler.setLevel(logging.DEBUG)
    
    return _console_handler


def _get_file_handler(log_file: Optional[str] = None) -> logging.Handler:
    """获取文件处理器"""
    global _file_handler
    
    if _file_handler is None:
        # 确保日志目录存在
        os.makedirs(_log_directory, exist_ok=True)
        
        # 默认日志文件名
        if log_file is None:
            log_file = f"videolingo_{time.strftime('%Y%m%d')}.log"
        
        log_path = os.path.join(_log_directory, log_file)
        
        # 创建轮转文件处理器
        _file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # 文件格式化器
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        _file_handler.setFormatter(file_formatter)
        _file_handler.setLevel(logging.DEBUG)
    
    return _file_handler


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'
    
    def __init__(self, fmt: str, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        self.use_colors = self._should_use_colors()
    
    def _should_use_colors(self) -> bool:
        """检查是否应该使用颜色"""
        # Windows CMD/PowerShell支持检查
        if os.name == 'nt':
            try:
                import colorama
                colorama.init()
                return True
            except ImportError:
                return False
        
        # Unix/Linux系统检查
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.use_colors and record.levelname in self.COLORS:
            # 添加颜色
            color = self.COLORS[record.levelname]
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            
            # 为消息添加颜色
            original_msg = record.getMessage()
            record.msg = f"{color}{original_msg}{self.RESET}"
            record.args = ()
        
        return super().format(record)


def set_global_level(level: int) -> None:
    """
    设置全局日志级别
    
    Args:
        level: 日志级别 (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    global _default_level
    _default_level = level
    
    # 更新所有已存在的日志记录器
    with _lock:
        for logger in _loggers.values():
            logger.setLevel(level)


def set_log_directory(directory: str) -> None:
    """
    设置日志文件目录
    
    Args:
        directory: 日志目录路径
    """
    global _log_directory, _file_handler
    _log_directory = directory
    
    # 重置文件处理器，使其使用新目录
    _file_handler = None


def enable_debug_logging() -> None:
    """启用调试日志"""
    set_global_level(logging.DEBUG)


def disable_file_logging() -> None:
    """禁用文件日志"""
    global _file_handler
    with _lock:
        if _file_handler:
            for logger in _loggers.values():
                if _file_handler in logger.handlers:
                    logger.removeHandler(_file_handler)
        _file_handler = None


def disable_console_logging() -> None:
    """禁用控制台日志"""
    global _console_handler
    with _lock:
        if _console_handler:
            for logger in _loggers.values():
                if _console_handler in logger.handlers:
                    logger.removeHandler(_console_handler)
        _console_handler = None


def get_logger_stats() -> Dict[str, Any]:
    """
    获取日志统计信息
    
    Returns:
        Dict: 包含日志统计信息的字典
    """
    with _lock:
        return {
            'total_loggers': len(_loggers),
            'logger_names': list(_loggers.keys()),
            'global_level': logging.getLevelName(_default_level),
            'log_directory': _log_directory,
            'console_enabled': _console_handler is not None,
            'file_enabled': _file_handler is not None
        }


def cleanup_loggers() -> None:
    """清理所有日志记录器"""
    global _loggers, _console_handler, _file_handler
    
    with _lock:
        # 关闭所有处理器
        for logger in _loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        # 清理全局处理器
        if _console_handler:
            _console_handler.close()
            _console_handler = None
            
        if _file_handler:
            _file_handler.close()
            _file_handler = None
        
        # 清空日志记录器字典
        _loggers.clear()


# 便捷函数
def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return setup_logger(name)


def log_function_call(func):
    """装饰器：记录函数调用"""
    def wrapper(*args, **kwargs):
        logger = setup_logger(func.__module__)
        logger.debug(f"调用函数: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
            raise
    return wrapper


# 初始化默认日志配置
_default_logger = setup_logger(__name__)

# 导出主要接口
__all__ = [
    'setup_logger',
    'get_logger', 
    'set_global_level',
    'set_log_directory',
    'enable_debug_logging',
    'disable_file_logging',
    'disable_console_logging',
    'get_logger_stats',
    'cleanup_loggers',
    'log_function_call',
    'ColoredFormatter'
] 