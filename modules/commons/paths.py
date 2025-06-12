import os

from pathlib import Path

# 判断操作系统来得到目录分割符
def get_separator():
    if os.name == "nt":
        return "\\"
    else:
        return "/"

# 获得一个output目录 默认是output
def get_filepath_by_output_dir(filename: str, output_base_dir: str = "output") -> Path: 
    return Path(os.getcwd()) / output_base_dir / filename

# 获得一个log目录 默认是output/log
def get_filepath_by_log_dir(filename: str, output_base_dir: str = "output", log_dir: str = "log") -> Path:
    return get_filepath_by_output_dir(os.path.join(log_dir, filename), output_base_dir=output_base_dir)

# 获得一个audio目录 默认是output/audio
def get_filepath_by_audio_dir(filename: str, output_base_dir: str = "output", audio_dir: str = "audio") -> Path:
    return get_filepath_by_output_dir(os.path.join(audio_dir, filename), output_base_dir=output_base_dir)

# 获得一个temp目录 默认是output/temp
def get_filepath_by_temp_dir(filename: str, output_base_dir: str = "output", temp_dir: str = "temp") -> Path:
    return get_filepath_by_output_dir(os.path.join(temp_dir, filename), output_base_dir=output_base_dir)

def get_filepath_by_default(filename: str, output_base_dir: str = "output") -> Path:
    # 如果filename是绝对路径，则直接返回
    if os.path.isabs(filename):
        return Path(filename)
    else:
        # 如果filename没有路径，则返回Log路径
        if '/' not in filename and '\\' not in filename:
            return get_filepath_by_log_dir(filename, output_base_dir=output_base_dir)
        else:
            # 如果filename有路径，则返回output路径
            return get_filepath_by_output_dir(filename, output_base_dir=output_base_dir)


