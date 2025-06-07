"""
Result management for SpaCy text splitter
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import time

@dataclass
class SplitStats:
    """Statistics for each splitting step"""
    step_name: str
    input_count: int
    output_count: int
    processing_time: float
    split_operations: int = 0
    
    @property
    def split_ratio(self) -> float:
        """Calculate splitting ratio"""
        if self.input_count == 0:
            return 0.0
        return self.output_count / self.input_count

@dataclass
class SplitResult:
    """
    Complete result of text splitting operation
    """
    # ------------
    # Basic info
    # ------------
    success: bool = True
    total_processing_time: float = 0.0
    input_file: Path = None
    output_file: Path = None
    
    # ------------
    # Statistics for each step
    # ------------
    stats: List[SplitStats] = field(default_factory=list)
    
    # ------------
    # Final results
    # ------------
    final_sentences: List[str] = field(default_factory=list)
    original_text_length: int = 0
    final_sentence_count: int = 0
    
    # ------------
    # Error handling
    # ------------
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def add_step_stats(self, step_name: str, input_count: int, output_count: int, 
                      processing_time: float, split_operations: int = 0):
        """Add statistics for a processing step"""
        stats = SplitStats(
            step_name=step_name,
            input_count=input_count,
            output_count=output_count,
            processing_time=processing_time,
            split_operations=split_operations
        )
        self.stats.append(stats)
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
    
    def set_error(self, error_message: str):
        """Set error state"""
        self.success = False
        self.error_message = error_message
    
    @property
    def total_split_operations(self) -> int:
        """Get total number of split operations"""
        return sum(stat.split_operations for stat in self.stats)
    
    @property
    def final_split_ratio(self) -> float:
        """Get final splitting ratio"""
        if not self.stats:
            return 1.0
        
        initial_count = self.stats[0].input_count
        if initial_count == 0:
            return 1.0
        
        return self.final_sentence_count / initial_count
    
    @property
    def average_sentence_length(self) -> float:
        """Get average sentence length in characters"""
        if not self.final_sentences:
            return 0.0
        
        total_length = sum(len(sentence) for sentence in self.final_sentences)
        return total_length / len(self.final_sentences)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the splitting operation"""
        return {
            "success": self.success,
            "total_time": round(self.total_processing_time, 2),
            "input_file": self.input_file,
            "output_file": self.output_file,
            "final_sentence_count": self.final_sentence_count,
            "total_split_operations": self.total_split_operations,
            "final_split_ratio": round(self.final_split_ratio, 2),
            "average_sentence_length": round(self.average_sentence_length, 1),
            "steps_completed": len(self.stats),
            "warnings_count": len(self.warnings),
            "error_message": self.error_message if not self.success else None
        }
    
    def print_summary(self):
        """Print a formatted summary"""
        print("=" * 50)
        print("SpaCy Text Splitting Summary")
        print("=" * 50)
        
        if self.success:
            print(f"✅ Status: SUCCESS")
            print(f"⏱️  Total Time: {self.total_processing_time:.2f}s")
            print(f"📄 Input: {self.input_file}")
            print(f"📄 Output: {self.output_file}")
            print(f"🔢 Final Sentences: {self.final_sentence_count}")
            print(f"✂️  Total Splits: {self.total_split_operations}")
            print(f"📊 Split Ratio: {self.final_split_ratio:.2f}")
            print(f"📏 Avg Length: {self.average_sentence_length:.1f} chars")
            
            if self.stats:
                print("\n📈 Step Details:")
                for stat in self.stats:
                    print(f"  {stat.step_name}: {stat.input_count} → {stat.output_count} "
                          f"({stat.processing_time:.2f}s, {stat.split_operations} splits)")
        else:
            print(f"❌ Status: FAILED")
            print(f"❌ Error: {self.error_message}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print("=" * 50) 