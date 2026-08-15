# pachong_bilibili

基于 `yt-dlp` + `FFmpeg` 的 Bilibili 视频下载与整理工具，提供 Web 控制台和命令行脚本。

> 本项目仅用于个人学习与本地资料管理。请遵守 Bilibili 用户协议、版权要求和相关法律法规，不要下载或传播无权保存的内容。

## 主要功能

### Web 控制台

- 单视频、多 URL 批量下载
- 分 P、合集、课程、番剧等播放列表下载
- 课堂 `ep` 单集链接自动转换为整门课程 `ss` 链接
- 画质选择：最高 / 4K / 1080P / 720P / 480P
- 并发分片下载，默认 8 线程
- cookies 检测
- 实时任务状态、进度和日志
- 自动或手动整理 mp4
- 手动合并分离的音视频文件
- 暗色 / 亮色 / 天蓝三种主题

### 命令行脚本

- 批量下载
- 主控重试
- mp4 整理
- 音视频合并
- 合集目录扁平化
- 课程目录扁平化
- 音频转文字

## 目录结构

```text
pachong_bilibili/
  app.py                  # Flask Web 控制台入口
  config.json             # Web 配置文件（首次保存后生成）
  cookies.txt             # Bilibili 登录 cookies
  downloaded_files.txt    # 已下载 URL 记录
  yt-dlp.exe              # 本地 yt-dlp
  templates/index.html    # 页面模板
  static/app.js           # 前端逻辑
  static/style.css        # UI 样式
  yt-dlp_pachong.py       # 命令行下载脚本
  main.py                 # 命令行主控脚本
  mp4_file_organizer.py   # mp4 整理脚本
  merge_media.py          # 合并分离音视频
  flatten_collection.py   # 扁平化合集目录
  flatten_course.py       # 扁平化课程目录
  audio_to_text*.py       # 音频转文字脚本
```

## 环境依赖

- Python 3.x（推荐 3.11+）
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
  - 优先使用项目目录内的 `yt-dlp.exe`
  - 如果项目内没有，则使用系统 PATH 中的 `yt-dlp`
- FFmpeg
  - 在 Web 配置中指定路径，或加入系统 PATH
- Python 包：
  - `flask`
  - `requests`

安装基础依赖：

```powershell
pip install flask requests
```

可选：通过 pip 安装或更新 yt-dlp：

```powershell
pip install -U yt-dlp
```

可选：音频转文字依赖

Whisper：

```powershell
pip install openai-whisper
```

Google 语音识别：

```powershell
pip install SpeechRecognition pydub
```

## 快速启动 Web 控制台

```powershell
cd "项目目录"
python app.py
```

如果 Windows 上 `python` 不可用，可尝试：

```powershell
py app.py
```

启动后访问：

```text
http://127.0.0.1:5000/
```

## Web 使用流程

1. 准备 `cookies.txt`
   - 登录 `bilibili.com`
   - 使用浏览器扩展导出 Netscape 格式 cookies：
     - Chrome / Edge：`Get cookies.txt LOCALLY`
     - Firefox：`cookies.txt`
   - 保存到项目目录，或在 Web 配置中填写绝对路径

2. 打开页面，检查顶部状态：
   - yt-dlp
   - cookies
   - ffmpeg

3. 在配置面板确认：
   - cookies 文件
   - 输出目录
   - ffmpeg 路径
   - yt-dlp 路径
   - 下载完成后是否自动整理 mp4

4. 点击「检查 cookies」，确认 cookies 可用于下载。

5. 在下载区域填写 URL，每行一个。

6. 选择画质和并发线程。

7. 如需下载分 P、合集、课程，请勾选「下载整个合集 / 分P」。

8. 点击「开始下载」。

9. 在任务区域查看实时状态、进度、日志；日志支持复制。

## 配置文件 `config.json`

示例：

```json
{
  "cookies_path": "cookies.txt",
  "output_dir": "",
  "ffmpeg_location": "../ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
  "yt_dlp_path": "",
  "auto_organize": true
}
```

配置项：

| 配置项 | 默认值 | 说明 |
|---|---:|---|
| `cookies_path` | `cookies.txt` | cookies 文件路径，支持相对项目目录或绝对路径 |
| `output_dir` | 项目目录 | 下载输出目录，留空使用项目目录 |
| `ffmpeg_location` | 空 | `ffmpeg.exe` 或包含 `ffmpeg.exe` 的目录 |
| `yt_dlp_path` | 空 | `yt-dlp.exe` 路径；留空优先项目内 `yt-dlp.exe`，再找 PATH |
| `auto_organize` | `true` | 下载完成后自动整理 mp4 |

## 下载行为

单视频：

```text
-f bv*+ba/b
--merge-output-format mp4
--concurrent-fragments 8
```

播放列表 / 课程 / 番剧：

```text
--yes-playlist
```

输出模板：

- 单视频：`输出目录/%(title)s [%(id)s].%(ext)s`
- 播放列表：`输出目录/%(playlist_title)s/%(title)s.%(ext)s`

课堂 `ep` 链接：

- 程序会调用 Bilibili 接口，把 `cheese/play/epXXX` 自动转换为 `cheese/play/ssXXX`，从而下载整门课程。

