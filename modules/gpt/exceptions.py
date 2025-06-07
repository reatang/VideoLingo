"""
# ----------------------------------------------------------------------------
# GPT异常类定义
# 
# 定义GPT调用过程中可能出现的各种异常类型
# ----------------------------------------------------------------------------
"""


class GPTError(Exception):
    """GPT调用基础异常"""
    pass


class GPTTimeoutError(GPTError):
    """GPT调用超时异常"""
    pass


class GPTValidationError(GPTError):
    """GPT响应验证失败异常"""
    pass


class GPTConfigError(GPTError):
    """GPT配置错误异常"""
    pass


class GPTCacheError(GPTError):
    """GPT缓存错误异常"""
    pass 