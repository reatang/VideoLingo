"""
Connector-based text splitting strategy
"""

import spacy
from typing import List
from rich import print as rprint
from spacy.tokens import Doc, Token

from .base_splitter import BaseSplitter

class ConnectorSplitter(BaseSplitter):
    """
    Split text based on connector words with grammatical analysis
    """

    def split_text(self, text: str, nlp: spacy.Language) -> List[str]:
        """
        Split text by connectors with grammatical validation.
        This implementation will perform iterative splitting to handle multiple connectors in a sentence.
        
        Args:
            text: input text to split
            nlp: spaCy language model
            
        Returns:
            List[str]: list of sentences split by connectors
        """
        sentences = [text]
        
        while True:
            split_occurred = False
            new_sentences = []
            
            for sent in sentences:
                doc = nlp(sent)
                start = 0
                temp_sent_split = False
                
                for i, token in enumerate(doc):
                    split_before, _ = self._analyze_connector(doc, token)
                    
                    if i + 1 < len(doc) and doc[i + 1].text in ["'s", "'re", "'ve", "'ll", "'d"]:
                        continue
                    
                    left_words = doc[max(0, token.i - self.config.context_words):token.i]
                    right_words = doc[token.i+1:min(len(doc), token.i + self.config.context_words + 1)]
                    
                    left_words_no_punct = [word for word in left_words if not word.is_punct]
                    right_words_no_punct = [word for word in right_words if not word.is_punct]
                    
                    if len(left_words_no_punct) >= self.config.context_words and len(right_words_no_punct) >= self.config.context_words and split_before:
                        rprint(f"[yellow]✂️  Split before '{token.text}': {' '.join(w.text for w in left_words)}| {token.text} {' '.join(w.text for w in right_words)}[/yellow]")
                        new_sentences.append(doc[start:token.i].text.strip())
                        start = token.i
                        split_occurred = True
                        temp_sent_split = True
                        break # Process one split per sentence fragment at a time
                
                if start < len(doc):
                    new_sentences.append(doc[start:].text.strip())

                if temp_sent_split:
                    break # restart the loop with new sentences
            
            sentences = new_sentences

            if not split_occurred:
                break
        
        return [s for s in sentences if s]

    def _analyze_connector(self, doc: Doc, token: Token):
        """
        Analyze whether a token is a connector that should trigger a sentence split.
        """
        lang = self.config.language
        connectors_map = {
            "en": ["that", "which", "where", "when", "because", "but", "and", "or"],
            "zh": ["因为", "所以", "但是", "而且", "虽然", "如果", "即使", "尽管"],
            "ja": ["けれども", "しかし", "だから", "それで", "ので", "のに", "ため"],
            "fr": ["que", "qui", "où", "quand", "parce que", "mais", "et", "ou"],
            "ru": ["что", "который", "где", "когда", "потому что", "но", "и", "или"],
            "es": ["que", "cual", "donde", "cuando", "porque", "pero", "y", "o"],
            "de": ["dass", "welche", "wo", "wann", "weil", "aber", "und", "oder"],
            "it": ["che", "quale", "dove", "quando", "perché", "ma", "e", "o"]
        }
        
        deps_map = {
            "en": {"mark_dep": "mark", "det_pron_deps": ["det", "pron"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "zh": {"mark_dep": "mark", "det_pron_deps": ["det", "pron"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "ja": {"mark_dep": "mark", "det_pron_deps": ["case"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "fr": {"mark_dep": "mark", "det_pron_deps": ["det", "pron"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "ru": {"mark_dep": "mark", "det_pron_deps": ["det"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "es": {"mark_dep": "mark", "det_pron_deps": ["det", "pron"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "de": {"mark_dep": "mark", "det_pron_deps": ["det", "pron"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]},
            "it": {"mark_dep": "mark", "det_pron_deps": ["det", "pron"], "verb_pos": "VERB", "noun_pos": ["NOUN", "PROPN"]}
        }

        connectors = connectors_map.get(lang, [])
        deps = deps_map.get(lang)

        if not connectors or not deps:
            return False, False
        
        if token.text.lower() not in connectors:
            return False, False
        
        if lang == "en" and token.text.lower() == "that":
            if token.dep_ == deps["mark_dep"] and token.head.pos_ == deps["verb_pos"]:
                return True, False
            else:
                return False, False
        elif token.dep_ in deps["det_pron_deps"] and token.head.pos_ in deps["noun_pos"]:
            return False, False
        else:
            return True, False 