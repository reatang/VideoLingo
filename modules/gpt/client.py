"""
# ----------------------------------------------------------------------------
# GPT客户端核心实现
# 
# 基于原有ask_gpt逻辑重构的现代化GPT客户端
# 支持多种API提供商、配置管理、缓存等功能
# ----------------------------------------------------------------------------
"""

import os
import json
import json_repair
from typing import Optional, Dict, Any
from openai import OpenAI

from .models import GPTRequest, GPTResponse
from .cache import GPTCache
from .exceptions import GPTError, GPTTimeoutError, GPTValidationError


class GPTClient:
    """现代化的GPT客户端类"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 llm_support_json: bool = False,
                 cache_dir: str = 'output/gpt_log',
                 config_manager=None):
        """
        初始化GPT客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            llm_support_json: 是否支持JSON模式
            cache_dir: 缓存目录
            config_manager: 配置管理器
        """
        self._config_manager = config_manager
        self._init_from_config(api_key, base_url, model, llm_support_json)
        
        # 初始化OpenAI客户端
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self._normalize_base_url(self.base_url)
        )
        
        # 初始化缓存
        self.cache = GPTCache(cache_dir)
        
        print(f"✅ GPT客户端初始化完成")
        print(f"   模型: {self.model}")
        print(f"   基础URL: {self.base_url}")
        print(f"   JSON支持: {self.llm_support_json}")
    
    def _init_from_config(self, api_key, base_url, model, llm_support_json):
        """从配置初始化参数"""
        if self._config_manager:
            try:
                api_config = self._config_manager.get_api_config()
                self.api_key = api_key or api_config.get('key', '')
                self.base_url = base_url or api_config.get('base_url', 'https://api.siliconflow.cn')
                self.model = model or api_config.get('model', 'deepseek-ai/DeepSeek-V3')
                self.llm_support_json = llm_support_json if llm_support_json is not None else api_config.get('llm_support_json', False)
            except Exception:
                # 使用默认值
                self.api_key = api_key or ''
                self.base_url = base_url or 'https://api.siliconflow.cn'
                self.model = model or 'deepseek-ai/DeepSeek-V3'
                self.llm_support_json = llm_support_json or False
        else:
            # 尝试从环境变量或使用默认值
            self.api_key = api_key or os.getenv('OPENAI_API_KEY', '')
            self.base_url = base_url or 'https://api.siliconflow.cn'
            self.model = model or 'deepseek-ai/DeepSeek-V3'
            self.llm_support_json = llm_support_json or False
        
        if not self.api_key:
            raise GPTError("API key is not set")
    
    def _normalize_base_url(self, base_url: str) -> str:
        """标准化基础URL"""
        if 'ark' in base_url:
            return "https://ark.cn-beijing.volces.com/api/v3"
        elif 'v1' not in base_url:
            return base_url.strip('/') + '/v1'
        return base_url
    
    def complete(self, request: GPTRequest) -> GPTResponse:
        """
        执行GPT补全请求
        
        Args:
            request: GPT请求对象
            
        Returns:
            GPT响应对象
        """
        # 检查缓存
        cached_response = self.cache.get(request)
        if cached_response:
            print("🔄 使用缓存响应")
            return cached_response
        
        try:
            # 构建请求参数
            messages = [{"role": "user", "content": request.prompt}]
            
            # 设置响应格式
            response_format = None
            if request.response_type == "json" and self.llm_support_json:
                response_format = {"type": "json_object"}
            
            params = {
                "model": self.model,
                "messages": messages,
                "timeout": request.timeout,
                **request.extra_params
            }
            
            if response_format:
                params["response_format"] = response_format
            
            # 发送请求
            resp_raw = self._client.chat.completions.create(**params)
            
            # 处理响应
            resp_content = resp_raw.choices[0].message.content
            
            # 解析JSON响应
            if request.response_type == "json":
                try:
                    parsed_content = json.loads(resp_content)
                except json.JSONDecodeError:
                    # 使用json_repair修复
                    parsed_content = json_repair.loads(resp_content)
            else:
                parsed_content = resp_content
            
            # 创建响应对象
            response = GPTResponse(
                content=parsed_content,
                raw_content=resp_content,
                request=request,
                model=self.model
            )
            
            # 验证响应
            if request.validator:
                validation_result = request.validator(parsed_content)
                if validation_result.get('status') != 'success':
                    self.cache.save_error(request, response, validation_result.get('message', 'Validation failed'))
                    raise GPTValidationError(f"Response validation failed: {validation_result.get('message')}")
            
            # 保存到缓存
            self.cache.save(request, response)
            
            return response
            
        except Exception as e:
            if isinstance(e, (GPTError, GPTValidationError)):
                raise
            else:
                raise GPTError(f"GPT request failed: {str(e)}")


def create_gpt_client(config_manager=None, **kwargs) -> GPTClient:
    """
    创建GPT客户端实例
    
    Args:
        config_manager: 配置管理器
        **kwargs: 其他初始化参数
        
    Returns:
        GPT客户端实例
    """
    if config_manager is None:
        try:
            from ..config import get_config_manager
            config_manager = get_config_manager()
        except ImportError:
            print("⚠️  配置管理器不可用，使用默认配置")
            config_manager = None
    
    return GPTClient(config_manager=config_manager, **kwargs) 