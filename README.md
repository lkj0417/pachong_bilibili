# pachong 项目说明

## 功能简介

本项目包含用于批量下载 Bilibili 视频和自动整理本地 mp4 文件的 Python 脚本，主要功能如下：

- 使用 yt-dlp 批量下载 Bilibili 视频，支持 cookies 登录，自动记录下载日志，避免重复下载。
- 下载时自动选择最佳视频和音频并用 FFmpeg 合并为单个 mp4 文件。
- 自动整理下载的 mp4 文件，根据文件名规则归类到不同文件夹。
- 提供主控脚本，支持自动重试与异常处理。

## 依赖

- Python 3.x
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)（项目内已附带 `yt-dlp.exe`，也可通过 `pip install yt-dlp` 安装）
- FFmpeg（用于视频合并与转码，需配置环境变量）

## 用法

1. 准备 cookies.txt（从浏览器导出 Bilibili 登录 cookies），放在项目目录下即可。

2. 批量下载 Bilibili 视频：
   - 方式一：在 `urls.txt` 中每行填写一个视频 URL，然后运行：
     ```bash
     python yt-dlp_pachong.py
     ```
   - 方式二：直接通过命令行传入一个或多个 URL：
     ```bash
     python yt-dlp_pachong.py "https://www.bilibili.com/video/BV1xxxx"
     ```
   - 下载日志会自动保存到 `downloaded_files.txt`，重复运行时会跳过已下载的 URL。

3. 整理 mp4 文件：
   - 运行：
     ```bash
     python mp4_file_organizer.py
     ```
   - 脚本会按文件名中的 `[BV号]` 提取标题前缀，将 mp4 文件归类到对应文件夹。

4. 主控脚本自动重试：
   - 运行：
     ```bash
     python main.py
     ```
   - 会自动调用下载和整理脚本，并在失败时重试。Windows 下如 `python` 不可用，可改用 `py`。

5. 合并已有音视频文件：
   - 如果已经下载了分离的视频和音频文件，可运行：
     ```bash
     python merge_media.py
     ```
   - 脚本会按文件名中的 `[BV号]` 配对同一视频的视频和音频，并用 FFmpeg 合并为 `标题.merged.mp4`。
   - 合并成功后如需删除原始视频和音频，可加 `--delete-sources`：
     ```bash
     python merge_media.py --delete-sources
     ```

## 其他说明

- 下载日志保存在 `downloaded_files.txt`，避免重复下载。
- 文件整理规则基于文件名中的 `[BV号]`，如需调整可修改 `mp4_file_organizer.py`。
- 如果下载时提示 `HTTP Error 412`，通常是 `cookies.txt` 已失效，需要从浏览器重新导出 Bilibili 登录 cookies。

