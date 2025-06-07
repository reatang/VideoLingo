"""
Comma-based text splitting strategy
"""

import itertools
import spacy
from typing import List
from rich import print as rprint
from spacy.tokens import Doc, Token, Span

from .base_splitter import BaseSplitter

class CommaSplitter(BaseSplitter):
    """
    Split text based on comma positions with grammatical analysis
    """
    
    def split_text(self, text: str, nlp: spacy.Language) -> List[str]:
        """
        Split text by commas with grammatical validation
        
        Args:
            text: input text to split
            nlp: spaCy language model
            
        Returns:
            List[str]: list of sentences split by commas
        """
        doc = nlp(text)
        sentences = []
        start = 0
        
        for i, token in enumerate(doc):
            if token.text == "," or token.text == "，":
                suitable_for_splitting = self._analyze_comma(start, doc, token)
                
                if suitable_for_splitting:
                    sentence = doc[start:token.i].text.strip()
                    sentences.append(sentence)
                    rprint(f"[yellow]✂️  Split at comma: {doc[start:token.i][-4:]},| {doc[token.i + 1:][:4]}[/yellow]")
                    start = token.i + 1
        
        # add remaining text
        if start < len(doc):
            sentences.append(doc[start:].text.strip())
        
        return sentences if len(sentences) > 1 else [text]
    
    def _analyze_comma(self, start: int, doc: Doc, token: Token) -> bool:
        """
        Analyze whether a comma should trigger splitting
        
        Args:
            start: start position of current segment
            doc: spaCy document
            token: comma token
            
        Returns:
            bool: whether the comma is suitable for splitting
        """
        # get phrases around the comma
        left_phrase = doc[max(start, token.i - 9):token.i]
        right_phrase = doc[token.i + 1:min(len(doc), token.i + 10)]
        
        # check if right phrase has valid grammatical structure
        suitable_for_splitting = self._is_valid_phrase(right_phrase)
        
        # remove punctuation and check word count
        left_words = [t for t in left_phrase if not t.is_punct]
        right_words = list(itertools.takewhile(lambda t: not t.is_punct, right_phrase))
        
        # ensure minimum phrase length
        if len(left_words) <= self.config.min_phrase_length or len(right_words) <= self.config.min_phrase_length:
            suitable_for_splitting = False
        
        return suitable_for_splitting
    
    def _is_valid_phrase(self, phrase: Span) -> bool:
        """
        Check if a phrase has valid grammatical structure (subject and verb)
        
        Args:
            phrase: spaCy span to analyze
            
        Returns:
            bool: whether the phrase has valid structure
        """
        has_subject = any(token.dep_ in ["nsubj", "nsubjpass"] or token.pos_ == "PRON" for token in phrase)
        has_verb = any((token.pos_ == "VERB" or token.pos_ == 'AUX') for token in phrase)
        return has_subject and has_verb 