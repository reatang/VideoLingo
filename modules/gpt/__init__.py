"""
# ----------------------------------------------------------------------------
# GPT调用模块
# 
# 提供统一的GPT API调用接口，支持：
# 1. 多种API提供商（OpenAI、DeepSeek、SiliconFlow等）
# 2. 响应格式验证和处理
# 3. 缓存机制
# 4. 错误处理和重试
# 5. 配置集成
# ----------------------------------------------------------------------------
"""

from .client import GPTClient, create_gpt_client
from .cache import GPTCache
from .models import GPTRequest, GPTResponse
from .exceptions import GPTError, GPTTimeoutError, GPTValidationError

# 导出主要API
__all__ = [
    'GPTClient',
    'create_gpt_client',
    'GPTCache',
    'GPTRequest',
    'GPTResponse',
    'GPTError',
    'GPTTimeoutError',
    'GPTValidationError',
    'ask_gpt',
    'cleanup_global_client'
]

# 全局客户端实例
_global_client = None

def get_global_client(**kwargs) -> GPTClient:
    """获取全局GPT客户端实例"""
    global _global_client
    if _global_client is None:
        _global_client = create_gpt_client(**kwargs)
    return _global_client

def cleanup_global_client():
    """清理全局GPT客户端"""
    global _global_client
    if _global_client is not None:
        try:
            _global_client._client.close()
        except Exception as e:
            print(f"⚠️  清理全局GPT客户端时出错: {e}")
        finally:
            _global_client = None

def ask_gpt(prompt: str, 
           resp_type: str = None,
           valid_def: callable = None,
           log_title: str = "default",
           **kwargs) -> any:
    """
    便捷的GPT调用函数，保持与原有接口兼容
    
    Args:
        prompt: 提示词
        resp_type: 响应类型 ('json' 或 None)
        valid_def: 验证函数
        log_title: 日志标题
        **kwargs: 其他参数
        
    Returns:
        GPT响应结果
    """
    client_kwargs = {}
    if kwargs.get('cache_dir'):
        client_kwargs['cache_dir'] = kwargs['cache_dir']
    client = get_global_client(**client_kwargs)

    request_kwargs = {}
    if kwargs.get('extra_params'):
        request_kwargs['extra_params'] = kwargs['extra_params']
    request = GPTRequest(
        prompt=prompt,
        response_type=resp_type,
        validator=valid_def,
        log_title=log_title,
        **request_kwargs
    )
    
    response = client.complete(request)
    return response.content 