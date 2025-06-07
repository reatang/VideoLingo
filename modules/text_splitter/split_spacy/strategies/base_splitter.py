"""
Base class for text splitting strategies
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Union
from pathlib import Path
import spacy
from rich import print as rprint

from ..core.config import SplitterConfig

class BaseSplitter(ABC):
    """
    Abstract base class for text splitting strategies
    """
    
    def __init__(self, config: SplitterConfig):
        self.config = config
    
    @abstractmethod
    def split_text(self, text: str, nlp: spacy.Language) -> List[str]:
        """
        Split a single text into multiple parts
        
        Args:
            text: input text to split
            nlp: spaCy language model
            
        Returns:
            List[str]: list of split text parts
        """
        pass
    
    def process(self, input_data: Union[str, List[str]], nlp: spacy.Language) -> Union[List[str], Tuple[List[str], int]]:
        """
        Process input data (can be file path or list of sentences)
        
        Args:
            input_data: input file path or list of sentences
            nlp: spaCy language model
            
        Returns:
            List[str] or Tuple[List[str], int]: processed sentences, optionally with split count
        """
        if isinstance(input_data, str) or isinstance(input_data, Path):
            # input is file path
            return self._process_file(input_data, nlp)
        else:
            # input is list of sentences
            return self._process_sentences(input_data, nlp)
    
    def _process_file(self, file_path: str, nlp: spacy.Language) -> List[str]:
        """Process input file - to be implemented by subclasses if needed"""
        raise NotImplementedError("File processing not implemented for this splitter")
    
    def _process_sentences(self, sentences: List[str], nlp: spacy.Language) -> Tuple[List[str], int]:
        """
        Process list of sentences
        
        Args:
            sentences: list of input sentences
            nlp: spaCy language model
            
        Returns:
            Tuple[List[str], int]: (processed sentences, number of split operations)
        """
        all_sentences = []
        split_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            split_sentences = self.split_text(sentence, nlp)
            all_sentences.extend(split_sentences)
            
            # count split operations (splits that resulted in more than 1 part)
            if len(split_sentences) > 1:
                split_count += len(split_sentences) - 1
        
        return all_sentences, split_count
    
    def save_temp_result(self, sentences: List[str], temp_file: str):
        """Save intermediate results to temporary file"""
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                for sentence in sentences:
                    if sentence.strip():
                        f.write(sentence.strip() + "\n")
            
            rprint(f"[blue]💾 Intermediate result saved to: {temp_file}[/blue]")
            
        except Exception as e:
            rprint(f"[yellow]⚠️  Failed to save temp result: {str(e)}[/yellow]") 