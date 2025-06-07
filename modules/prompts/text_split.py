"""
Prompt generator for text splitting tasks.
"""

from typing import Dict
from .base import PromptGenerator, PromptTemplate

class TextSplitGenerator(PromptGenerator):
    """
    Generates prompts for splitting long sentences.
    """

    def __init__(self, language: str = 'en'):
        self.language = language
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, PromptTemplate]:
        """Loads the templates for this generator."""
        split_template = PromptTemplate(
            name="semantic_split",
            category="text_splitter",
            language=self.language,
            description="Splits a long sentence into multiple parts based on semantic meaning.",
            template="""
## Role
You are a professional Netflix subtitle splitter in **{language}**.

## Task
Split the given subtitle text into **{num_parts}** parts, each less than **{word_limit}** words.

1. Maintain sentence meaning coherence according to Netflix subtitle standards
2. MOST IMPORTANT: Keep parts roughly equal in length (minimum 3 words each)
3. Split at natural points like punctuation marks or conjunctions
4. If provided text is repeated words, simply split at the middle of the repeated words.

## Steps
1. Analyze the sentence structure, complexity, and key splitting challenges
2. Generate two alternative splitting approaches with [br] tags at split positions
3. Compare both approaches highlighting their strengths and weaknesses
4. Choose the best splitting approach

## Given Text
<split_this_sentence>
{sentence}
</split_this_sentence>

## Output in only JSON format and no other text
```json
{{
    "analysis": "Brief description of sentence structure, complexity, and key splitting challenges",
    "split1": "First splitting approach with [br] tags at split positions",
    "split2": "Alternative splitting approach with [br] tags at split positions",
    "assess": "Comparison of both approaches highlighting their strengths and weaknesses",
    "choice": "1 or 2"
}}
```

Note: Start you answer with ```json and end with ```, do not add any other text.
""".strip()
        )
        return {"semantic_split": split_template}

    def get_templates(self) -> Dict[str, PromptTemplate]:
        return self.templates

    def generate(self, template_name: str = "semantic_split", **kwargs) -> str:
        """
        Generates the final prompt string.
        
        Args:
            template_name (str): The name of the template to use.
            **kwargs: Must include 'sentence', 'num_parts', and 'word_limit'.
        
        Returns:
            The formatted prompt.
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found in TextSplitGenerator.")
        
        template = self.templates[template_name]
        
        # Add the generator's language to the formatting arguments
        all_kwargs = {'language': self.language, **kwargs}
        
        return template.format(**all_kwargs) 