import os
import hashlib
import random
import time
from src.utils.common import format_size

class FileGenerator:
    """
    负责生成指定数量、大小、内容的测试文件，不依赖任何UI。
    """
    def __init__(self, target_dir, file_size_min, file_size_max, size_unit, max_files, is_loop=False, interval=0):
        self.target_dir = target_dir
        self.file_size_min = file_size_min
        self.file_size_max = file_size_max
        self.size_unit = size_unit
        self.max_files = max_files
        self.is_loop = is_loop
        self.interval = interval
        self.chunk_size = 10 * 1024 * 1024

    def convert_to_bytes(self, size, unit):
        multipliers = {'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
        return int(size * multipliers[unit])

    def generate_file_content(self, file_path, total_size, pause_flag=None, stop_flag=None):
        hasher = hashlib.md5()
        written_size = 0
        with open(file_path, 'wb') as f:
            while written_size < total_size:
                if stop_flag and stop_flag():
                    return None
                while pause_flag and pause_flag():
                    if stop_flag and stop_flag():
                        return None
                    time.sleep(0.1)
                remaining = total_size - written_size
                current_chunk_size = min(self.chunk_size, remaining)
                chunk = os.urandom(current_chunk_size)
                hasher.update(chunk)
                f.write(chunk)
                written_size += current_chunk_size
        return hasher.hexdigest()

    def generate_files(self, progress_callback=None, finished_callback=None, stop_flag=None, pause_flag=None, stopped_callback=None):
        """
        生成文件主流程。progress_callback: 进度回调，finished_callback: 完成回调，stop_flag: 停止标志，pause_flag: 暂停标志，stopped_callback: 停止回调。
        """
        round_number = 1
        while True:
            random_suffix = ''.join(random.choices('0123456789ABCDEF', k=8))
            parent_dir_name = f"{round_number}_{random_suffix}"
            files_dir = os.path.join(self.target_dir, parent_dir_name)
            os.makedirs(files_dir, exist_ok=True)
            files_created = 0
            total_size = 0
            created_file_paths = []
            min_bytes = self.convert_to_bytes(self.file_size_min, self.size_unit)
            max_bytes = self.convert_to_bytes(self.file_size_max, self.size_unit)
            if progress_callback:
                progress_callback('start', files_dir, files_created, self.max_files, total_size, round_number)
            for i in range(self.max_files):
                if stop_flag and stop_flag():
                    if stopped_callback:
                        stopped_callback(files_dir, files_created, self.max_files, total_size, round_number)
                    return
                while pause_flag and pause_flag():
                    if stop_flag and stop_flag():
                        if stopped_callback:
                            stopped_callback(files_dir, files_created, self.max_files, total_size, round_number)
                        return
                    time.sleep(0.1)
                file_size = random.randint(min_bytes, max_bytes)
                temp_file = os.path.join(files_dir, f"temp_{i}")
                md5 = self.generate_file_content(temp_file, file_size, pause_flag=pause_flag, stop_flag=stop_flag)
                if md5 is None:
                    if stopped_callback:
                        stopped_callback(files_dir, files_created, self.max_files, total_size, round_number)
                    return
                num_width = len(str(self.max_files))
                file_number = str(i+1).zfill(num_width)
                final_path = os.path.join(files_dir, f"{file_number}.{md5}.md5file")
                os.rename(temp_file, final_path)
                total_size += file_size
                files_created += 1
                created_file_paths.append(os.path.abspath(final_path))
                if progress_callback:
                    progress_callback('progress', files_dir, files_created, self.max_files, total_size, round_number)
                if self.interval > 0:
                    time.sleep(self.interval)
            # 写入 all_created_files.txt
            all_files_txt = os.path.join(files_dir, "all_created_files.txt")
            with open(all_files_txt, "w", encoding="utf-8") as f:
                for path in created_file_paths:
                    f.write(path + "\n")
            if finished_callback:
                finished_callback(files_dir, files_created, total_size)
            if progress_callback:
                progress_callback('finished', files_dir, files_created, self.max_files, total_size, round_number)
            if not self.is_loop:
                break
            round_number += 1
            if progress_callback:
                progress_callback('loop_wait', files_dir, files_created, self.max_files, total_size, round_number)
            time.sleep(3)
