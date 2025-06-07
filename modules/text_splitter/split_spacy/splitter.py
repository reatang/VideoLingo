"""
Main splitter class that orchestrates the text splitting process
"""

import os
import time
import pandas as pd
from typing import List, Optional
from rich import print as rprint

from modules.common_utils import paths

from .core.config import SplitterConfig
from .core.runtime import SpacyRuntime 
from .core.result import SplitResult
from .strategies.mark_splitter import MarkSplitter
from .strategies.comma_splitter import CommaSplitter
from .strategies.connector_splitter import ConnectorSplitter
from .strategies.root_splitter import RootSplitter
from .exceptions import SpacySplitterError, FileProcessingError

class SpacySplitter:
    """
    Main SpaCy text splitter with lifecycle management
    
    Lifecycle:
    - Startup phase: initialize configuration and runtime
    - Working phase: execute splitting pipeline
    - Cleanup phase: release resources and clean temporary files
    """
    
    def __init__(self, config: SplitterConfig = None):
        """
        Initialize splitter with configuration
        
        Args:
            config: SplitterConfig instance, defaults to None (creates default config)
        """
        self.config = config or SplitterConfig()
        self.runtime: Optional[SpacyRuntime] = None
        self._is_started = False
        
    def startup(self) -> None:
        """
        Startup phase: initialize runtime and load models
        """
        if self._is_started:
            return
            
        rprint("[blue]🚀 Starting SpaCy text splitter...[/blue]")
        
        try:
            # initialize runtime and load model
            self.runtime = SpacyRuntime(self.config)
            self.runtime.startup()
            
            self._is_started = True
            rprint(f"[green]✅ SpaCy splitter started successfully![/green]")
            
        except Exception as e:
            raise SpacySplitterError(f"Failed to start SpaCy splitter: {str(e)}")
    
    def process_file(self, input_file: str = None, output_file: str = None) -> SplitResult:
        """
        Process text file through the splitting pipeline
        
        Args:
            input_file: path to input Excel file (cleaned_chunks.xlsx)
            output_file: path to output file (optional)
            
        Returns:
            SplitResult: complete processing result with statistics
        """
        # ensure splitter is started
        if not self._is_started:
            self.startup()
        
        start_time = time.time()
        result = SplitResult()
        
        try:
            # set file paths
            full_path = paths.get_filepath_by_default(input_file, output_base_dir=self.config.output_dir)
            result.input_file = full_path
            
            # validate input file exists
            if not full_path.exists():
                raise FileProcessingError(f"Input file not found: {full_path}")
            
            rprint(f"[blue]📄 Processing file: {full_path}[/blue]")
            
            # execute splitting pipeline
            sentences = self._execute_pipeline(full_path, result)
            
            # save final results
            if not output_file:
                output_file = paths.get_filepath_by_default(self.config.output_file, output_base_dir=self.config.output_dir)
            else:
                output_file = paths.get_filepath_by_default(output_file, output_base_dir=self.config.output_dir)
            
            result.output_file = output_file
            self._save_final_result(sentences, output_file)
        
            # set final result data
            result.final_sentences = sentences
            result.final_sentence_count = len(sentences)
            result.total_processing_time = time.time() - start_time
            
            rprint(f"[green]🎉 Text splitting completed successfully![/green]")
            rprint(f"[green]📊 Final result: {len(sentences)} sentences in {result.total_processing_time:.2f}s[/green]")
            
        except Exception as e:
            result.set_error(str(e))
            # 打印错误栈
            import traceback
            traceback.print_exc()
            rprint(f"[red]❌ Text splitting failed: {str(e)}[/red]")
        
        return result
    
    def _execute_pipeline(self, input_file: str, result: SplitResult) -> List[str]:
        """
        Execute the complete splitting pipeline
        
        Args:
            input_file: input file path
            result: result object to collect statistics
            
        Returns:
            List[str]: final list of split sentences
        """
        nlp = self.runtime.get_nlp()
        current_sentences = []
        
        # ------------
        # Step 1: Split by punctuation marks
        # ------------
        if self.config.enable_mark_split:
            step_start = time.time()
            mark_splitter = MarkSplitter(self.config)
            sentences = mark_splitter.process(input_file, nlp)
            step_time = time.time() - step_start
            
            result.add_step_stats("split_by_mark", 1, len(sentences), step_time, 0)
            current_sentences = sentences
            rprint(f"[cyan]📍 Step 1 completed: {len(sentences)} sentences from mark splitting[/cyan]")
        
        # ------------
        # Step 2: Split by commas  
        # ------------
        if self.config.enable_comma_split and current_sentences:
            step_start = time.time()
            comma_splitter = CommaSplitter(self.config)
            sentences, split_count = comma_splitter.process(current_sentences, nlp)
            step_time = time.time() - step_start
            
            result.add_step_stats("split_by_comma", len(current_sentences), len(sentences), step_time, split_count)
            current_sentences = sentences
            rprint(f"[cyan]📍 Step 2 completed: {len(sentences)} sentences after comma splitting[/cyan]")
        
        # ------------
        # Step 3: Split by connectors
        # ------------
        if self.config.enable_connector_split and current_sentences:
            step_start = time.time()
            connector_splitter = ConnectorSplitter(self.config)
            sentences, split_count = connector_splitter.process(current_sentences, nlp)
            step_time = time.time() - step_start
            
            result.add_step_stats("split_by_connector", len(current_sentences), len(sentences), step_time, split_count)
            current_sentences = sentences
            rprint(f"[cyan]📍 Step 3 completed: {len(sentences)} sentences after connector splitting[/cyan]")
        
        # ------------
        # Step 4: Split long sentences by root
        # ------------
        if self.config.enable_root_split and current_sentences:
            step_start = time.time()
            root_splitter = RootSplitter(self.config)
            sentences, split_count = root_splitter.process(current_sentences, nlp)
            step_time = time.time() - step_start
            
            result.add_step_stats("split_by_root", len(current_sentences), len(sentences), step_time, split_count)
            current_sentences = sentences
            rprint(f"[cyan]📍 Step 4 completed: {len(sentences)} sentences after root splitting[/cyan]")
        
        return current_sentences
    
    def _save_final_result(self, sentences: List[str], output_file: str):
        """Save final sentences to output file"""
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:  # skip empty sentences
                        f.write(sentence + "\n")
            
            rprint(f"[green]💾 Final result saved to: {output_file}[/green]")
            
        except Exception as e:
            raise FileProcessingError(f"Failed to save final result: {str(e)}")
    
    def cleanup(self) -> None:
        """
        Cleanup phase: release resources and clean temporary files
        """
        if self.runtime:
            self.runtime.cleanup()
            self.runtime = None
        
        # clean temporary files if auto cleanup enabled
        if self.config.auto_cleanup:
            self._clean_temp_files()
        
        self._is_started = False
        rprint("[blue]🧹 SpaCy splitter cleanup completed[/blue]")
    
    def _clean_temp_files(self):
        """Clean temporary files"""
        temp_files = self.config.temp_files
        for file_type, file_path in temp_files.items():
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    rprint(f"[blue]🗑️  Cleaned temp file: {file_path}[/blue]")
                except Exception as e:
                    rprint(f"[yellow]⚠️  Failed to clean temp file {file_path}: {str(e)}[/yellow]")
    
    def __enter__(self):
        """Context manager entry"""
        self.startup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup() 