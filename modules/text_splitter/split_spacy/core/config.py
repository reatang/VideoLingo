"""
Configuration management for SpaCy text splitter
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
from modules.config import get_global_config

@dataclass
class SplitterConfig:
    """
    Configuration for SpaCy text splitter
    """
    # ------------
    # Language settings
    # ------------
    language: str = "auto"
    detected_language: str = "en"
    
    # ------------
    # Model settings
    # ------------
    spacy_model_map: Dict[str, str] = field(default_factory=dict)
    
    # ------------
    # Splitting parameters
    # ------------
    context_words: int = 5  # context words for connector splitting
    min_phrase_length: int = 3  # minimum phrase length for comma splitting
    max_sentence_length: int = 60  # maximum sentence length before root splitting
    min_sentence_length: int = 30  # minimum sentence length for root splitting
    
    # ------------
    # File paths
    # ------------
    output_dir: str = "output"
    input_file: str = "log/cleaned_chunks.xlsx"
    output_file: str = "log/split_text.txt"
    temp_file_prefix: str = "__"
    
    # ------------
    # Processing options
    # ------------
    enable_comma_split: bool = True
    enable_connector_split: bool = True
    enable_mark_split: bool = True
    enable_root_split: bool = True
    auto_cleanup: bool = True
    
    def __post_init__(self):
        """Post initialization processing"""
        config_manager = get_global_config()

        # create output directory if not exists
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "log"), exist_ok=True)
        
        # set detected language if auto, load from global config
        if self.language == "auto":
            whisper_language = config_manager.load_key("whisper.language", "auto")
            # Follow the logic from old code
            if whisper_language == "en":
                 self.detected_language = "en"
            else:
                self.detected_language = config_manager.load_key("whisper.detected_language", "en")
        else:
            self.detected_language = self.language

        # Load spacy model map from global config
        if not self.spacy_model_map:
            self.spacy_model_map = config_manager.load_key("spacy_model_map", {
                "en": "en_core_web_md",
                "zh": "zh_core_web_md", 
                "ja": "ja_core_news_md",
                "fr": "fr_core_news_md",
                "ru": "ru_core_news_md",
                "es": "es_core_news_md",
                "de": "de_core_news_md",
                "it": "it_core_news_md"
            })
    
    def get_model_name(self) -> str:
        """Get spaCy model name for current language"""
        model = self.spacy_model_map.get(self.detected_language.lower(), "en_core_web_md")
        return model
    
    def get_temp_file_path(self, filename: str) -> str:
        """Get temporary file path with prefix"""
        return os.path.join(self.output_dir, f"{self.temp_file_prefix}{filename}")
    
    def get_joiner(self) -> str:
        """Get text joiner based on language"""
        if self.detected_language in ["zh", "ja"]:
            return ""
        else:
            return " "
    
    @property
    def temp_files(self) -> Dict[str, str]:
        """Get all temporary file paths"""
        return {
            "split_by_mark": self.get_temp_file_path("split_by_mark.txt"),
            "split_by_comma": self.get_temp_file_path("split_by_comma.txt"), 
            "split_by_connector": self.get_temp_file_path("split_by_connector.txt"),
        } 