# 最简单使用
from os.path import join
from modules.text_splitter.split_spacy import split_text



result = split_text(join("log", "cleaned_chunks.xlsx"), output_dir=join("my_scripts", "output"))