## Web API 简表

| 方法 | 路径 | 功能 |
|---|---|---|
| `GET` | `/` | Web 控制台页面 |
| `GET` | `/api/health` | 检查 yt-dlp、cookies、ffmpeg、输出目录 |
| `GET` | `/api/config` | 读取配置 |
| `POST` | `/api/config` | 保存配置 |
| `POST` | `/api/cookies/check` | 检查 cookies 和下载访问能力 |
| `POST` | `/api/download` | 创建下载任务 |
| `GET` | `/api/tasks` | 获取任务队列 |
| `POST` | `/api/tasks/clear` | 清除已完成/失败/跳过/部分完成任务 |
| `GET` | `/api/files` | 获取输出目录文件列表 |
| `POST` | `/api/organize` | 整理 mp4 文件 |
| `POST` | `/api/merge` | 合并已有分离音视频 |
| `GET` | `/api/log` | 读取下载日志 |

## 命令行脚本用法

### 1. 命令行下载：`yt-dlp_pachong.py`

传 URL：

```powershell
python yt-dlp_pachong.py "https://www.bilibili.com/video/BVxxxx"
```

多个 URL：

```powershell
python yt-dlp_pachong.py "URL1" "URL2"
```

或创建 `urls.txt`，每行一个 URL，然后：

```powershell
python yt-dlp_pachong.py
```

特点：

- 自动读取项目内 `yt-dlp.exe`，否则找 PATH
- 自动查找 FFmpeg
- 存在 `cookies.txt` 时自动加 `--cookies`
- 使用 `downloaded_files.txt` 跳过已下载 URL
- 对合集 / 课程 / list / collection 链接自动启用 `--yes-playlist`

### 2. 主控脚本：`main.py`

```powershell
python main.py
```

作用：

- 先运行 `yt-dlp_pachong.py`
- 成功后运行 `mp4_file_organizer.py`
- 每个脚本失败时最多重试 3 次

### 3. 整理 mp4：`mp4_file_organizer.py`

```powershell
python mp4_file_organizer.py
```

作用：

- 扫描当前目录中的 mp4
- 多 P 文件名形如 `合集名 p01 xxx [BV...]` 时，移动到 `合集名/` 并重命名为 `p01 xxx.mp4`

### 4. 合并已有音视频：`merge_media.py`

```powershell
python merge_media.py
```

指定目录：

```powershell
python merge_media.py "目标目录"
```

预览模式：

```powershell
python merge_media.py "目标目录" --dry-run
```

合并后删除源文件：

```powershell
python merge_media.py "目标目录" --delete-sources
```

默认输出：

```text
标题.merged.mp4
```

### 5. 扁平化合集目录：`flatten_collection.py`

```powershell
python flatten_collection.py "目标目录"
```

预览：

```powershell
python flatten_collection.py "目标目录" --dry-run
```

作用：递归扫描 mp4，按 `[BV]` 规则归拢到合集文件夹。

### 6. 扁平化课程目录：`flatten_course.py`

```powershell
python flatten_course.py "目标目录"
```

预览：

```powershell
python flatten_course.py "目标目录" --dry-run
```

作用：识别课程分集目录，调用 Bilibili 课程接口获取课程标题，将分集 mp4 统一移动到课程文件夹。

### 7. 音频转文字

Whisper：

```powershell
python audio_to_text.py "音频文件路径"
python audio_to_text_whisper.py "音频文件路径"
```

Google 语音识别：

```powershell
python audio_to_text_simple.py "音频文件路径"
```

输出通常为：

```text
原文件名_转录.txt
```

## 常见问题

### 1. cookies 检查失败或下载 403 / 412

通常是 cookies 失效或格式不对。请重新登录 Bilibili，并用浏览器扩展导出 Netscape 格式 `cookies.txt`。

关键 cookies：

- `SESSDATA`
- `bili_jct`
- `DedeUserID`

### 2. 下载提示需要购买课程

这是 Bilibili 平台权限限制。即使 cookies 已登录，未购买的分集也无法下载，无法通过本工具绕过。

### 3. 重新提交相同 URL 被跳过

`downloaded_files.txt` 会记录已下载 URL。如需重新下载，请删除该文件中对应 URL 记录。

### 4. 服务重启后任务队列消失

任务队列保存在内存中，重启后清空；已下载文件、`downloaded_files.txt` 不受影响。

### 5. FFmpeg 未配置

在 Web 配置中填写：

- `ffmpeg.exe` 的完整路径
- 或包含 `ffmpeg.exe` 的目录
- 或留空，让程序尝试 PATH 和项目常见目录

### 6. Web 版和命令行版区别

Web 版功能更完整，支持任务队列、实时日志、画质选择、cookies 检查、主题切换、整理和合并操作。命令行版适合简单批处理。

## 注意事项

- `cookies.txt` 必须是 Netscape 格式，不是浏览器请求头里的 cookie 字符串。
- 音频转文字功能目前是独立脚本，未集成到 Web 页面。
- Windows 下文件名或目录名过长可能触发路径长度限制，建议输出目录设置得短一些。
- 下载公开视频不需要登录；下载会员/付费内容仍需账号具备相应权限。
