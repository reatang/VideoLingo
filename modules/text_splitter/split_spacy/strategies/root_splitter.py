"""
Strategy for splitting long sentences based on root analysis
"""

import spacy
from typing import List
from rich import print as rprint
from spacy.tokens import Doc

from .base_splitter import BaseSplitter

class RootSplitter(BaseSplitter):
    """
    Split long sentences based on root dependencies and other heuristics
    """

    def split_text(self, text: str, nlp: spacy.Language) -> List[str]:
        """
        Split a long sentence if it exceeds a certain length.
        
        Args:
            text: input text to split
            nlp: spaCy language model
            
        Returns:
            List[str]: list of split sentences, or original sentence in a list
        """
        doc = nlp(text)
        
        if len(doc) <= self.config.max_sentence_length:
            return [text]

        rprint(f"[yellow]✂️  Splitting long sentence by root: {text[:30]}...[/yellow]")
        
        # First pass with DP-based splitting
        split_sentences = self._split_long_sentence(doc, nlp)
        
        # Second pass for sentences that are still too long
        final_sentences = []
        for sent in split_sentences:
            doc_sent = nlp(sent)
            if len(doc_sent) > self.config.max_sentence_length:
                final_sentences.extend(self._split_extremely_long_sentence(doc_sent))
            else:
                final_sentences.append(sent)
        
        return final_sentences

    def _split_long_sentence(self, doc: Doc, nlp: spacy.Language) -> List[str]:
        """
        Optimal splitting using dynamic programming.
        """
        tokens = [token.text for token in doc]
        n = len(tokens)
        dp = [float('inf')] * (n + 1)
        dp[0] = 0
        prev = [0] * (n + 1)
        
        max_len = self.config.max_sentence_length
        min_len = self.config.min_sentence_length

        for i in range(1, n + 1):
            for j in range(max(0, i - (max_len + 20)), i): # Limit search range
                if min_len <= i - j:
                    token = doc[i-1]
                    # Split at sentence ends, verbs, or root dependencies
                    if j == 0 or (token.is_sent_end or token.pos_ in ['VERB', 'AUX'] or token.dep_ == 'ROOT'):
                        if dp[j] + 1 < dp[i]:
                            dp[i] = dp[j] + 1
                            prev[i] = j
        
        sentences = []
        i = n
        joiner = self.config.get_joiner()
        while i > 0:
            j = prev[i]
            if j == i: # Should not happen, but as a safeguard
                i -=1
                continue
            sentences.append(joiner.join(tokens[j:i]).strip())
            i = j
        
        return sentences[::-1] if sentences else [doc.text]

    def _split_extremely_long_sentence(self, doc: Doc) -> List[str]:
        """
        Force split sentences that are still too long after the first pass.
        """
        tokens = [token.text for token in doc]
        n = len(tokens)
        max_len = self.config.max_sentence_length
        
        num_parts = (n + max_len - 1) // max_len
        if num_parts == 0:
             return []
        part_length = n // num_parts
        
        sentences = []
        joiner = self.config.get_joiner()
        for i in range(num_parts):
            start = i * part_length
            end = start + part_length if i < num_parts - 1 else n
            if start < end:
                sentence = joiner.join(tokens[start:end])
                sentences.append(sentence)
        
        return sentences 