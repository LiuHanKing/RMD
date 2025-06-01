import requests
import threading

def download_chunk(url, start, end, filename):
    headers = {'Range': f'bytes={start}-{end}'}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'r+b') as f:
            f.seek(start)
            f.write(r.content)

def download_file(url, filename, num_threads=4):
    r = requests.head(url)
    file_size = int(r.headers.get('Content-Length', 0))
    if file_size == 0:
        print("无法获取文件大小，请检查 URL 是否正确。")
        return
    with open(filename, 'wb') as f:
        f.truncate(file_size)

    chunk_size = file_size // num_threads
    threads = []
    for i in range(num_threads):
        start = i * chunk_size
        end = start + chunk_size - 1 if i < num_threads - 1 else file_size - 1
        t = threading.Thread(target=download_chunk, args=(url, start, end, filename))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    print("文件下载完成。")

if __name__ == '__main__':
    while True:
        url = input("请输入要下载的文件的 URL: ")
        if url.startswith('http://') or url.startswith('https://'):
            break
        else:
            print("输入的 URL 缺少协议头，请添加 'http://' 或 'https://'。")
    filename = input("请输入保存的文件名: ")
    download_file(url, filename)