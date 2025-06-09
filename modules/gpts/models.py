"""
# ----------------------------------------------------------------------------
# GPT数据模型
# 
# 定义GPT调用相关的数据结构和模型
# ----------------------------------------------------------------------------
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
import time


@dataclass
class GPTRequest:
    """GPT请求数据模型"""
    prompt: str
    response_type: Optional[str] = None  # 'json' or None
    validator: Optional[Callable] = None
    log_title: str = "default"
    timeout: int = 300
    extra_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_cache_key(self) -> str:
        """生成缓存键"""
        import hashlib
        key_data = f"{self.prompt}:{self.response_type}:{self.log_title}"
        return hashlib.md5(key_data.encode()).hexdigest()


@dataclass 
class GPTResponse:
    """GPT响应数据模型"""
    content: Any  # 解析后的内容
    raw_content: str  # 原始响应内容
    request: GPTRequest
    model: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'content': self.content,
            'raw_content': self.raw_content,
            'model': self.model,
            'timestamp': self.timestamp,
            'request': {
                'prompt': self.request.prompt,
                'response_type': self.request.response_type,
                'log_title': self.request.log_title
            }
        }


@dataclass
class GPTUsageStats:
    """GPT使用统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    total_tokens: int = 0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests 