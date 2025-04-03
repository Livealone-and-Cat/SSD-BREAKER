import os
import time
import ctypes
import threading
import shutil
import msvcrt
import sys
import glob
from typing import List, Tuple, Optional, Dict

class SSD_BREAKER:
    def __init__(self):
        # 配置区
        self.CHUNK_SIZE = 128 * 1024 * 1024  # 默认块大小128MB
        self.MIN_FILE_SIZE_GB = 0.1           # 最小文件0.1GB
        self.DISPLAY_REFRESH_INTERVAL = 1.0   # 显示刷新间隔(秒)
        self.MAX_FILENAME_DISPLAY = 3         # 最大显示文件名数量
        
        # 运行状态区
        self.running = False
        self.paused = False
        self.current_drive = ""
        self.current_operation = ""
        
        # 数据统计区
        self.total_written_all_loops = 0
        self.total_written_current_loop = 0
        self.loop_counter = 0
        self.start_time = 0
        self.chunk_size_bytes = 0
        
        # 线程控制区
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.current_files = set()
        
        # 显示控制区
        self.last_display_time = 0
        self.last_written_bytes = 0
        self.last_speed_check_time = 0
        
        # 初始化数据区
        self.data = self._generate_ssdbreaker_data()
        self.drive_info_cache = {}

    def _generate_ssdbreaker_data(self) -> bytes:
        """生成随机数据"""
        try:
            print("正在准备数据...")
            return os.urandom(self.CHUNK_SIZE)
        except Exception as e:
            print(f"生成随机数据失败: {e}")
            print("改用伪随机模式...")
            return bytes([(i % 256) for i in range(self.CHUNK_SIZE)])

    def _cleanup_files(self, verbose: bool = True):
        """清理临时文件"""
        deleted_files = []
        error_files = []
        
        patterns = [
            f"{self.current_drive}:\\ssdbreaker_*.tmp",
            f"{self.current_drive}:\\ssdbreaker.tmp"
        ]
        
        # 清理当前文件和遗留文件
        for filepath in list(self.current_files):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    filename = os.path.basename(filepath)
                    deleted_files.append(filename)
            except Exception as e:
                error_files.append(f"{os.path.basename(filepath)}(错误:{str(e)})")
            finally:
                if filepath in self.current_files:
                    self.current_files.remove(filepath)
        
        # 清理可能遗留的文件
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                try:
                    if os.path.exists(filepath) and filepath not in self.current_files:
                        os.remove(filepath)
                        deleted_files.append(os.path.basename(filepath))
                except Exception as e:
                    error_files.append(f"{os.path.basename(filepath)}(错误:{str(e)})")
        
        # 显示清理结果
        if verbose and (deleted_files or error_files):
            display_msg = []
            if deleted_files:
                display_list = deleted_files[:self.MAX_FILENAME_DISPLAY]
                display_msg.append(f"已清理: {', '.join(display_list)}"
                                  f"{'...' if len(deleted_files)>self.MAX_FILENAME_DISPLAY else ''}")
            if error_files:
                error_list = error_files[:self.MAX_FILENAME_DISPLAY]
                display_msg.append(f"清理失败: {', '.join(error_list)}"
                                  f"{'...' if len(error_files)>self.MAX_FILENAME_DISPLAY else ''}")
            
            print("\n" + " | ".join(display_msg))

    def _get_drive_info(self, letter: str) -> Dict[str, int]:
        """获取磁盘信息"""
        if letter in self.drive_info_cache:
            return self.drive_info_cache[letter]
        
        try:
            usage = shutil.disk_usage(f"{letter}:\\")
            info = {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'is_ready': True
            }
            self.drive_info_cache[letter] = info
            return info
        except Exception as e:
            print(f"无法读取磁盘 {letter} 信息: {str(e)}")
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'is_ready': False
            }

    def _get_available_drives(self) -> List[Tuple[str, Dict[str, int]]]:
        """获取可用磁盘列表"""
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        
        for i, letter in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
            if bitmask & (1 << i):
                info = self._get_drive_info(letter)
                if info['is_ready']:
                    drives.append((letter, info))
        
        return drives

    def _format_size(self, bytes: int, precision: int = 2) -> str:
        """格式化大小显示"""
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        while bytes >= 1024 and unit_index < len(units)-1:
            bytes /= 1024.0
            unit_index += 1
        return f"{bytes:.{precision}f}{units[unit_index]}"

    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        time_units = [
            ('天', 86400),
            ('小时', 3600),
            ('分钟', 60),
            ('秒', 1)
        ]
        
        parts = []
        remaining = seconds
        for unit_name, unit_seconds in time_units:
            if remaining >= unit_seconds:
                value = int(remaining // unit_seconds)
                parts.append(f"{value}{unit_name}")
                remaining %= unit_seconds
            if remaining < 1:
                break
        
        return " ".join(parts) if parts else "0秒"

    def _ssdbreaker_input(self, prompt: str) -> str:
        """获取用户输入"""
        while msvcrt.kbhit():
            msvcrt.getch()
        
        sys.stdout.write(f"{prompt}")
        sys.stdout.flush()
        return input().strip()

    def _update_display(self, force: bool = False):
        """更新显示信息"""
        current_time = time.time()
        if not force and current_time - self.last_display_time < self.DISPLAY_REFRESH_INTERVAL:
            return
        
        elapsed_time = current_time - self.start_time
        bytes_written = self.total_written_current_loop - self.last_written_bytes
        time_elapsed = current_time - self.last_speed_check_time
        
        instant_speed = (bytes_written / (1024**2)) / max(0.1, time_elapsed)
        avg_speed = (self.total_written_current_loop / (1024**2)) / elapsed_time if elapsed_time > 0 else 0
        
        display_info = [
            f"{self.current_operation}",
            f"用时: {self._format_time(elapsed_time)}",
            f"本次: {self._format_size(self.total_written_current_loop)}",
            f"累计: {self._format_size(self.total_written_all_loops)}",
            f"速度: {avg_speed:.1f}MB/s (当前: {instant_speed:.1f}MB/s)",
            f"{'⏸️暂停中' if self.paused else '▶️运行中'}"
        ]
        
        sys.stdout.write("\r\033[K" + " | ".join(display_info))
        sys.stdout.flush()
        
        self.last_display_time = current_time
        self.last_written_bytes = self.total_written_current_loop
        self.last_speed_check_time = current_time

    def _select_drive_interactive(self) -> Optional[str]:
        """交互式选择磁盘"""
        while True:
            drives = self._get_available_drives()
            if not drives:
                print("没有找到可用磁盘！")
                return None
            
            print("\n可用磁盘列表:")
            for i, (letter, info) in enumerate(drives, 1):
                print(f"  {i}. {letter}: {self._format_size(info['free'])} 可用空间")
            
            choice = self._ssdbreaker_input("请选择磁盘编号或输入盘符 (如 1 或 C): ").upper()
            
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(drives):
                    self.current_drive = drives[index][0]
                    return self.current_drive
            elif len(choice) == 1 and choice.isalpha():
                if any(d[0] == choice for d in drives):
                    self.current_drive = choice
                    return self.current_drive
            
            print("输入无效，请重新选择！")

    def _configure_operation(self) -> Optional[Tuple[float, Optional[float], Tuple[Optional[int], bool]]]:
        """配置操作参数"""
        # 获取磁盘剩余空间
        drive_info = self._get_drive_info(self.current_drive)
        if not drive_info['is_ready']:
            print("磁盘不可用！")
            return None
            
        free_bytes = drive_info['free']
        free_gb = free_bytes / (1024 ** 3)
        
        # 获取总大小
        while True:
            size_input = self._ssdbreaker_input(
                f"请输入要填充的总大小 (如 10G/500M 或 1-100% 可用空间:{self._format_size(free_bytes)}): "
            ).strip()
            
            try:
                if '%' in size_input:
                    # 百分比计算
                    percent = float(size_input.replace('%', ''))
                    if 0 < percent <= 100:
                        total_size = (percent / 100) * free_gb
                        print(f"将填充: {self._format_size(total_size * (1024**3))} "
                              f"(磁盘剩余空间的 {percent}%)")
                        break
                    print("错误！百分比必须介于1-100之间")
                elif any(u in size_input.upper() for u in ['K', 'M', 'G', 'T']):
                    # 处理带单位的输入
                    unit = size_input[-1].upper()
                    num = float(size_input[:-1])
                    
                    if unit == 'K':
                        total_size = num / (1024*1024)
                    elif unit == 'M':
                        total_size = num / 1024
                    elif unit == 'G':
                        total_size = num
                    elif unit == 'T':
                        total_size = num * 1024
                    
                    if total_size <= 0:
                        raise ValueError("大小必须为正数")
                    
                    # 检查是否超过剩余空间
                    if total_size > free_gb:
                        print(f"错误！超过磁盘剩余空间 (剩余:{self._format_size(free_bytes)})")
                        continue
                    break
                else:
                    print("必须包含单位 (如 10G/500M) 或百分比 (如 50%)！")
            except ValueError as e:
                print(f"输入错误: {e}")

        # 获取分块设置
        chunk_size = None
        if self._ssdbreaker_input("要分块写入吗？(Y/n): ").lower() != 'n':
            while True:
                chunk_input = self._ssdbreaker_input("请输入每个块大小 (如 128M/1G): ").strip()
                try:
                    if any(u in chunk_input.upper() for u in ['K', 'M', 'G', 'T']):
                        unit = chunk_input[-1].upper()
                        num = float(chunk_input[:-1])
                        
                        if unit == 'K':
                            chunk_size = num / (1024*1024)
                        elif unit == 'M':
                            chunk_size = num / 1024
                        elif unit == 'G':
                            chunk_size = num
                        elif unit == 'T':
                            chunk_size = num * 1024
                            
                        if chunk_size <= 0 or chunk_size >= total_size:
                            print("块大小必须小于总大小！")
                            continue
                        break
                    else:
                        print("必须包含单位！示例: 128M")
                except (ValueError, IndexError):
                    print("输入格式错误！示例: 128M")

        # 获取循环设置
        while True:
            choice = self._ssdbreaker_input("请输入循环次数（正整数）或输入'r'无限循环: ").strip().lower()
            if choice == 'r':
                loop_info = (None, True)
                break
            elif choice.isdigit():
                num = int(choice)
                if num > 0:
                    loop_info = (num, False)
                    break
                print("请输入正整数！")
            else:
                print("输入无效，请输入数字或'r'！")

        return (total_size, chunk_size, loop_info)

    def _confirm_operation(self, drive: str, config: Tuple[float, Optional[float], Tuple[Optional[int], bool]]) -> bool:
        """确认操作"""
        total_size, chunk_size, (loop_count, is_infinite) = config
        
        print("\n" + "="*60)
        print(f"目标磁盘: {drive}:")
        print(f"总大小: {self._format_size(total_size * (1024**3))}")
        if chunk_size:
            print(f"块大小: {self._format_size(chunk_size * (1024**3))}")
            print(f"块数量: {int(total_size // chunk_size) + (1 if total_size % chunk_size > 0 else 0)}")
        
        if is_infinite:
            print("循环模式: 无限循环")
        else:
            print(f"循环次数: {loop_count} 次")
        
        confirm = self._ssdbreaker_input("确认开始操作吗？(Y/n): ").lower()
        return confirm == 'y'

    def _write_file(self, filepath: str, size: int) -> bool:
        """写入文件数据"""
        try:
            with open(filepath, 'wb', buffering=0) as f:
                written = 0
                while written < size:
                    if self.stop_event.is_set():
                        return False
                    while self.paused:
                        time.sleep(0.1)
                        self._update_display()
                    
                    chunk = min(len(self.data), size - written)
                    f.write(self.data[:chunk])
                    with self.lock:
                        self.total_written_current_loop += chunk
                        self.total_written_all_loops += chunk
                    written += chunk
                    
                    self.current_operation = f"{os.path.basename(filepath)}: {written/size*100:.1f}%"
                    self._update_display()
                return True
        except Exception as e:
            print(f"\n写入失败 {filepath}: {e}")
            return False

    def _execute_operation(self, drive: str, config: Tuple[float, Optional[float], Tuple[Optional[int], bool]]):
        """执行主操作"""
        total_size, chunk_size, (loop_count, is_infinite) = config
        total_bytes = int(total_size * (1024 ** 3))
        
        self.loop_counter = 0
        while is_infinite or self.loop_counter < loop_count:
            self.loop_counter += 1
            print(f"\n=== 第 {self.loop_counter}{'/'+str(loop_count) if not is_infinite else ''} 次循环 ===")

            # 重置状态
            self.running = True
            self.paused = False
            self.total_written_current_loop = 0
            self.start_time = time.time()
            self.last_display_time = 0
            self.last_written_bytes = 0
            self.last_speed_check_time = 0
            self.stop_event.clear()
            self.current_files.clear()

            print("开始写入... (按 p 暂停，s 继续，q 退出)")
            
            # 执行写入
            if chunk_size:
                # 分块写入模式
                chunk_bytes = int(chunk_size * (1024 ** 3))
                num_files = total_bytes // chunk_bytes
                remainder = total_bytes % chunk_bytes
                
                for i in range(num_files + (1 if remainder > 0 else 0)):
                    if self.stop_event.is_set():
                        break
                    
                    filepath = f"{drive}:\\ssdbreaker_{i}.tmp"
                    self.current_files.add(filepath)
                    current_size = chunk_bytes if i < num_files else remainder
                    
                    self.current_operation = f"块 {i+1}/{num_files + (1 if remainder > 0 else 0)} ({self._format_size(current_size)})"
                    if not self._write_file(filepath, current_size):
                        break
            else:
                # 单文件模式
                filepath = f"{drive}:\\ssdbreaker.tmp"
                self.current_files.add(filepath)
                self.current_operation = f"单文件 ({self._format_size(total_bytes)})"
                self._write_file(filepath, total_bytes)
            
            # 显示结果
            self.running = False
            total_time = time.time() - self.start_time
            avg_speed = (self.total_written_current_loop / (1024**2)) / total_time if total_time > 0 else 0
            
            print("\n\n" + "="*60)
            print(f"第 {self.loop_counter} 次循环结果:")
            print(f"本次写入量: {self._format_size(self.total_written_current_loop)}")
            print(f"累计总写入量: {self._format_size(self.total_written_all_loops)}")
            if chunk_size:
                print(f"单个分块大小: {self._format_size(chunk_bytes)}")
            print(f"总用时: {self._format_time(total_time)}")
            print(f"平均速度: {avg_speed:.1f}MB/s")
            print("="*60)
            
            if self.stop_event.is_set():
                print("用户请求停止")
                break
            
            # 清理文件
            self._cleanup_files()

    def draw_startup_banner(self):
        print(r"""
          /\_/\   喵呜~
         ( o.o )  欢迎使用SSD BREAKER V2.5.1
          > ^ <   在SSD中，每个闪存单元都有一定的寿命，通常为几万次到几百万次的写入。 当一个单元被写满时，它就会被标记为“坏块”，不再用于存储数据。（老生常谈
         /  ~  \  
        """)
        print("="*60)
        print("功 能:")
        print("  - 多磁盘精确打击")
        print("  - 智能分块毁灭技术")
        print("  - 实时进度输出")
        print("  - 自动清理作案痕迹")
        print("  - 支持暂停/继续破坏")
        print("="*60)
        print("警 告:")
        print("  - 此工具会造成不可逆磁盘寿命缩短")
        print("  - 请确保这个东西没有用于非法用途")
        print("  - 中断操作会自动清理已经创建的文件")
        print("="*60)

    def run(self):
        """主控制流程"""
        try:
            self.draw_startup_banner()
            
            # 磁盘选择
            drive = self._select_drive_interactive()
            if not drive:
                return
            
            # 参数配置
            config = self._configure_operation()
            if not config:
                return
            
            # 操作确认
            if not self._confirm_operation(drive, config):
                return
            
            # 执行操作
            self._execute_operation(drive, config)
            
        except KeyboardInterrupt:
            print("\n检测到中断信号...")
        except Exception as e:
            print(f"\n发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup_files()
            print("\n操作执行完毕")

if __name__ == "__main__":
    # 简单的文件锁实现单例检查
    lock_file = os.path.join(os.getenv('TEMP'), 'SSD_BREAKER.lock')
    try:
        if os.path.exists(lock_file):
            print("程序已在运行中！")
            sys.exit(1)
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        SSD_BREAKER().run()
    finally:
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass