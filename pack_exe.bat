@echo off
rem 激活虚拟环境（如果有），若没有虚拟环境可注释或删除这行
rem call path\to\your\venv\Scripts\activate

rem 安装 PyInstaller（如果未安装）
pip install pyinstaller

rem 使用 PyInstaller 打包程序
pyinstaller --onefile --windowed src\gui_multithread_download.py

rem 提示打包完成
echo 打包完成！可在 dist 目录下找到生成的可执行文件。
pause