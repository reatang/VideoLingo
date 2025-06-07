"""
Runtime management for SpaCy text splitter
"""

import spacy
from spacy.cli import download
from typing import Optional
import warnings
from rich import print as rprint

from .config import SplitterConfig
from ..exceptions import SpacySplitterError

warnings.filterwarnings("ignore", category=FutureWarning)

class SpacyRuntime:
    """
    SpaCy model runtime manager
    
    Manages the lifecycle of spaCy model:
    - Startup phase: load and initialize model
    - Working phase: provide model access 
    - Cleanup phase: release resources
    """
    
    def __init__(self, config: SplitterConfig):
        self.config = config
        self.nlp: Optional[spacy.Language] = None
        self._is_initialized = False
        self._model_name = ""
    
    def startup(self) -> None:
        """
        Startup phase: initialize and load spaCy model
        """
        if self._is_initialized:
            return
        
        try:
            self._model_name = self.config.get_model_name()
            rprint(f"[blue]⏳ Loading NLP spaCy model: <{self._model_name}> ...[/blue]")
            
            # try to load model
            try:
                self.nlp = spacy.load(self._model_name)
            except IOError:
                # model not found, try to download
                rprint(f"[yellow]Model {self._model_name} not found, downloading...[/yellow]")
                rprint("[yellow]If download failed, please check your network and try again.[/yellow]")
                download(self._model_name)
                self.nlp = spacy.load(self._model_name)
            
            # verify model loaded successfully
            if self.nlp is None:
                raise SpacySplitterError(f"Failed to load spaCy model: {self._model_name}")
            
            self._is_initialized = True
            rprint(f"[green]✅ NLP spaCy model loaded successfully! Language: {self.nlp.lang}[/green]")
            
        except Exception as e:
            raise SpacySplitterError(f"Failed to initialize spaCy runtime: {str(e)}")
    
    def get_nlp(self) -> spacy.Language:
        """
        Get spaCy model instance
        
        Returns:
            spacy.Language: the loaded spaCy model
            
        Raises:
            SpacySplitterError: if runtime not initialized
        """
        if not self._is_initialized or self.nlp is None:
            raise SpacySplitterError("SpaCy runtime not initialized. Call startup() first.")
        
        return self.nlp
    
    def cleanup(self) -> None:
        """
        Cleanup phase: release model resources
        """
        if self.nlp is not None:
            # in spaCy, there's no explicit cleanup method
            # just remove reference to help garbage collection  
            self.nlp = None
            
        self._is_initialized = False
        rprint("[blue]🧹 SpaCy runtime cleaned up[/blue]")
    
    @property 
    def is_initialized(self) -> bool:
        """Check if runtime is initialized"""
        return self._is_initialized
    
    @property
    def model_name(self) -> str:
        """Get current model name"""
        return self._model_name
    
    @property
    def language(self) -> str:
        """Get model language"""
        if self.nlp is not None:
            return self.nlp.lang
        return self.config.detected_language
    
    def __enter__(self):
        """Context manager entry"""
        self.startup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup() 