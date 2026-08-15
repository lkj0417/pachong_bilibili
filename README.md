# Bilibili 爬虫控制台 / pachong_bilibili

这是一个基于 `yt-dlp` + `FFmpeg` 的 Bilibili 下载与整理工具，当前主要入口是 Flask Web 控制台，同时保留若干命令行脚本用于批量下载、文件整理、音视频合并和音频转文字。

> 本项目仅用于个人学习与本地资料管理。请遵守 Bilibili 用户协议、版权要求和相关法律法规，不要下载或传播无权保存的内容。

## 主要功能

- Web 控制台下载 Bilibili 视频：
  - 支持单视频、多 URL 批量下载。
  - 支持分 P、合集、课程、番剧等 playlist 类型链接。
  - 支持课程 `ep` 单集链接自动转换为整门课程 `ss` 链接。
  - 支持画质选择：最高画质、2160p、1080p、720p、480p。
  - 支持并发分片下载，默认 `8`，范围 `1-32`。
- 使用 `cookies.txt` 登录下载，并提供 cookies 可用性检测。
- 自动调用 FFmpeg 合并音视频为 `mp4`。
- 下载任务实时显示状态、进度、日志、解析出的合集名/视频名和 URL。
- 下载失败或“部分完成”时支持自动修复和手动“检测并修复”。
- 支持 `yt-dlp` / FFmpeg 版本检查与一键更新。
- 支持下载完成后自动整理 mp4。
- 支持手动整理 mp4、手动合并已有分离音视频。
- 保留命令行脚本，适合简单批处理或单独运行某个工具。

## 目录说明

```text
pachong_bilibili/
  app.py                    # Flask Web 控制台入口
  config.json               # Web 配置文件
  cookies.txt               # Bilibili 登录 cookies（需自行导出）
  downloaded_files.txt      # 已下载 URL 记录
  yt_dlp_archive.txt        # yt-dlp 分集归档，自动修复时用于跳过已完成分集
  yt-dlp.exe                # Windows 下可选的本地 yt-dlp 可执行文件
  templates/index.html      # Web 页面模板
  static/app.js             # Web 前端交互逻辑
  static/style.css          # Web UI 样式
  yt-dlp_pachong.py         # 命令行下载脚本
  main.py                   # 命令行主控脚本
  mp4_file_organizer.py     # mp4 整理脚本
  merge_media.py            # 分离音视频合并脚本
  flatten_collection.py     # 递归扁平化合集目录
  flatten_course.py         # 课程目录扁平化
  audio_to_text*.py         # 音频转文字相关脚本
```

## 运行环境与依赖

### 基础依赖

- Python 3.11+（推荐）
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
  - 优先使用项目目录内的 `yt-dlp.exe`。
  - 如果项目内没有，则使用系统 PATH 中的 `yt-dlp`。
- FFmpeg
  - 可在 `config.json` 或 Web 页面中配置 `ffmpeg.exe` 路径。
  - 也可以放在 `../ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe`。
  - 或安装到系统 PATH。
- Python 包：
  - `flask`
  - `requests`

安装基础 Python 依赖：

```powershell
cd "C:\Users\lkj04\Desktop\project\pachong\pachong_bilibili"
pip install flask requests
```

如果需要通过 pip 安装 `yt-dlp`：

```powershell
pip install -U yt-dlp
```

### 可选依赖：音频转文字

Whisper 版本：

```powershell
pip install openai-whisper
```

Google 语音识别版本：

```powershell
pip install SpeechRecognition pydub
```

## 快速启动 Web 控制台

```powershell
cd "C:\Users\lkj04\Desktop\project\pachong\pachong_bilibili"
python app.py
```

如果 Windows 上 `python` 不可用，可以尝试：

```powershell
py app.py
```

启动后访问：

```text
http://127.0.0.1:5000/
```

默认启动参数：

- Host：`127.0.0.1`
- Port：`5000`
- Debug：关闭
- Threaded：开启

## Web 控制台使用流程

1. 准备 `cookies.txt`
   - 登录 `bilibili.com`。
   - 使用浏览器扩展导出 Netscape 格式 cookies：
     - Chrome / Edge：`Get cookies.txt LOCALLY`
     - Firefox：`cookies.txt`
   - 将文件保存为项目目录下的 `cookies.txt`，或在 Web 配置里填写绝对路径。

2. 打开 Web 页面，检查顶部状态：
   - `yt-dlp`
   - `cookies`
   - `ffmpeg`

3. 在“配置中心”确认：
   - cookies 文件路径
   - 输出目录
   - FFmpeg 路径
   - yt-dlp 路径
   - 下载完成后是否自动整理 mp4
   - 部分完成时是否自动修复缺失分集
   - 修复重试次数

4. 点击“检查 cookies”，确认 cookies 可用。

5. 在“下载视频”区域填写 URL：
   - 每行一个 URL。
   - 合集 / 分 P / 课程建议勾选“下载整个合集 / 分P”。
   - 选择画质和并发线程。

