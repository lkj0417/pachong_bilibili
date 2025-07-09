# pachong 项目说明

## 功能简介

本项目包含用于批量下载 Bilibili 视频和自动整理本地 mp4 文件的 Python 脚本，主要功能如下：

- 使用 yt-dlp 批量下载 Bilibili 视频，支持 cookies 登录，自动记录下载日志，避免重复下载。
- 自动整理下载的 mp4 文件，根据文件名规则归类到不同文件夹。
- 提供主控脚本，支持自动重试与异常处理。

## 依赖

- Python 3.x
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- FFmpeg（用于视频合并与转码，需配置环境变量）

## 用法

1. 安装依赖：
   ```bash
   pip install yt-dlp
   ```
   并确保已安装 FFmpeg。

2. 下载 Bilibili 视频：
   - 准备 cookies.txt（从浏览器导出 Bilibili 登录 cookies）。
   - 修改 `yt-dlp_pachong.py` 中的 `url` 和 `cookies_path`。
   - 运行：
     ```bash
     python yt-dlp_pachong.py
     ```

3. 整理 mp4 文件：
   - 运行：
     ```bash
     python mp4_file_organizer.py
     ```
   - 脚本会自动将 mp4 文件按前缀归类到不同文件夹。

4. 主控脚本自动重试：
   - 运行：
     ```bash
     python main.py
     ```
   - 会自动调用下载和整理脚本，并在失败时重试。

## 其他说明

- 下载日志保存在 `downloaded_files.txt`，避免重复下载。
- 文件整理规则基于文件名中的 `-` 和 `p`，如需调整可修改 `mp4_file_organizer.py`。
- 若遇到下载失败或脚本异常，`main.py` 会自动重试并清理相关文件。

