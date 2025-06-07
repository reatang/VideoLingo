"""
Exception classes for SpaCy text splitter
"""

class SpacySplitterError(Exception):
    """Base exception class for SpaCy text splitter"""
    
    def __init__(self, message: str, details: str = ""):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}. Details: {self.details}"
        return self.message

class ModelLoadError(SpacySplitterError):
    """Exception raised when spaCy model fails to load"""
    pass

class ConfigurationError(SpacySplitterError):
    """Exception raised for configuration-related errors"""
    pass

class FileProcessingError(SpacySplitterError):
    """Exception raised during file processing"""
    pass

class SplittingError(SpacySplitterError):
    """Exception raised during text splitting operations"""
    pass 