6. 点击“开始下载”。

7. 在“任务队列”查看：
   - 状态徽章
   - 解析出的合集名或视频名
   - URL
   - 进度条
   - 当前消息
   - 详细日志
   - 失败或部分完成任务的“检测并修复”按钮

## 配置文件 `config.json`

示例：

```json
{
  "cookies_path": "cookies.txt",
  "output_dir": "C:\\Users\\lkj04\\Desktop\\project\\pachong\\pachong_bilibili",
  "ffmpeg_location": "../ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
  "yt_dlp_path": "",
  "auto_organize": true,
  "auto_repair_partial": true,
  "partial_repair_attempts": 3
}
```

常用配置项：

| 配置项 | 默认值 | 说明 |
|---|---:|---|
| `cookies_path` | `cookies.txt` | cookies 文件路径，支持相对项目目录或绝对路径 |
| `output_dir` | 项目目录 | 下载输出目录 |
| `ffmpeg_location` | 空 | `ffmpeg.exe` 或包含 `ffmpeg.exe` 的目录 |
| `yt_dlp_path` | 空 | `yt-dlp.exe` 路径；空则优先项目内 `yt-dlp.exe`，再找 PATH |
| `auto_organize` | `true` | 下载完成后自动整理 mp4 |
| `auto_repair_partial` | `true` | 合集部分完成时自动修复缺失分集 |
| `partial_repair_attempts` | `3` | 自动修复重试次数，范围 `0-10` |

内部可选配置项：

| 配置项 | 说明 |
|---|---|
| `download_archive` | yt-dlp 下载归档路径；未配置时使用 `yt_dlp_archive.txt` |
| `cookies_test_url` | cookies 下载测试 URL |
| `ffmpeg_release_name` | FFmpeg 更新后保存的 release 文件名 |
| `ffmpeg_release_updated_at` | FFmpeg 更新后保存的远程更新时间，用于判断是否有新构建 |

## 下载、归档与自动修复机制

Web 下载命令会包含更稳健的网络重试参数：

- `--retries 15`
- `--fragment-retries 15`
- `--retry-sleep 5`
- `--socket-timeout 30`
- `--concurrent-fragments <并发数>`
- `--merge-output-format mp4`

合集 / 分 P 下载会启用：

- `--yes-playlist`
- `--download-archive yt_dlp_archive.txt`

归档文件会记录已经成功下载的分集。后续修复时，`yt-dlp` 会自动跳过已完成分集，只补失败或缺失的分集。

输出模板：

- 合集：`输出目录/%(playlist_title)s/%(title)s.%(ext)s`
- 单视频：`输出目录/%(title)s [%(id)s].%(ext)s`

当下载返回非 0，但日志中出现类似“合集已下载完但部分分集失败”的情况时，任务会进入“部分完成”。如果开启自动修复，程序会：

1. 从日志中识别疑似失败分集，例如 `p85 / 120`。
2. 使用归档跳过已完成分集。
3. 按配置的重试次数重新执行下载。
4. 修复成功后将任务状态改为“完成”。
5. 多次修复失败后保留“部分完成”，可在 Web 页面点击“检测并修复”。

## 工具版本检查与更新

Web 页面“工具版本”区域支持检查和更新 `yt-dlp` / FFmpeg。

### yt-dlp

检查本地版本：

```powershell
yt-dlp --version
```

更新方式：

```powershell
yt-dlp -U
```

### FFmpeg

自动更新当前仅支持 Windows。

更新逻辑：

1. 从 GitHub `BtbN/FFmpeg-Builds` 查询 `latest`。
2. 下载 `ffmpeg-master-latest-win64-gpl.zip`。
3. 安全解压并查找 `bin/ffmpeg.exe`。
4. 覆盖到项目管理目录，默认：`../ffmpeg-master-latest-win64-gpl`。
5. 写入 `config.json`：
   - `ffmpeg_location`
   - `ffmpeg_release_name`
   - `ffmpeg_release_updated_at`

## Web API 简表

| 方法 | 路径 | 功能 |
|---|---|---|
| `GET` | `/` | Web 控制台页面 |
| `GET` | `/api/health` | 检查 yt-dlp、cookies、ffmpeg、输出目录 |
| `GET` | `/api/tools/status?remote=1` | 检查工具本地状态和远程最新版本 |
| `POST` | `/api/tools/yt-dlp/update` | 更新 yt-dlp |
| `POST` | `/api/tools/ffmpeg/update` | 更新 FFmpeg |
| `GET` | `/api/config` | 读取配置 |
| `POST` | `/api/config` | 保存配置 |
| `POST` | `/api/cookies/check` | 检查 cookies 和下载访问能力 |
| `POST` | `/api/download` | 创建下载任务 |
| `GET` | `/api/tasks` | 获取任务队列 |
| `POST` | `/api/tasks/<task_id>/repair` | 检测并修复失败/部分完成任务 |
| `POST` | `/api/tasks/clear` | 清除已完成/失败/跳过/部分完成任务 |
| `GET` | `/api/files` | 获取输出目录文件列表 |
| `POST` | `/api/organize` | 整理 mp4 文件 |
| `POST` | `/api/merge` | 合并已有分离音视频 |
| `GET` | `/api/log` | 读取下载日志 |

