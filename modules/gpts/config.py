from dataclasses import dataclass, field
from modules.configs import get_global_config

@dataclass
class GPTConfig:
    """
    GPT 配置类
    """

    # ------------
    # 模型名称
    # ------------
    model_name: str = field(default="")

    # ------------
    # 平台key  
    # ------------
    api_key: str = field(default="")

    # ------------
    # 平台url 
    # ------------
    base_url: str = field(default="")


    # ------------
    # 是否原生支持JSON
    # ------------
    llm_support_json: bool = False

    # ------------
    # 缓存目录
    # ------------
    cache_dir: str = field(default="output/gpt_log")

    def __post_init__(self):
        config_manager = get_global_config()

        # 从全局配置中获取配置
        if not self.model_name:
            self.model_name = config_manager.load_key("api.model", "")
        if not self.api_key:
            self.api_key = config_manager.load_key("api.key", "")
        if not self.base_url:
            self.base_url = config_manager.load_key("api.base_url", "")
        if not self.llm_support_json:
            self.llm_support_json = config_manager.load_key("api.llm_support_json", False)
        if not self.cache_dir:
            self.cache_dir = config_manager.load_key("api.cache_dir", "output/gpt_log")


    def get_config(self):
        return {
            "model_name": self.model_name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "llm_support_json": self.llm_support_json,
            "cache_dir": self.cache_dir
        }

