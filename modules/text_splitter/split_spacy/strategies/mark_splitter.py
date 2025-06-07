"""
Punctuation mark based text splitting strategy
"""

import os
import pandas as pd
import spacy
from typing import List
from rich import print as rprint

from .base_splitter import BaseSplitter
from ..exceptions import FileProcessingError

class MarkSplitter(BaseSplitter):
    """
    Split text based on punctuation marks using spaCy sentence boundary detection
    """
    
    def split_text(self, text: str, nlp: spacy.Language) -> List[str]:
        """
        Split text by punctuation marks
        
        Args:
            text: input text to split
            nlp: spaCy language model
            
        Returns:
            List[str]: list of sentences split by punctuation
        """
        doc = nlp(text)
        
        # ensure sentence boundary detection is available
        if not doc.has_annotation("SENT_START"):
            rprint("[yellow]⚠️  Warning: Sentence boundary detection not available[/yellow]")
            return [text]
        
        sentences = []
        current_sentence = []
        
        # iterate through all sentences detected by spaCy
        for sent in doc.sents:
            text = sent.text.strip()
            
            # check if current sentence should be merged with previous
            if current_sentence and (
                text.startswith('-') or 
                text.startswith('...') or
                current_sentence[-1].endswith('-') or
                current_sentence[-1].endswith('...')
            ):
                current_sentence.append(text)
            else:
                # save previous sentence if exists
                if current_sentence:
                    joiner = self.config.get_joiner()
                    sentences.append(joiner.join(current_sentence))
                    current_sentence = []
                current_sentence.append(text)
        
        # add the last sentence
        if current_sentence:
            joiner = self.config.get_joiner()
            sentences.append(joiner.join(current_sentence))
        
        return sentences
    
    def _process_file(self, file_path: str, nlp: spacy.Language) -> List[str]:
        """
        Process Excel file and split by punctuation marks
        
        Args:
            file_path: path to input Excel file (cleaned_chunks.xlsx)
            nlp: spaCy language model
            
        Returns:
            List[str]: list of sentences split by punctuation marks
        """
        try:
            # read Excel file
            chunks = pd.read_excel(file_path)
            chunks.text = chunks.text.apply(lambda x: x.strip('"').strip(""))
            
            # join chunks using language-appropriate joiner
            joiner = self.config.get_joiner()
            rprint(f"[blue]🔍 Using {self.config.detected_language} language joiner: '{joiner}'[/blue]")
            
            input_text = joiner.join(chunks.text.to_list())
            
            # split by punctuation marks
            sentences = self.split_text(input_text, nlp)
            
            # save to temporary file
            temp_file = self.config.temp_files["split_by_mark"]
            self._save_with_punctuation_handling(sentences, temp_file)
            
            rprint(f"[green]💾 Sentences split by punctuation marks: {len(sentences)} sentences[/green]")
            return sentences
            
        except Exception as e:
            raise FileProcessingError(f"Failed to process file with mark splitter: {str(e)}")
    
    def _save_with_punctuation_handling(self, sentences: List[str], temp_file: str):
        """
        Save sentences with special punctuation handling for CJK languages
        """
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                for i, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                        
                    # special handling for standalone punctuation
                    if i > 0 and sentence in [',', '.', '，', '。', '？', '！']:
                        # merge punctuation with previous line for CJK languages
                        f.seek(f.tell() - 1, os.SEEK_SET)  # move to end of previous line
                        f.write(sentence)  # add punctuation
                    else:
                        f.write(sentence + "\n")
            
            rprint(f"[blue]💾 Mark splitting result saved to: {temp_file}[/blue]")
            
        except Exception as e:
            raise FileProcessingError(f"Failed to save mark splitting result: {str(e)}") 