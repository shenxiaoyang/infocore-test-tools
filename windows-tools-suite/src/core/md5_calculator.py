import os
import hashlib
import sys
import multiprocessing
from ..utils.logger import get_logger
import time

class MD5Calculator:
    """MD5计算器类"""
    def __init__(self):
        self.logger = get_logger(__name__)
        self.default_directory = r'C:\Windows'
        self.default_extensions = [
            '.exe', '.dll', '.sys',
            '.mui', '.ttf', '.wim',
            '.cur', '.ani', '.fon',
            '.TTF', '.cat', '.manifest',
            '.chm'
        ]
        self.progress_callback = None
        # 根据CPU核心数动态设置线程数
        self.max_workers = min(multiprocessing.cpu_count(), 4)
        self.batch_size = 10000  # 每批写入的文件数
        self.output_file = None  # 当前输出文件
        self.total_md5 = hashlib.md5()  # 用于计算总MD5值
        self.current_directory = ""  # 当前正在处理的目录
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def update_progress(self, current, total, message):
        """更新进度信息"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def is_link_file(self, file_path):
        """检查文件是否是链接文件"""
        try:
            # 检查是否是符号链接
            if os.path.islink(file_path):
                return True
            
            # 检查是否是Windows快捷方式
            if file_path.lower().endswith('.lnk'):
                return True
                
            # 检查是否是Windows的Junction Point或者Mount Point
            if os.path.ismount(file_path):
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"检查链接文件失败: {file_path}, 错误: {str(e)}")
            return False
    
    def calculate_file_md5(self, file_path):
        """计算单个文件的MD5值"""
        try:
            # 检查是否是链接文件
            if self.is_link_file(file_path):
                self.logger.debug(f"跳过链接文件: {file_path}")
                return None
                
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)  # 转换为MB
            
            self.logger.debug(f"正在处理: {file_path} (大小: {file_size_mb:.2f}MB)")
                
            with open(file_path, 'rb') as f:
                md5_hash = hashlib.md5()
                # 使用分块读取以处理大文件
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
                md5_value = md5_hash.hexdigest()
                self.logger.debug(f"MD5计算完成: {file_path} = {md5_value}")
                return md5_value
        except Exception as e:
            self.logger.error(f"计算文件MD5失败: {file_path}, 错误: {str(e)}")
            return None
    
    def process_file(self, file_path, extensions):
        """处理单个文件"""
        if any(file_path.lower().endswith(ext.lower()) for ext in extensions):
            md5 = self.calculate_file_md5(file_path)
            if md5:
                return file_path, md5
        return None
    
    def prepare_output_file(self):
        """准备输出文件"""
        try:
            # 使用exe所在目录作为基准目录
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 查找下一个可用的文件序号
            index = 1
            while os.path.exists(os.path.join(output_dir, f"md5-{index}.log")):
                index += 1
            
            # 生成文件名
            filename = os.path.join(output_dir, f"md5-{index}.log")
            self.output_file = filename
            return filename
        except Exception as e:
            self.logger.error(f"准备输出文件失败: {str(e)}")
            raise
    
    def write_batch_results(self, results):
        """写入一批结果到文件"""
        try:
            if not self.output_file:
                self.prepare_output_file()
            
            # 写入结果
            with open(self.output_file, 'a', encoding='utf-8') as f:
                for file_path, md5 in results.items():
                    if isinstance(md5, str):  # 确保 md5 是字符串类型
                        f.write(f"{file_path}\t{md5}\n")
                        # 更新总MD5值
                        self.total_md5.update(md5.encode())
            
        except Exception as e:
            self.logger.error(f"写入结果失败: {str(e)}")
            raise
    
    def save_final_record(self):
        """保存最终的record记录"""
        try:
            if not self.output_file:
                self.logger.error("没有输出文件")
                return
            
            # 统一用prepare_output_file的output目录
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(base_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            record_file = os.path.join(output_dir, "record.log")
            
            with open(record_file, 'a', encoding='utf-8') as f:
                f.write(f"{self.output_file}\t{self.total_md5.hexdigest()}\n")
            
            self.logger.info(f"结果已保存到: {record_file}")
        except Exception as e:
            self.logger.error(f"保存record记录失败: {str(e)}")
            raise
    
    def scan_directory(self, directories, extensions, exclude_hours=4, exclude_keywords=[], time_type='modified'):
        start_time = time.time()
        results = {}
        total_scanned = 0
        processed_files = 0
        excluded_files = 0
        total_size = 0
        skipped_files = []
        current_time = time.time()
        processed_paths = set()
        
        # 检查是否包含通配符
        match_all = '*' in [ext.strip() for ext in extensions]

        for directory in directories:
            self.current_directory = directory
            self.logger.info(f"开始扫描目录: {directory}")
            self.logger.info(f"文件扩展名过滤: {'所有文件' if match_all else ', '.join(extensions)}")
            self.logger.info(exclude_keywords)
        
            # 遍历目录并处理文件
            for root, dirs, files in os.walk(directory):
                dirs.sort()
                files.sort()
                
                # 更新当前处理的子目录
                self.current_directory = root
                if len(files) > 0:
                    self.logger.debug(f"正在处理子目录: {root}，包含 {len(files)} 个文件")
                
                for file in files:
                    file_path = os.path.join(root, file)
                    total_scanned += 1
                    self.logger.debug(f"扫描文件: {file_path}")
                    
                    try:
                        file_size = os.path.getsize(file_path)
                    except OSError:
                        self.logger.error(f"获取文件大小失败: {file_path}")
                        excluded_files += 1
                        skipped_files.append((file_path, "无法获取文件大小"))
                        continue
                    
                    # 检查是否已经处理过这个文件
                    if file_path in processed_paths:
                        self.logger.debug(f"文件已处理过，跳过: {file_path}")  # 改为 debug 级别
                        excluded_files += 1
                        skipped_files.append((file_path, "文件已处理过"))
                        continue
                    processed_paths.add(file_path)
                    
                    # 检查文件扩展名（如果不是匹配所有文件的情况）
                    if not match_all and not any(file.lower().endswith(ext.lower()) for ext in extensions):
                        self.logger.debug(f"跳过文件（扩展名不匹配）: {file_path}")  # 改为 debug 级别
                        excluded_files += 1
                        skipped_files.append((file_path, "扩展名不匹配"))
                        continue
                        
                    # 检查是否包含排除关键字（增强日志）
                    matched_keyword = None
                    for keyword in exclude_keywords:
                        if keyword.lower() in file_path.lower():
                            matched_keyword = keyword
                            self.logger.debug(
                                f"文件[{file_path}]包含排除关键字[{keyword}]，将被排除。"
                            )
                            break
                        else:
                            self.logger.debug(
                                f"文件[{file_path}]未包含排除关键字[{keyword}]。"
                            )
                    if matched_keyword:
                        skipped_files.append((file_path, f"关键字排除({matched_keyword})"))
                        excluded_files += 1
                        continue
                    
                    # 检查文件时间
                    try:
                        if time_type == 'modified':
                            file_time = int(os.path.getmtime(file_path))
                            time_desc = "修改时间"
                        elif time_type == 'created':
                            file_time = int(os.path.getctime(file_path))
                            time_desc = "创建时间"
                        else:  # accessed
                            file_time = int(os.path.getatime(file_path))
                            time_desc = "访问时间"
                        
                        current_time = int(time.time())
                        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_time))
                        seconds_since = current_time - file_time
                        hours_since = seconds_since / 3600
                        
                        if seconds_since < exclude_hours * 3600:
                            self.logger.debug(f"跳过文件（时间排除）: {file_path}, {time_desc}: {time_str}")  # 改为 debug 级别
                            skipped_files.append((file_path, f"时间排除 ({time_desc}: {time_str})"))
                            excluded_files += 1
                            continue
                    except OSError as e:
                        self.logger.error(f"获取文件时间失败: {file_path}, 错误: {str(e)}")
                        excluded_files += 1
                        skipped_files.append((file_path, f"无法获取文件时间: {str(e)}"))
                        continue
                    
                    # 检查是否是链接文件
                    if self.is_link_file(file_path):
                        self.logger.debug(f"跳过链接文件: {file_path}")  # 改为 debug 级别
                        excluded_files += 1
                        skipped_files.append((file_path, "链接文件"))
                        continue
                    
                    # 计算MD5
                    md5 = self.calculate_file_md5(file_path)
                    if md5:
                        results[file_path] = md5
                        self.total_md5.update(md5.encode())
                        processed_files += 1
                        total_size += file_size
                        
                        # 每处理100个文件输出一次日志
                        if processed_files % 1000 == 0:
                            self.logger.info(f"已成功处理 {processed_files} 个文件")
                        
                        # 如果结果达到批处理大小，写入文件
                        if len(results) >= self.batch_size:
                            self.write_batch_results(results)
                            results.clear()
                    else:
                        self.logger.error(f"MD5计算失败: {file_path}")
                        excluded_files += 1
                        skipped_files.append((file_path, "MD5计算失败"))
                    
                    # 计算已用时间
                    elapsed_time = time.time() - start_time
                    elapsed_minutes = int(elapsed_time // 60)
                    elapsed_seconds = int(elapsed_time % 60)
                    
                    # 更新进度信息
                    total_size_mb = total_size / (1024 * 1024)
                    progress_msg = (
                        f"已扫描{total_scanned}个文件，"
                        f"符合条件{processed_files}个文件(总大小: {total_size_mb:.2f}MB)，"
                        f"排除{excluded_files}个文件，"
                        f"已用时间: {elapsed_minutes}分{elapsed_seconds}秒"
                    )
                    self.update_progress(total_scanned, 0, progress_msg)
        
        # 记录被排除的文件
        if skipped_files:
            os.makedirs("output", exist_ok=True)  # 确保output目录存在
            skip_file = os.path.join("output", f"skipped-{int(time.time())}.log")
            with open(skip_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write("以下文件因被排除而跳过：\n")
                f.write(f"总计跳过文件数：{len(skipped_files)}\n\n")
                for file_path, reason in sorted(skipped_files):
                    f.write(f"{file_path} ({reason})\n")
            self.logger.info(f"被排除的文件列表已保存到: {skip_file}")
        
        # 写入最后一批结果
        if results:
            self.write_batch_results(results)
        
        # 保存record记录
        self.save_final_record()
        
        elapsed_time = time.time() - start_time
        final_msg = (
            f"处理完成，共扫描{total_scanned}个文件，"
            f"成功处理{processed_files}个文件，"
            f"排除{excluded_files}个文件（详见skipped日志），"
            f"总大小: {total_size / (1024 * 1024):.2f}MB，"
            f"耗时: {elapsed_time:.2f}秒"
        )
        self.logger.info(final_msg)
        return self.output_file

    def reset(self):
        self.output_file = None
        self.total_md5 = hashlib.md5()
        self.current_directory = ""