## 命令行脚本用法

### 1. 命令行下载：`yt-dlp_pachong.py`

方式一：命令行传 URL：

```powershell
python yt-dlp_pachong.py "https://www.bilibili.com/video/BVxxxx"
```

多个 URL：

```powershell
python yt-dlp_pachong.py "URL1" "URL2"
```

方式二：创建 `urls.txt`，每行一个 URL，然后运行：

```powershell
python yt-dlp_pachong.py
```

特点：

- 自动读取项目内 `yt-dlp.exe`，否则找 PATH。
- 自动查找 FFmpeg。
- 存在 `cookies.txt` 时自动加 `--cookies`。
- 使用 `downloaded_files.txt` 跳过已下载 URL。
- 对合集/课程/list/collection 链接自动启用 `--yes-playlist`。

### 2. 主控脚本：`main.py`

```powershell
python main.py
```

作用：

- 先运行 `yt-dlp_pachong.py`。
- 成功后运行 `mp4_file_organizer.py`。
- 每个脚本失败时最多重试 3 次。

### 3. 整理 mp4：`mp4_file_organizer.py`

```powershell
python mp4_file_organizer.py
```

作用：

- 扫描当前目录中的 mp4。
- 按文件名规则移动到对应文件夹。
- 多 P 文件名形如 `合集名 p01 xxx [BV...]` 时，会移动到 `合集名/` 并重命名。

### 4. 合并已有音视频：`merge_media.py`

默认扫描当前目录：

```powershell
python merge_media.py
```

指定目录：

```powershell
python merge_media.py "目标目录"
```

只预览不执行：

```powershell
python merge_media.py "目标目录" --dry-run
```

合并后删除源视频/音频：

```powershell
python merge_media.py "目标目录" --delete-sources
```

默认输出文件名：

```text
标题.merged.mp4
```

### 5. 扁平化合集目录：`flatten_collection.py`

```powershell
python flatten_collection.py "目标目录"
```

预览模式：

```powershell
python flatten_collection.py "目标目录" --dry-run
```

作用：递归扫描目标目录下的 mp4，按整理规则移动到统一合集文件夹，并清理空目录。

### 6. 扁平化课程目录：`flatten_course.py`

```powershell
python flatten_course.py "目标目录"
```

预览模式：

```powershell
python flatten_course.py "目标目录" --dry-run
```

作用：识别课程分集目录，调用 Bilibili 课程 API 获取课程标题，并将分集 mp4 移动到课程标题文件夹。

### 7. 音频转文字

Whisper 版本：

```powershell
python audio_to_text.py "音频文件路径"
python audio_to_text_whisper.py "音频文件路径"
```

Google 语音识别版本：

```powershell
python audio_to_text_simple.py "音频文件路径"
```

输出文件通常为：

```text
原文件名_转录.txt
```

## 常见问题

### 1. cookies 检查失败或下载 403 / 412

通常是 cookies 失效或格式不对。请重新登录 Bilibili，并用浏览器扩展导出 Netscape 格式 `cookies.txt`。

关键 cookies 包括：

- `SESSDATA`
- `bili_jct`
- `DedeUserID`

### 2. 重新提交相同 URL 被跳过

`downloaded_files.txt` 会记录已下载 URL。若确实需要重新下载，请删除该文件中对应 URL 记录。

### 3. 合集部分完成

优先使用 Web 页面任务卡片里的“检测并修复”。程序会使用 `yt_dlp_archive.txt` 跳过已完成分集，只补缺失分集。

### 4. 服务重启后任务队列消失

任务队列保存在内存中，重启服务后会清空；下载文件、`downloaded_files.txt` 和 `yt_dlp_archive.txt` 不会因此删除。

### 5. FFmpeg 未配置

可以在 Web 配置里填写以下任一形式：

- `ffmpeg.exe` 的完整路径。
- 包含 `ffmpeg.exe` 的目录。
- 留空，让程序尝试 PATH 和项目常见目录。

### 6. Web 版和命令行版有什么区别

Web 版功能更完整，支持任务队列、实时日志、画质选择、cookies 检查、自动修复、工具更新等。命令行版适合简单批量下载和自动整理。

## 注意事项

- `cookies.txt` 必须是 Netscape 格式，不是浏览器请求头里的 cookie 字符串。
- `yt-dlp` 和 FFmpeg 更新需要访问 GitHub。
- FFmpeg 自动更新目前仅支持 Windows。
- 音频转文字功能是独立脚本，未集成到 Web 页面。
- 如果文件名或目录名过长，Windows 下可能遇到路径长度限制，建议将输出目录设置得短一些。

