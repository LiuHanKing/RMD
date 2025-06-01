import requests
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import os
import configparser
import time
import logging
# 删除 json 模块导入，因为不再需要保存断点信息

# 配置文件路径
conf_dir = os.path.join(os.path.dirname(__file__), 'conf')
if not os.path.exists(conf_dir):
    os.makedirs(conf_dir)
config_path = os.path.join(conf_dir, 'config.ini')

# 删除断点信息文件路径定义
# breakpoint_file = os.path.join(conf_dir, 'breakpoints.json')

config = configparser.ConfigParser()

# 配置日志
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 下载相关日志配置
download_log_file = os.path.join(log_dir, 'download.log')
download_logger = logging.getLogger('download')
# 指定编码为 utf-8
download_handler = logging.FileHandler(download_log_file, encoding='utf-8')
download_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
download_handler.setFormatter(download_formatter)
download_logger.addHandler(download_handler)
download_logger.setLevel(logging.INFO)

# 错误日志配置
error_log_file = os.path.join(log_dir, 'error.log')
error_logger = logging.getLogger('error')
# 指定编码为 utf-8
error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
error_handler.setFormatter(download_formatter)
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)

# 删除 download_log.txt 文件
download_log_txt = os.path.join(log_dir, 'download_log.txt')
if os.path.exists(download_log_txt):
    os.remove(download_log_txt)

# 添加一个标志位来控制下载的终止
stop_download = False

def convert_bytes(bytes_value):
    """将字节数转换为合适的单位"""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    while bytes_value >= 1024 and unit_index < len(units) - 1:
        bytes_value /= 1024
        unit_index += 1
    return f"{bytes_value:.2f} {units[unit_index]}"

def convert_speed(speed):
    """将下载速度转换为合适的单位"""
    units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s']
    unit_index = 0
    while speed >= 1024 and unit_index < len(units) - 1:
        speed /= 1024
        unit_index += 1
    return f"{speed:.2f} {units[unit_index]}"

# 添加线程锁
lock = threading.Lock()

# 修改 download_chunk 函数，移除断点保存逻辑
def download_chunk(url, start, end, filename, progress_bar, result_label, start_time, file_size):
    global stop_download
    headers = {'Range': f'bytes={start}-{end}'}
    update_interval = 1024 * 1024  # 每下载 1MB 更新一次界面
    update_counter = 0
    try:
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'r+b') as f:
                f.seek(start)
                for chunk in r.iter_content(chunk_size=1024):
                    if stop_download:
                        break
                    if chunk:
                        f.write(chunk)
                        def update_progress():
                            with lock:
                                progress_bar['value'] += len(chunk)
                        root.after(0, update_progress)
                        update_counter += len(chunk)

                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0 and update_counter >= update_interval:
                            def update_label_text():
                                with lock:
                                    formatted_downloaded = convert_bytes(progress_bar['value'])
                                    formatted_remaining = convert_bytes(file_size - progress_bar['value'])
                                    download_speed = progress_bar['value'] / elapsed_time
                                    formatted_speed = convert_speed(download_speed)
                                    remaining_size = file_size - progress_bar['value']
                                    remaining_time = remaining_size / download_speed if download_speed > 0 else 0

                            # 将剩余时间转换为秒、分、时的格式
                            if remaining_time < 60:
                                formatted_remaining_time = f"{remaining_time:.2f} 秒"
                            elif remaining_time < 3600:
                                minutes = remaining_time // 60
                                seconds = remaining_time % 60
                                formatted_remaining_time = f"{minutes:.0f} 分 {seconds:.2f} 秒"
                            else:
                                hours = remaining_time // 3600
                                remaining_minutes = (remaining_time % 3600)
                                minutes = remaining_minutes // 60
                                seconds = remaining_minutes % 60
                                formatted_remaining_time = f"{hours:.0f} 时 {minutes:.0f} 分 {seconds:.2f} 秒"

                            result_label.config(text=f"已下载 {formatted_downloaded}，下载速度: {formatted_speed}，剩余 {formatted_remaining}，剩余时间: {formatted_remaining_time}")
                            root.after(0, update_label_text)
                            update_counter = 0
    except Exception as e:
        def update_error_label():
            result_label.config(text=f"下载线程出错: {str(e)}")
        root.after(0, update_error_label)
        error_logger.error(f"URL: {url}, 保存路径: {filename}, 错误信息: {str(e)}")

# 添加 update_label 函数定义
def update_label(text):
    result_label.config(text=text)

# 修改 download_file 函数，移除断点检查逻辑
def download_file(url, filename, num_threads=4):
    global stop_download
    start_time = time.time()
    try:
        r = requests.head(url)
        # 检查服务器是否支持分块下载
        accept_ranges = r.headers.get('Accept-Ranges', 'none')
        if accept_ranges != 'bytes':
            num_threads = 1
            root.after(0, update_label, "服务器不支持分块下载，将使用单线程下载。")

        file_size = int(r.headers.get('Content-Length', 0))
        if file_size == 0:
            root.after(0, update_label, "无法获取文件大小，请检查 URL 是否正确。")
            error_logger.error(f"URL: {url}, 保存路径: {filename}, 错误信息: 无法获取文件大小，请检查 URL 是否正确。")
            return
        
        # 显示文件大小
        formatted_file_size = convert_bytes(file_size)
        root.after(0, update_label, f"文件大小: {formatted_file_size}，开始下载...")

        progress_bar['maximum'] = file_size
        
        print(f"尝试打开文件: {filename}")  # 添加调试信息
        try:
            with open(filename, 'ab'):  # 以追加模式打开文件
                pass
        except Exception as open_error:
            print(f"打开文件时出错: {open_error}")  # 添加调试信息
            root.after(0, update_label, f"打开文件时出错: {open_error}")
            error_logger.error(f"URL: {url}, 保存路径: {filename}, 错误信息: 打开文件时出错: {open_error}")
            return

        chunk_size = file_size // num_threads
        threads = []
        for i in range(num_threads):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < num_threads - 1 else file_size - 1
            # 确保请求的范围在文件大小之内
            if start >= file_size:
                continue
            if end >= file_size:
                end = file_size - 1
            t = threading.Thread(target=download_chunk, args=(url, start, end, filename, progress_bar, result_label, start_time, file_size))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        
    except Exception as e:
        root.after(0, update_label, f"下载出错: {str(e)}")
        error_logger.error(f"URL: {url}, 保存路径: {filename}, 错误信息: {str(e)}")
    finally:
        elapsed_time = time.time() - start_time
        if not stop_download:
            root.after(0, update_label, f"文件下载完成，耗时: {elapsed_time:.2f} 秒。")
        else:
            root.after(0, update_label, "下载已终止。")

def start_download():
    url = url_entry.get()
    save_dir = file_entry.get()
    print(f"获取到的保存目录: {save_dir}")
    if not save_dir:
        result_label.config(text="请先设置保存路径再进行下载。")
        return
    
    # 从 URL 中提取文件名
    filename = url.split("/")[-1].split("?")[0]
    if not filename:
        filename = "downloaded_file"
    
    # 确保 save_dir 是目录路径
    if os.path.isfile(save_dir):
        save_dir = os.path.dirname(save_dir)
    
    # 处理同名文件
    counter = 1
    original_filename = filename
    file_path = os.path.join(save_dir, filename)
    while os.path.exists(file_path):
        name, ext = os.path.splitext(original_filename)
        filename = f"{name}_{counter}{ext}"
        file_path = os.path.join(save_dir, filename)
        counter += 1
    
    print(f"最终确定的文件路径: {file_path}")
    
    # 检查保存目录是否存在，如果不存在则创建
    if not os.path.exists(save_dir):
        try:
            os.makedirs(save_dir, exist_ok=True)
            print(f"已成功创建保存路径: {save_dir}")
            download_logger.info(f"已成功创建保存路径: {save_dir}")
        except OSError as e:
            result_label.config(text=f"创建保存路径失败: {str(e)}")
            error_logger.error(f"URL: {url}, 保存路径: {file_path}, 错误信息: 创建保存路径失败: {str(e)}")
            return

    if url and save_dir:
        # 保存配置
        config['DEFAULT'] = {
            'url': url,
            'filename': file_path
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        
        # 记录下载日志到 download.log
        download_logger.info(f"开始下载，URL: {url}, 保存路径: {file_path}")

        download_thread = threading.Thread(target=download_file, args=(url, file_path))
        download_thread.start()

# 读取配置
if os.path.exists(config_path):
    config.read(config_path)
    default_config = config['DEFAULT']
    default_url = default_config.get('url', '')
    default_filename = default_config.get('filename', '')
else:
    default_url = ''
    default_filename = ''

# 创建主窗口
root = tk.Tk()
root.title("多线程下载工具")

# 创建输入框和标签
url_label = tk.Label(root, text="下载链接:")
url_label.pack()
url_entry = tk.Entry(root, width=50)
url_entry.pack()

file_label = tk.Label(root, text="保存路径:")
file_label.pack()
file_entry = tk.Entry(root, width=50)
file_entry.pack()

# 添加 select_file 函数
def select_file():
    directory = filedialog.askdirectory()
    if directory:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, directory)

select_button = tk.Button(root, text="选择保存路径", command=select_file)
select_button.pack()

start_button = tk.Button(root, text="开始下载", command=start_download)
start_button.pack()

progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack()

result_label = tk.Label(root, text="")
result_label.pack()

def stop_download_function():
    global stop_download
    stop_download = True
    result_label.config(text="下载已终止。")
    stop_button.pack_forget()  # 隐藏中止下载按钮
    continue_button.pack()  # 显示继续下载按钮

    # 获取当前下载的文件路径
    url = url_entry.get()
    save_dir = file_entry.get()
    filename = url.split("/")[-1].split("?")[0]
    if not filename:
        filename = "downloaded_file"
    file_path = os.path.join(save_dir, filename)

    # 检查文件是否存在，如果存在则删除
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"已删除未下载完的文件: {file_path}")
            download_logger.info(f"已删除未下载完的文件: {file_path}")
        except Exception as e:
            print(f"删除文件时出错: {str(e)}")
            error_logger.error(f"删除文件 {file_path} 时出错: {str(e)}")

def continue_download():
    global stop_download
    stop_download = False
    url = url_entry.get()
    save_dir = file_entry.get()
    # 从 URL 中提取文件名
    filename = url.split("/")[-1].split("?")[0]
    if not filename:
        filename = "downloaded_file"
    file_path = os.path.join(save_dir, filename)
    download_thread = threading.Thread(target=download_file, args=(url, file_path))
    download_thread.start()
    continue_button.pack_forget()  # 隐藏继续下载按钮
    stop_button.pack()  # 显示中止下载按钮

stop_button = tk.Button(root, text="中止下载", command=stop_download_function)
# 初始状态下隐藏中止下载按钮
stop_button.pack_forget()

# 确保继续下载按钮被正确创建
continue_button = tk.Button(root, text="继续下载", command=continue_download)
# 初始状态下隐藏继续下载按钮
continue_button.pack_forget()

# 初始化继续下载按钮，初始状态为隐藏（使用 pack_forget 隐藏）
continue_button = tk.Button(root, text="继续下载", command=continue_download)
continue_button.pack_forget()

stop_button = tk.Button(root, text="终止下载", command=stop_download_function)
stop_button.pack()

from tkinter import messagebox

# 定义 on_closing 函数
def on_closing():
    global stop_download
    if any(thread.is_alive() for thread in threading.enumerate() if thread.name != 'MainThread'):
        response = messagebox.askyesno("确认关闭", "正在下载文件，是否终止下载并关闭程序？")
        if response:
            stop_download = True
            # 可以在这里添加保存断点信息等操作
            root.destroy()
    else:
        root.destroy()

# 在退出程序时停止下载
root.protocol("WM_DELETE_WINDOW", on_closing)

# 添加新的文字标签
new_text_label = tk.Label(root, text="https://github.com/LiuHanKing/RMD.git")
new_text_label.pack(pady=10)

# 删除调用检查断点的函数这一行
# check_breakpoints()

# 运行主循环
root.mainloop()