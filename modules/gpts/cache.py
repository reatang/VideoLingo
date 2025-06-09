"""
# ----------------------------------------------------------------------------
# GPT缓存管理
# 
# 负责GPT请求和响应的缓存管理，提高效率，避免重复调用
# ----------------------------------------------------------------------------
"""

import os
import json
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any

from .models import GPTRequest, GPTResponse


class GPTCache:
    """GPT缓存管理器"""
    
    def __init__(self, cache_dir: str = 'output/gpt_log'):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        
        print(f"✅ GPT缓存初始化完成: {self.cache_dir}")
    
    def get(self, request: GPTRequest) -> Optional[GPTResponse]:
        """
        获取缓存的响应
        
        Args:
            request: GPT请求
            
        Returns:
            缓存的响应，如果不存在则返回None
        """
        with self._lock:
            cache_file = self.cache_dir / f"{request.log_title}.json"
            
            if not cache_file.exists():
                return None
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 查找匹配的缓存项
                for item in cache_data:
                    if (item.get("prompt") == request.prompt and 
                        item.get("resp_type") == request.response_type):
                        
                        # 重建响应对象
                        response = GPTResponse(
                            content=item.get("resp"),
                            raw_content=item.get("resp_content", ""),
                            request=request,
                            model=item.get("model", "unknown")
                        )
                        return response
                        
            except Exception as e:
                print(f"⚠️  读取缓存失败: {str(e)}")
            
            return None
    
    def save(self, request: GPTRequest, response: GPTResponse) -> None:
        """
        保存响应到缓存
        
        Args:
            request: GPT请求
            response: GPT响应
        """
        with self._lock:
            cache_file = self.cache_dir / f"{request.log_title}.json"
            
            # 读取现有缓存
            cache_data = []
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                except Exception:
                    cache_data = []
            
            # 添加新项
            cache_item = {
                "model": response.model,
                "prompt": request.prompt,
                "resp_content": response.raw_content,
                "resp_type": request.response_type,
                "resp": response.content,
                "message": None
            }
            cache_data.append(cache_item)
            
            # 保存缓存
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"⚠️  保存缓存失败: {str(e)}")
    
    def save_error(self, request: GPTRequest, response: GPTResponse, error_message: str) -> None:
        """
        保存错误响应到缓存
        
        Args:
            request: GPT请求
            response: GPT响应
            error_message: 错误消息
        """
        with self._lock:
            error_file = self.cache_dir / "error.json"
            
            # 读取现有错误缓存
            error_data = []
            if error_file.exists():
                try:
                    with open(error_file, 'r', encoding='utf-8') as f:
                        error_data = json.load(f)
                except Exception:
                    error_data = []
            
            # 添加错误项
            error_item = {
                "model": response.model,
                "prompt": request.prompt,
                "resp_content": response.raw_content,
                "resp_type": request.response_type,
                "resp": response.content,
                "message": error_message,
                "log_title": request.log_title
            }
            error_data.append(error_item)
            
            # 保存错误缓存
            try:
                with open(error_file, 'w', encoding='utf-8') as f:
                    json.dump(error_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"⚠️  保存错误缓存失败: {str(e)}")
    
    def clear(self, log_title: Optional[str] = None) -> None:
        """
        清除缓存
        
        Args:
            log_title: 特定的日志标题，如果为None则清除所有缓存
        """
        with self._lock:
            if log_title:
                cache_file = self.cache_dir / f"{log_title}.json"
                if cache_file.exists():
                    cache_file.unlink()
                    print(f"🗑️  已清除缓存: {log_title}")
            else:
                # 清除所有JSON缓存文件
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
                print(f"🗑️  已清除所有缓存")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        stats = {
            'total_files': 0,
            'total_entries': 0,
            'cache_size_mb': 0.0,
            'log_titles': []
        }
        
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            stats['total_files'] = len(cache_files)
            
            total_size = 0
            for cache_file in cache_files:
                total_size += cache_file.stat().st_size
                
                if cache_file.name != 'error.json':
                    stats['log_titles'].append(cache_file.stem)
                    
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            stats['total_entries'] += len(data)
                    except Exception:
                        pass
            
            stats['cache_size_mb'] = round(total_size / (1024 * 1024), 2)
            
        except Exception as e:
            print(f"⚠️  获取缓存统计失败: {str(e)}")
        
        return stats 