import os
import time
import ctypes
import threading
import shutil
import msvcrt
import sys
import glob
from typing import List, Tuple, Optional

class KawaiiDiskDestroyer:
    def __init__(self):
        # 超可爱配置
        self.CHUNK_SIZE = 128 * 1024 * 1024  # 128MB块
        self.MIN_FILE_SIZE_GB = 0.1           # 最小文件0.1GB
        
        # 运行状态
        self.running = False
        self.paused = False
        self.total_written = 0
        self.start_time = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.current_files = set()
        
        # 显示状态
        self.current_chunk = ""
        self.last_refresh = 0
        self.last_written = 0
        self.last_time = 0
        
        # 初始化超可爱数据
        self.data = self._generate_kawaii_data()

    def _generate_kawaii_data(self) -> bytes:
        """生成超可爱的随机数据ฅ^•ﻌ•^ฅ"""
        try:
            return os.urandom(self.CHUNK_SIZE)
        except Exception as e:
            print(f"(;´༎ຶД༎ຶ`) 生成随机数据失败啦: {e}")
            return bytes([(i % 256) for i in range(self.CHUNK_SIZE)])

    def _cleanup_files(self):
        """清理所有临时文件(´･_･`)"""
        for path in list(self.current_files) + glob.glob(f"{self.current_drive}:\\kawaii*.tmp"):
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"\n(｡•́︿•̀｡) 已清理: {os.path.basename(path)}")
            except Exception as e:
                print(f"(;´༎ຶД༎ຶ`) 清理失败 {path}: {e}")

    def _get_available_drives(self) -> List[Tuple[str, int]]:
        """获取所有可用磁盘ฅ(＾・ω・＾ฅ)"""
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            if bitmask & 1:
                try:
                    free = shutil.disk_usage(f"{letter}:\\").free
                    drives.append((letter, free))
                except Exception:
                    pass  # 跳过不可访问的驱动器
            bitmask >>= 1
        return drives
    
    def _format_size(self, bytes: int) -> str:
        """格式化文件大小显示(=^･ω･^=)"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.2f}{unit}"
            bytes /= 1024.0
        return f"{bytes:.2f}PB"

    def _format_time(self, seconds: float) -> str:
        """萌化时间显示(◕‿◕✿)"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            return f"{int(seconds//60)}分{int(seconds%60)}秒"
        else:
            return f"{int(seconds//3600)}小时{int((seconds%3600)//60)}分{int(seconds%60)}秒"

    def _kawaii_input(self, prompt: str) -> str:
        """超可爱输入函数(=^･ω･^=)"""
        while msvcrt.kbhit():
            msvcrt.getch()
        sys.stdout.write(f"(◕‿◕) {prompt}")
        sys.stdout.flush()
        return input().strip()

    def _update_display(self):
        """单行动态刷新显示(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧"""
        now = time.time()
        if now - self.last_refresh < 1.0 and not self.stop_event.is_set():
            return
            
        self.last_refresh = now
        total_time = now - self.start_time
        instant_speed = ((self.total_written - self.last_written) / (1024**2)) / max(0.1, now - self.last_time)
        avg_speed = (self.total_written / (1024**2)) / total_time if total_time > 0 else 0
        
        display_msg = (
            f"{self.current_chunk} | "
            f"已用: {self._format_time(total_time)} | "
            f"写入: {self._format_size(self.total_written)} | "
            f"速度: {avg_speed:.1f}MB/s (当前: {instant_speed:.1f}MB/s) | "
            f"{'⏸️暂停中' if self.paused else '▶️运行中'}"
        )
        
        sys.stdout.write("\r\033[K" + display_msg)
        sys.stdout.flush()
        self.last_written = self.total_written
        self.last_time = now

    def select_drive(self) -> str:
        """选择目标磁盘"""
        self.current_drive = ""
        while not self.current_drive:
            drives = self._get_available_drives()
            if not drives:
                print("(;´༎ຶД༎ຶ`) 没有找到可用磁盘啦！")
                sys.exit(1)
            
            print("\n可用磁盘列表:")
            for i, (letter, free) in enumerate(drives, 1):
                print(f"  {i}. {letter}: {self._format_size(free)} 可用")

            choice = self._kawaii_input("请选择磁盘编号或盘符 (如 1 或 C): ").upper()
            
            if choice.isdigit() and 0 < int(choice) <= len(drives):
                self.current_drive = drives[int(choice)-1][0]
            elif len(choice) == 1 and choice.isalpha() and any(d[0] == choice for d in drives):
                self.current_drive = choice
            else:
                print("(；′⌒`) 输入无效，请重新选择！")
        
        self._cleanup_files()  # 自动清理旧文件
        return self.current_drive

    def get_file_size(self) -> Tuple[float, Optional[float]]:
        """获取填充参数"""
        while True:
            size_input = self._kawaii_input("请输入要填充的总大小 (必须带单位，如 10G/500M/50%): ").strip()
            try:
                if '%' in size_input:
                    percent = float(size_input.replace('%', '')) / 100
                    if 0 < percent <= 1:
                        total_size = percent
                        break
                    print("(╯°□°）╯ 百分比要在0-100之间啦！")
                elif any(u in size_input.upper() for u in ['K', 'M', 'G', 'T']):
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
                    else:
                        raise ValueError
                    
                    if total_size <= 0:
                        raise ValueError
                    break
                else:
                    print("(；´Д｀) 必须包含单位哦！示例: 10G 或 50%")
            except (ValueError, IndexError):
                print("(；´Д｀) 输入格式错误！示例: 10G 或 50%")

        # 获取分块设置
        use_chunks = self._kawaii_input("要分块写入吗？(Y/n): ").lower() != 'n'
        chunk_size = None
        
        if use_chunks:
            while True:
                chunk_input = self._kawaii_input("请输入每个块大小 (必须带单位，如 128M/1G): ").strip()
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
                            print("(╯°□°）╯ 块大小必须小于总大小！")
                            continue
                        break
                    else:
                        print("(；´Д｀) 必须包含单位哦！示例: 128M")
                except (ValueError, IndexError):
                    print("(；´Д｀) 输入格式错误！示例: 128M")
        
        return (total_size, chunk_size)

    def get_loop_setting(self) -> Tuple[Optional[int], bool]:
        """获取循环设置(≧▽≦)"""
        while True:
            choice = self._kawaii_input("请输入循环次数（正整数）或输入'r'无限循环: ").strip().lower()
            if choice == 'r':
                return (None, True)
            elif choice.isdigit():
                num = int(choice)
                if num > 0:
                    return (num, False)
                print("(；´Д｀) 请输入正整数！")
            else:
                print("(；´Д｀) 输入无效，请输入数字或'r'！")

    def confirm_operation(self, total_size: float, chunk_size: Optional[float], loop_info: Tuple[Optional[int], bool]) -> bool:
        """确认操作(๑>ᴗ<๑)"""
        print("\n" + "="*50)
        print(f"目标磁盘: {self.current_drive}:")
        print(f"总大小: {self._format_size(total_size * (1024**3))}")
        if chunk_size:
            print(f"块大小: {self._format_size(chunk_size * (1024**3))}")
            print(f"块数量: {int(total_size // chunk_size) + (1 if total_size % chunk_size > 0 else 0)}")
        
        loop_count, is_infinite = loop_info
        if is_infinite:
            print("循环模式: 无限循环 ♾️")
        else:
            print(f"循环次数: {loop_count} 次 🔁")
        
        confirm = self._kawaii_input("确认开始操作吗？(Y/n): ").lower()
        return confirm == 'y'

    def _write_file(self, file_path: str, size: int):
        """写入文件数据"""
        try:
            with open(file_path, 'wb', buffering=0) as f:
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
                        self.total_written += chunk
                    written += chunk
                    
                    # 更新当前块进度
                    self.current_chunk = (
                        f"{os.path.basename(file_path)}: "
                        f"{written/size*100:.1f}%"
                    )
                    self._update_display()
                return True
        except Exception as e:
            print(f"\n(;´༎ຶД༎ຶ`) 写入失败 {file_path}: {e}")
            return False

    def destroy(self, total_size_gb: float, chunk_size_gb: Optional[float]):
        """执行磁盘写入操作"""
        total_size = int(total_size_gb * (1024 ** 3))
        self.current_files.clear()
        
        try:
            if chunk_size_gb:
                # 分块写入模式
                chunk_size = int(chunk_size_gb * (1024 ** 3))
                num_files = total_size // chunk_size
                remainder = total_size % chunk_size
                
                for i in range(num_files + (1 if remainder > 0 else 0)):
                    if self.stop_event.is_set():
                        break
                    
                    path = f"{self.current_drive}:\\kawaii_{i}.tmp"
                    self.current_files.add(path)
                    current_size = chunk_size if i < num_files else remainder
                    
                    # 更新块信息
                    self.current_chunk = (
                        f"块 {i+1}/{num_files + (1 if remainder > 0 else 0)} "
                        f"({self._format_size(current_size)})"
                    )
                    
                    if not self._write_file(path, current_size):
                        break
            else:
                # 单文件模式
                path = f"{self.current_drive}:\\kawaii.tmp"
                self.current_files.add(path)
                self.current_chunk = f"单文件 ({self._format_size(total_size)})"
                self._write_file(path, total_size)
        finally:
            self._cleanup_files()

    def draw_cat(self):
        """绘制小猫咪"""
        print(r"""
          /\_/\  
         ( o.o ) 
          > ^ <  
         /  ~  \ 
        """)
        print("(=^･ω･^=) SSD BREAKER V2 (=^･ω･^=)")
        print("="*50)
        print("为自由而战 - Fight for freedom!")
        print("="*50)

    def run(self):
        """主运行方法"""
        try:
            self.draw_cat()
            
            # 1. 选择磁盘（自动清理旧文件）
            drive = self.select_drive()
            
            # 2. 获取填充参数
            total_size, chunk_size = self.get_file_size()
            
            # 3. 获取循环设置
            loop_info = self.get_loop_setting()
            
            # 4. 确认操作
            if not self.confirm_operation(total_size, chunk_size, loop_info):
                print("(；ω；) 操作已取消")
                return
            
            loop_count, is_infinite = loop_info
            current_loop = 0
            
            while is_infinite or (current_loop < loop_count):
                current_loop += 1
                print(f"\n=== 第 {current_loop}{'/'+str(loop_count) if not is_infinite else ''} 次循环 ===")

                # 重置状态
                self.running = True
                self.paused = False
                self.total_written = 0
                self.start_time = time.time()
                self.last_refresh = 0
                self.last_written = 0
                self.last_time = 0
                self.stop_event.clear()

                print("开始写入... (按 p 暂停，s 继续，q 退出)")
                
                destroy_thread = threading.Thread(
                    target=self.destroy,
                    args=(total_size, chunk_size)
                )
                destroy_thread.start()

                # 控制循环
                try:
                    while destroy_thread.is_alive():
                        if msvcrt.kbhit():
                            key = msvcrt.getch().decode().lower()
                            if key == 'p' and not self.paused:
                                self.paused = True
                            elif key == 's' and self.paused:
                                self.paused = False
                            elif key == 'q':
                                self.stop_event.set()
                        time.sleep(0.1)
                        self._update_display()
                except KeyboardInterrupt:
                    self.stop_event.set()

                destroy_thread.join()
                self.running = False
                
                # 显示本轮结果
                total_time = time.time() - self.start_time
                avg_speed = (self.total_written / (1024**2)) / total_time if total_time > 0 else 0
                print("\n\n" + "="*50)
                print(f"第 {current_loop} 次循环结果:")
                print(f"总写入量: {self._format_size(self.total_written)}")
                print(f"总用时: {self._format_time(total_time)}")
                print(f"平均速度: {avg_speed:.1f}MB/s")
                print("="*50)

                if self.stop_event.is_set():
                    print("(；ω；) 用户请求停止")
                    break
        except Exception as e:
            print(f"\n(´;ω;`) 发生错误: {e}")
        finally:
            self._cleanup_files()
            input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        KawaiiDiskDestroyer().run()
    except Exception as e:
        print(f"(´;ω;`) 发生错误: {e}")