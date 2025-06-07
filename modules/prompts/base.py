"""
# ----------------------------------------------------------------------------
# 提示词管理基础类
# 
# 提供提示词模板的基础框架和管理器
# ----------------------------------------------------------------------------
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class PromptTemplate:
    """提示词模板数据类"""
    name: str
    template: str
    description: str = ""
    language: str = "en"
    category: str = "general"
    variables: Dict[str, str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}
    
    def format(self, **kwargs) -> str:
        """
        格式化提示词模板
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的提示词
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")


class PromptGenerator(ABC):
    """提示词生成器基类"""
    
    @abstractmethod
    def generate(self, **kwargs) -> str:
        """
        生成提示词
        
        Args:
            **kwargs: 生成参数
            
        Returns:
            生成的提示词
        """
        pass
    
    @abstractmethod
    def get_templates(self) -> Dict[str, PromptTemplate]:
        """
        获取所有模板
        
        Returns:
            模板字典
        """
        pass


class PromptManager:
    """提示词管理器"""
    
    def __init__(self):
        """初始化提示词管理器"""
        self.generators: Dict[str, PromptGenerator] = {}
        self.templates: Dict[str, PromptTemplate] = {}
        
        print("✅ 提示词管理器初始化完成")
    
    def register(self, name: str, generator: PromptGenerator) -> None:
        """
        注册提示词生成器
        
        Args:
            name: 生成器名称
            generator: 生成器实例
        """
        self.generators[name] = generator
        
        # 加载生成器的模板
        templates = generator.get_templates()
        for template_name, template in templates.items():
            full_name = f"{name}.{template_name}"
            self.templates[full_name] = template
        
        print(f"✅ 已注册提示词生成器: {name} ({len(templates)} 个模板)")
    
    def get_generator(self, name: str) -> Optional[PromptGenerator]:
        """
        获取提示词生成器
        
        Args:
            name: 生成器名称
            
        Returns:
            生成器实例
        """
        return self.generators.get(name)
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        获取提示词模板
        
        Args:
            name: 模板名称 (格式: generator.template)
            
        Returns:
            模板实例
        """
        return self.templates.get(name)
    
    def generate(self, generator_name: str, **kwargs) -> str:
        """
        生成提示词
        
        Args:
            generator_name: 生成器名称
            **kwargs: 生成参数
            
        Returns:
            生成的提示词
        """
        generator = self.get_generator(generator_name)
        if generator is None:
            raise ValueError(f"Unknown prompt generator: {generator_name}")
        
        return generator.generate(**kwargs)
    
    def list_generators(self) -> Dict[str, Any]:
        """
        列出所有注册的生成器
        
        Returns:
            生成器信息字典
        """
        result = {}
        for name, generator in self.generators.items():
            templates = generator.get_templates()
            result[name] = {
                'class': generator.__class__.__name__,
                'templates': list(templates.keys()),
                'template_count': len(templates)
            }
        return result
    
    def export_templates(self, output_file: str) -> None:
        """
        导出所有模板到JSON文件
        
        Args:
            output_file: 输出文件路径
        """
        templates_data = {}
        for name, template in self.templates.items():
            templates_data[name] = {
                'name': template.name,
                'template': template.template,
                'description': template.description,
                'language': template.language,
                'category': template.category,
                'variables': template.variables
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 已导出 {len(templates_data)} 个模板到: {output_file}")
    
    def load_templates(self, input_file: str) -> None:
        """
        从JSON文件加载模板
        
        Args:
            input_file: 输入文件路径
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            loaded_count = 0
            for name, data in templates_data.items():
                template = PromptTemplate(
                    name=data['name'],
                    template=data['template'],
                    description=data.get('description', ''),
                    language=data.get('language', 'en'),
                    category=data.get('category', 'general'),
                    variables=data.get('variables', {})
                )
                self.templates[name] = template
                loaded_count += 1
            
            print(f"📥 已加载 {loaded_count} 个模板从: {input_file}")
            
        except Exception as e:
            print(f"❌ 加载模板失败: {str(e)}") 