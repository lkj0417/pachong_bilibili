import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, render_template, request

import merge_media
import mp4_file_organizer


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DOWNLOAD_LOG = os.path.join(BASE_DIR, "downloaded_files.txt")
DOWNLOAD_ARCHIVE = os.path.join(BASE_DIR, "yt_dlp_archive.txt")

app = Flask(__name__)

tasks = {}
tasks_lock = threading.Lock()

DEFAULT_CONFIG = {
    "cookies_path": "cookies.txt",
    "output_dir": BASE_DIR,
    "ffmpeg_location": "",
    "yt_dlp_path": "",
    "auto_organize": True,
    "auto_repair_partial": True,
    "partial_repair_attempts": 3,
}

PROGRESS_RE = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")
PLAYLIST_ITEM_RE = re.compile(r"\[download\]\s+Downloading item\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
TITLE_META_PREFIX = "__PACHONG_TITLE__\t"
COOKIE_KEYS = ["SESSDATA", "bili_jct", "DedeUserID"]
DEFAULT_COOKIE_TEST_URL = "https://www.bilibili.com/video/BV1xx411c7mD"
QUALITY_FORMATS = {
    "best": "bv*+ba/b",
    "2160p": "bv*[height<=2160]+ba/b",
    "1080p": "bv*[height<=1080]+ba/b",
    "720p": "bv*[height<=720]+ba/b",
    "480p": "bv*[height<=480]+ba/b",
}
PLAYLIST_URL_PATTERNS = [
    r"bilibili\.com/(cheese|bangumi)/play/ss",
    r"bilibili\.com/list/",
    r"space\.bilibili\.com/.*/channel/collectiondetail",
    r"space\.bilibili\.com/.*/lists/",
]
CHEESE_EP_PATTERN = re.compile(r"bilibili\.com/cheese/play/ep(\d+)", re.IGNORECASE)
YTDLP_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
FFMPEG_RELEASE_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest"
FFMPEG_ASSET_NAME = "ffmpeg-master-latest-win64-gpl.zip"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "pachong-bilibili-updater",
}


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def resolve_path(path):
    if not path:
        return ""
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (OSError, json.JSONDecodeError):
            config = {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(config)
    return merged


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_output_dir(config):
    return resolve_path(config.get("output_dir")) or BASE_DIR


def clamp_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def get_partial_repair_attempts(config):
    return clamp_int(config.get("partial_repair_attempts"), 3, 0, 10)


def get_download_archive_path(config):
    archive = config.get("download_archive") or DOWNLOAD_ARCHIVE
    return resolve_path(archive) if not os.path.isabs(archive) else archive


def get_yt_dlp_path(config):
    if config.get("yt_dlp_path"):
        return resolve_path(config["yt_dlp_path"])
    local = os.path.join(BASE_DIR, "yt-dlp.exe")
    return local if os.path.exists(local) else "yt-dlp"


def resolve_executable(command):
    if not command:
        return ""
    if os.path.isfile(command):
        return os.path.abspath(command)
    found = shutil.which(command)
    return found or ""


def run_command_output(cmd, timeout=20):
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": "找不到可执行文件"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": "命令执行超时"}


def version_tuple(value):
    numbers = re.findall(r"\d+", str(value or ""))[:4]
    return tuple(int(item) for item in numbers)


def parse_github_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def file_mtime_iso(path):
    if not path or not os.path.exists(path):
        return ""
    return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat(timespec="seconds")


def github_get_json(url):
    response = requests.get(url, headers=GITHUB_HEADERS, timeout=20)
    response.raise_for_status()
    return response.json()


def latest_yt_dlp_release():
    data = github_get_json(YTDLP_RELEASE_API)
    tag = str(data.get("tag_name") or "").lstrip("v")
    return {
        "version": tag,
        "name": data.get("name") or tag,
        "url": data.get("html_url") or "https://github.com/yt-dlp/yt-dlp/releases/latest",
        "published_at": data.get("published_at") or "",
    }


def latest_ffmpeg_release():
    data = github_get_json(FFMPEG_RELEASE_API)
    assets = data.get("assets") or []
    asset = next((item for item in assets if item.get("name") == FFMPEG_ASSET_NAME), None)
    if not asset:
        asset = next(
            (
                item
                for item in assets
                if "win64" in item.get("name", "") and "gpl" in item.get("name", "") and item.get("name", "").endswith(".zip")
            ),
            None,
        )
    if not asset:
        raise RuntimeError("未在 FFmpeg-Builds 最新发布中找到 Windows GPL zip 资源")
    return {
        "tag": data.get("tag_name") or "latest",
        "name": asset.get("name") or FFMPEG_ASSET_NAME,
        "url": data.get("html_url") or "https://github.com/BtbN/FFmpeg-Builds/releases/tag/latest",
        "download_url": asset.get("browser_download_url"),
        "updated_at": asset.get("updated_at") or data.get("published_at") or "",
        "size": asset.get("size") or 0,
    }


def get_yt_dlp_status(config, include_remote=False):
    configured = get_yt_dlp_path(config)
    executable = resolve_executable(configured)
    version_result = run_command_output([executable or configured, "--version"], timeout=15) if (executable or configured) else {}
    local_version = (version_result.get("stdout") or "").splitlines()[0] if version_result.get("stdout") else ""
    status = {
        "configured": configured,
        "path": executable or configured,
        "ok": bool(executable and version_result.get("ok")),
        "version": local_version,
        "latest": None,
        "update_available": False,
        "can_update": bool(executable or configured),
        "message": version_result.get("stderr") or "",
    }
    if include_remote:
        try:
            latest = latest_yt_dlp_release()
            status["latest"] = latest
            if local_version and latest.get("version"):
                status["update_available"] = version_tuple(latest["version"]) > version_tuple(local_version)
        except Exception as exc:
            status["latest_error"] = str(exc)
    return status


def get_ffmpeg_install_root(ffmpeg_path):
    if ffmpeg_path:
        current = os.path.abspath(os.path.dirname(ffmpeg_path))
        while current and current != os.path.dirname(current):
            if os.path.basename(current).lower() == "ffmpeg-master-latest-win64-gpl":
                return current
            current = os.path.dirname(current)
    return os.path.abspath(os.path.join(BASE_DIR, "..", "ffmpeg-master-latest-win64-gpl"))


def get_ffmpeg_status(config, include_remote=False):
    ffmpeg_path = get_ffmpeg_path(config)
    version_result = run_command_output([ffmpeg_path, "-version"], timeout=15) if ffmpeg_path else {}
    first_line = (version_result.get("stdout") or "").splitlines()[0] if version_result.get("stdout") else ""
    status = {
        "path": ffmpeg_path,
        "ok": bool(ffmpeg_path and version_result.get("ok")),
        "version": first_line,
        "latest": None,
        "update_available": False,
        "can_update": os.name == "nt",
        "managed_root": get_ffmpeg_install_root(ffmpeg_path),
        "local_mtime": file_mtime_iso(ffmpeg_path),
        "message": version_result.get("stderr") or "",
    }
    if include_remote:
        try:
            latest = latest_ffmpeg_release()
            status["latest"] = latest
            remote_time = parse_github_time(latest.get("updated_at"))
            local_time = datetime.fromtimestamp(os.path.getmtime(ffmpeg_path), tz=timezone.utc) if ffmpeg_path and os.path.exists(ffmpeg_path) else None
            saved_remote = config.get("ffmpeg_release_updated_at")
            if saved_remote:
                status["update_available"] = saved_remote != latest.get("updated_at")
            else:
                status["update_available"] = bool(remote_time and (not ffmpeg_path or (local_time and remote_time > local_time)))
        except Exception as exc:
            status["latest_error"] = str(exc)
    return status


def tools_status(config, include_remote=False):
    return {
        "yt_dlp": get_yt_dlp_status(config, include_remote=include_remote),
        "ffmpeg": get_ffmpeg_status(config, include_remote=include_remote),
    }


def safe_extract_zip(zip_path, target_dir):
    target_dir = os.path.abspath(target_dir)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            destination = os.path.abspath(os.path.join(target_dir, member.filename))
            if not destination.startswith(target_dir + os.sep) and destination != target_dir:
                raise RuntimeError("压缩包包含不安全路径，已取消解压")
        archive.extractall(target_dir)


def find_extracted_ffmpeg_root(extract_dir):
    for root, _, files in os.walk(extract_dir):
        if "ffmpeg.exe" in files and os.path.basename(root).lower() == "bin":
            return os.path.dirname(root)
    raise RuntimeError("压缩包中未找到 bin\\ffmpeg.exe")


def download_file(url, destination):
    with requests.get(url, stream=True, headers=GITHUB_HEADERS, timeout=(10, 120)) as response:
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def get_cookies_path(config):
    path = config.get("cookies_path")
    if not path:
        return None
    full = resolve_path(path)
    return full if os.path.exists(full) else None


def parse_netscape_cookies(path):
    cookies = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Netscape 格式中 #HttpOnly_ 前缀表示 HttpOnly cookie，后面仍是有效字段
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly_"):]
            elif line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            try:
                expires = int(parts[4])
            except ValueError:
                expires = 0
            cookies.append(
                {
                    "domain": parts[0],
                    "name": parts[5],
                    "value": parts[6],
                    "expires": expires,
                }
            )
    return cookies


def live_check_bilibili(cookies_by_name):
    cookie_header = "; ".join(f"{item['name']}={item['value']}" for item in cookies_by_name.values())
    try:
        response = requests.get(
            "https://api.bilibili.com/x/web-interface/nav",
            headers={
                "Cookie": cookie_header,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
            timeout=10,
        )
        data = response.json()
        profile = data.get("data") or {}
        return {
            "ok": True,
            "code": data.get("code"),
            "logged_in": bool(profile.get("isLogin")),
            "uname": profile.get("uname", ""),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_download_access(url, config, cookies_path):
    yt_dlp = get_yt_dlp_path(config)
    cmd = [
        yt_dlp,
        "--skip-download",
        "--no-warnings",
        "--cookies",
        cookies_path,
        "--print",
        "%(id)s",
        url,
    ]
    ffmpeg_path = get_ffmpeg_path(config)
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "下载测试超时"}
    except FileNotFoundError:
        return {"ok": False, "message": "找不到 yt-dlp"}

    if proc.returncode == 0:
        return {"ok": True, "message": "下载访问正常"}

    error = (proc.stderr or "").strip()
    if "412" in error or "Precondition Failed" in error:
        return {"ok": False, "message": "服务器拒绝访问（HTTP 412），cookies 无法用于下载", "error": error[-500:]}
    if "403" in error or "Forbidden" in error:
        return {"ok": False, "message": "服务器拒绝访问（HTTP 403），可能需要重新导出 cookies", "error": error[-500:]}
    return {"ok": False, "message": "下载测试失败", "error": error[-500:]}


def check_cookies(config, url=None):
    path = get_cookies_path(config)
    result = {"exists": bool(path), "path": path or ""}
    if not path:
        result["summary"] = "未找到 cookies 文件"
        result["usable"] = False
        return result

    cookies = parse_netscape_cookies(path)
    by_name = {item["name"]: item for item in cookies}
    now = int(time.time())

    key_status = {}
    for key in COOKIE_KEYS:
        cookie = by_name.get(key)
        if not cookie:
            key_status[key] = "missing"
        elif cookie["expires"] and cookie["expires"] < now:
            key_status[key] = "expired"
        else:
            key_status[key] = "ok"

    expired = [name for name, item in by_name.items() if item["expires"] and item["expires"] < now]
    live = live_check_bilibili(by_name)
    test_url = url or config.get("cookies_test_url") or DEFAULT_COOKIE_TEST_URL
    download_check = check_download_access(test_url, config, path)

    result.update(
        {
            "count": len(cookies),
            "key_cookies": key_status,
            "expired_count": len(expired),
            "expired_names": expired[:20],
            "live": live,
            "download_check": download_check,
        }
    )

    if download_check.get("ok"):
        result["summary"] = "cookies 可用于下载"
        if live.get("ok") and not live.get("logged_in"):
            result["summary"] += "（未检测到登录，但公开视频可正常下载）"
        result["usable"] = True
    elif key_status.get("SESSDATA") == "expired":
        result["summary"] = "SESSDATA 已过期，且下载测试未通过，建议重新导出 cookies"
        result["usable"] = False
    elif live.get("ok") and live.get("logged_in"):
        result["summary"] = "已登录，但下载测试未通过，请检查网络或视频是否可访问"
        result["usable"] = False
    else:
        result["summary"] = "cookies 文件存在，但下载测试未通过"
        result["usable"] = False

    return result


def is_playlist_url(url):
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in PLAYLIST_URL_PATTERNS)


def get_cookie_header(config):
    path = get_cookies_path(config)
    if not path:
        return ""
    cookies = parse_netscape_cookies(path)
    return "; ".join(f"{item['name']}={item['value']}" for item in cookies)


def expand_bilibili_cheese_url(url, config):
    match = CHEESE_EP_PATTERN.search(url)
    if not match:
        return url

    ep_id = match.group(1)
    cookie_header = get_cookie_header(config)
    try:
        response = requests.get(
            "https://api.bilibili.com/pugv/view/web/season",
            params={"ep_id": ep_id},
            headers={"Cookie": cookie_header, "User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        data = response.json()
        season_id = (data.get("data") or {}).get("season_id")
        if data.get("code") == 0 and season_id:
            return f"https://www.bilibili.com/cheese/play/ss{season_id}"
    except Exception:
        pass
    return url


def get_ffmpeg_path(config):
    configured = config.get("ffmpeg_location")
    if configured:
        full = resolve_path(configured)
        if os.path.isfile(full):
            return full
        # 用户填的也可能是包含 ffmpeg.exe 的目录
        exe_in_dir = os.path.join(full, "ffmpeg.exe")
        if os.path.isfile(exe_in_dir):
            return exe_in_dir

    # 自动检测 PATH 中的 ffmpeg
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 常见的项目相对位置
    candidates = [
        os.path.join(BASE_DIR, "..", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe"),
        os.path.join(BASE_DIR, "ffmpeg.exe"),
        os.path.join(BASE_DIR, "bin", "ffmpeg.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return ""


def load_download_log():
    if not os.path.exists(DOWNLOAD_LOG):
        return set()
    with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_download_log(urls):
    with open(DOWNLOAD_LOG, "w", encoding="utf-8") as f:
        for url in sorted(urls):
            f.write(url + "\n")


def classify_file(name):
    ext = os.path.splitext(name)[1].lower()
    if ext in {".mp4", ".mkv", ".webm", ".flv", ".avi", ".mov"}:
        return "video"
    if ext in {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"}:
        return "audio"
    if ext in {".txt", ".srt", ".json", ".csv", ".md", ".log"}:
        return "text"
    return "other"


def update_task(task_id, status=None, progress=None, message=None):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return
        if status is not None:
            task["status"] = status
        if progress is not None:
            task["progress"] = progress
        if message is not None:
            task["message"] = message
        task["updated_at"] = now_iso()


def append_task_log(task_id, line):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return
        task["log"].append(line)
        if len(task["log"]) > 500:
            del task["log"][: len(task["log"]) - 500]


def update_task_title(task_id, playlist_title="", video_title=""):
    playlist_title = (playlist_title or "").strip()
    video_title = (video_title or "").strip()
    display_title = playlist_title or video_title
    if not display_title:
        return
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return
        if playlist_title:
            task["playlist_title"] = playlist_title
        if video_title:
            task["video_title"] = video_title
        task["display_title"] = display_title
        task["title_source"] = "playlist" if playlist_title else "video"
        task["updated_at"] = now_iso()


def parse_title_meta_line(line):
    if not line.startswith(TITLE_META_PREFIX):
        return None
    payload = line[len(TITLE_META_PREFIX) :]
    parts = payload.split("\t", 1)
    if len(parts) == 1:
        parts.append("")
    return {"playlist_title": parts[0].strip(), "video_title": parts[1].strip()}


def get_task_log_lines(task_id):
    with tasks_lock:
        return list(tasks.get(task_id, {}).get("log", []))


def parse_failed_playlist_items(log_lines):
    failed = set()
    current_item = None
    total_items = None
    hard_error_markers = (
        "ERROR:",
        "This video is unavailable",
        "Private video",
        "Video unavailable",
        "You need to purchase",
        "Unable to download",
        "giving up after",
    )
    for line in log_lines:
        item_match = PLAYLIST_ITEM_RE.search(line)
        if item_match:
            current_item = int(item_match.group(1))
            total_items = int(item_match.group(2))
            continue
        if current_item and any(marker in line for marker in hard_error_markers):
            failed.add(current_item)
    return {"failed": sorted(failed), "total": total_items}


def describe_failed_items(task_id):
    parsed = parse_failed_playlist_items(get_task_log_lines(task_id))
    failed = parsed.get("failed") or []
    if not failed:
        return "未能从日志中精确识别失败分集；已保留完整日志供排查"
    total = parsed.get("total")
    suffix = f" / {total}" if total else ""
    return f"疑似失败分集：{', '.join(f'p{item}' for item in failed)}{suffix}"


def _repair_partial_playlist(url, config, task_id, quality="best", download_playlist=False, concurrent_fragments=8, force=False):
    if not force and not bool(config.get("auto_repair_partial", True)):
        append_task_log(task_id, "[auto-repair] 已关闭自动修复部分完成任务。")
        return False

    attempts = get_partial_repair_attempts(config)
    if attempts <= 0:
        append_task_log(task_id, "[auto-repair] 修复重试次数为 0，跳过自动修复。")
        return False

    archive_path = get_download_archive_path(config)
    append_task_log(task_id, f"[auto-repair] 检测到合集部分完成，将使用归档跳过已完成分集：{archive_path}")
    append_task_log(task_id, f"[auto-repair] {describe_failed_items(task_id)}")

    for attempt in range(1, attempts + 1):
        update_task(task_id, "running", progress=0, message=f"自动修复部分完成：第 {attempt}/{attempts} 次重试")
        append_task_log(task_id, f"[auto-repair] ===== 第 {attempt}/{attempts} 次修复开始 =====")
        result = _download_one(url, config, task_id, quality, download_playlist, concurrent_fragments, repair_attempt=attempt)
        if result == "done":
            append_task_log(task_id, "[auto-repair] 修复成功：缺失分集已补齐。")
            return True
        append_task_log(task_id, f"[auto-repair] 第 {attempt}/{attempts} 次修复仍未完成，结果：{result}。")
        if attempt < attempts:
            time.sleep(3)

    append_task_log(task_id, f"[auto-repair] 自动修复失败：{describe_failed_items(task_id)}")
    return False


def task_looks_like_playlist(task):
    if task.get("download_playlist") is not None:
        return bool(task.get("download_playlist"))
    if is_playlist_url(task.get("url", "")):
        return True
    return any(PLAYLIST_ITEM_RE.search(line) for line in task.get("log", []))


def _repair_task(task_id):
    config = load_config()
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return
        if task.get("repairing"):
            return
        task["repairing"] = True
        task["status"] = "repairing"
        task["progress"] = 0.0
        task["message"] = "正在检测问题并修复…"
        task["updated_at"] = now_iso()

        url = task.get("url", "")
        quality = task.get("quality") or "best"
        download_playlist = task_looks_like_playlist(task)
        concurrent_fragments = clamp_int(task.get("concurrent_fragments"), 8, 1, 32)

    append_task_log(task_id, "[manual-repair] 用户手动触发：开始检测问题并修复。")
    append_task_log(task_id, f"[manual-repair] {describe_failed_items(task_id)}")
    try:
        repaired = _repair_partial_playlist(
            url,
            config,
            task_id,
            quality,
            download_playlist,
            concurrent_fragments,
            force=True,
        )
        if repaired:
            downloaded = load_download_log()
            if url:
                downloaded.add(url)
                save_download_log(downloaded)
            update_task(task_id, "done", progress=100.0, message="检测并修复完成，状态已重置为完成")
        else:
            update_task(task_id, "partial", progress=99.0, message=f"检测并修复失败：{describe_failed_items(task_id)}")
    except Exception as exc:
        append_task_log(task_id, f"[manual-repair] 修复异常：{exc}")
        update_task(task_id, "partial", progress=99.0, message=f"检测并修复异常：{exc}")
    finally:
        with tasks_lock:
            task = tasks.get(task_id)
            if task:
                task["repairing"] = False
                task["updated_at"] = now_iso()


def _download_one(url, config, task_id, quality="best", download_playlist=False, concurrent_fragments=8, repair_attempt=0):
    yt_dlp = get_yt_dlp_path(config)
    out_dir = get_output_dir(config)
    os.makedirs(out_dir, exist_ok=True)
    format_spec = QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"])

    cmd = [
        yt_dlp,
        "--newline",
        "--windows-filenames",
        "--encoding",
        "utf-8",
    ]
    playlist = download_playlist or is_playlist_url(url)
    if playlist:
        archive_path = get_download_archive_path(config)
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        cmd.extend(["--yes-playlist", "--download-archive", archive_path])
        output_template = os.path.join(out_dir, "%(playlist_title)s", "%(title)s.%(ext)s")
    else:
        output_template = os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s")
    cmd.extend(
        [
            "--retries",
            "15",
            "--fragment-retries",
            "15",
            "--retry-sleep",
            "5",
            "--socket-timeout",
            "30",
            "--print",
            f"before_dl:{TITLE_META_PREFIX}%(playlist_title|)s\t%(title)s",
            "-f",
            format_spec,
            "--merge-output-format",
            "mp4",
            "--concurrent-fragments",
            str(concurrent_fragments),
            "-o",
            output_template,
            url,
        ]
    )

    cookies = get_cookies_path(config)
    if cookies:
        cmd.extend(["--cookies", cookies])

    ffmpeg_path = get_ffmpeg_path(config)
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    prefix = f"自动修复第 {repair_attempt} 次：" if repair_attempt else ""
    update_task(task_id, message=f"{prefix}{' '.join(cmd)}")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        update_task(task_id, message="找不到 yt-dlp，请检查配置或 yt-dlp.exe")
        return False

    for raw in proc.stdout:
        line = raw.rstrip()
        title_meta = parse_title_meta_line(line)
        if title_meta:
            update_task_title(task_id, title_meta["playlist_title"], title_meta["video_title"])
            continue
        append_task_log(task_id, line)
        match = PROGRESS_RE.search(line)
        if match:
            update_task(task_id, progress=float(match.group(1)), message=line)
        else:
            update_task(task_id, message=line)

    proc.wait()
    if proc.returncode == 0:
        return "done"

    with tasks_lock:
        log_text = "\n".join(tasks.get(task_id, {}).get("log", []))
    if "Finished downloading playlist" in log_text or "You need to purchase" in log_text:
        return "partial"
    return "error"


def _run_batch(batch_id, urls, config, quality="best", download_playlist=False, concurrent_fragments=8):
    auto_organize = bool(config.get("auto_organize", True))
    downloaded = load_download_log()

    with tasks_lock:
        batch_task_ids = [t["id"] for t in tasks.values() if t.get("batch_id") == batch_id]

    success_count = 0
    for task_id in batch_task_ids:
        url = tasks[task_id]["url"]
        if url in downloaded:
            update_task(task_id, "skipped", message="已在下载日志中，跳过")
            continue

        update_task(task_id, "running", message="开始下载")
        result = _download_one(url, config, task_id, quality, download_playlist, concurrent_fragments)
        if result == "done":
            downloaded.add(url)
            save_download_log(downloaded)
            success_count += 1
            update_task(task_id, "done", progress=100.0, message="下载完成")
        elif result == "partial":
            repaired = _repair_partial_playlist(url, config, task_id, quality, download_playlist, concurrent_fragments)
            if repaired:
                downloaded.add(url)
                save_download_log(downloaded)
                success_count += 1
                update_task(task_id, "done", progress=100.0, message="部分完成已自动修复，下载完成")
            else:
                update_task(task_id, "partial", progress=99.0, message=f"部分完成，自动修复失败：{describe_failed_items(task_id)}")
        else:
            update_task(task_id, "error", message="下载失败，详见日志")

    if auto_organize and success_count > 0:
        try:
            mp4_file_organizer.organize_mp4_files(get_output_dir(config))
        except Exception as exc:
            print(f"自动整理失败: {exc}")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    config = load_config()
    yt_dlp = get_yt_dlp_path(config)
    cookies = get_cookies_path(config)
    ffmpeg_path = get_ffmpeg_path(config)
    yt_dlp_executable = resolve_executable(yt_dlp)
    return jsonify(
        {
            "yt_dlp": yt_dlp,
            "yt_dlp_ok": bool(yt_dlp_executable),
            "cookies": cookies,
            "cookies_ok": bool(cookies),
            "output_dir": get_output_dir(config),
            "ffmpeg": ffmpeg_path,
            "ffmpeg_ok": bool(ffmpeg_path and os.path.isfile(ffmpeg_path)),
        }
    )


@app.get("/api/tools/status")
def api_tools_status():
    include_remote = request.args.get("remote") in {"1", "true", "yes"}
    return jsonify(tools_status(load_config(), include_remote=include_remote))


@app.post("/api/tools/yt-dlp/update")
def api_update_yt_dlp():
    config = load_config()
    before = get_yt_dlp_status(config, include_remote=True)
    executable = before.get("path")
    if not executable:
        return jsonify({"ok": False, "message": "找不到 yt-dlp，请先在配置中填写 yt-dlp.exe 路径"}), 400

    proc = run_command_output([executable, "-U"], timeout=180)
    after = get_yt_dlp_status(config, include_remote=True)
    ok = bool(proc.get("ok"))
    return jsonify(
        {
            "ok": ok,
            "message": "yt-dlp 更新完成" if ok else "yt-dlp 更新失败",
            "before": before,
            "after": after,
            "stdout": proc.get("stdout"),
            "stderr": proc.get("stderr"),
            "returncode": proc.get("returncode"),
        }
    ), (200 if ok else 500)


@app.post("/api/tools/ffmpeg/update")
def api_update_ffmpeg():
    if os.name != "nt":
        return jsonify({"ok": False, "message": "当前自动更新 FFmpeg 仅支持 Windows 构建"}), 400

    config = load_config()
    before = get_ffmpeg_status(config, include_remote=True)
    try:
        latest = before.get("latest") or latest_ffmpeg_release()
    except Exception as exc:
        return jsonify({"ok": False, "message": f"获取 FFmpeg 最新版本失败：{exc}", "before": before}), 500
    download_url = latest.get("download_url")
    if not download_url:
        return jsonify({"ok": False, "message": "未找到 FFmpeg 下载地址"}), 500

    install_root = before.get("managed_root") or get_ffmpeg_install_root(before.get("path"))
    os.makedirs(os.path.dirname(install_root), exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="ffmpeg-update-")
    try:
        zip_path = os.path.join(temp_dir, latest.get("name") or FFMPEG_ASSET_NAME)
        extract_dir = os.path.join(temp_dir, "extract")
        os.makedirs(extract_dir, exist_ok=True)
        download_file(download_url, zip_path)
        safe_extract_zip(zip_path, extract_dir)
        extracted_root = find_extracted_ffmpeg_root(extract_dir)
        shutil.copytree(extracted_root, install_root, dirs_exist_ok=True)

        ffmpeg_exe = os.path.join(install_root, "bin", "ffmpeg.exe")
        config["ffmpeg_location"] = os.path.relpath(ffmpeg_exe, BASE_DIR).replace(os.sep, "/")
        config["ffmpeg_release_name"] = latest.get("name") or FFMPEG_ASSET_NAME
        config["ffmpeg_release_updated_at"] = latest.get("updated_at") or ""
        save_config(config)

        after = get_ffmpeg_status(config, include_remote=True)
        return jsonify(
            {
                "ok": True,
                "message": "FFmpeg 更新完成",
                "before": before,
                "after": after,
                "install_root": install_root,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "message": f"FFmpeg 更新失败：{exc}", "before": before}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/config")
def api_get_config():
    return jsonify({"config": load_config()})


@app.post("/api/cookies/check")
def api_cookies_check():
    config = load_config()
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    return jsonify(check_cookies(config, url=url))


@app.post("/api/config")
def api_save_config():
    data = request.get_json(silent=True) or {}
    allowed = {
        "cookies_path",
        "output_dir",
        "ffmpeg_location",
        "yt_dlp_path",
        "auto_organize",
        "auto_repair_partial",
        "partial_repair_attempts",
    }
    patch = {key: data[key] for key in allowed if key in data}
    if "partial_repair_attempts" in patch:
        patch["partial_repair_attempts"] = get_partial_repair_attempts(patch)
    config = load_config()
    config.update(patch)
    save_config(config)
    return jsonify({"ok": True, "config": config})


@app.post("/api/download")
def api_download():
    data = request.get_json(silent=True) or {}
    raw_urls = data.get("urls") or []
    urls = []
    if isinstance(raw_urls, str):
        urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
    else:
        urls = [str(item).strip() for item in raw_urls if str(item).strip()]

    if not urls:
        return jsonify({"ok": False, "message": "请至少填写一个视频 URL"}), 400

    quality = data.get("quality") or "best"
    download_playlist = bool(data.get("download_playlist"))
    try:
        concurrent_fragments = max(1, min(32, int(data.get("concurrent_fragments") or 8)))
    except (TypeError, ValueError):
        concurrent_fragments = 8
    config = load_config()
    urls = [expand_bilibili_cheese_url(url, config) for url in urls]
    batch_id = uuid.uuid4().hex
    created_tasks = []
    with tasks_lock:
        for url in urls:
            task_id = uuid.uuid4().hex
            task = {
                "id": task_id,
                "batch_id": batch_id,
                "url": url,
                "status": "pending",
                "progress": 0.0,
                "message": "等待下载",
                "log": [],
                "display_title": "",
                "playlist_title": "",
                "video_title": "",
                "title_source": "",
                "quality": quality,
                "download_playlist": download_playlist,
                "concurrent_fragments": concurrent_fragments,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            tasks[task_id] = task
            created_tasks.append(task)

    threading.Thread(
        target=_run_batch,
        args=(batch_id, urls, config, quality, download_playlist, concurrent_fragments),
        daemon=True,
    ).start()
    return jsonify({"ok": True, "tasks": created_tasks})


@app.get("/api/tasks")
def api_tasks():
    with tasks_lock:
        data = list(tasks.values())
    data.sort(key=lambda item: item["created_at"])
    return jsonify({"tasks": data})


@app.post("/api/tasks/<task_id>/repair")
def api_task_repair(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task:
            return jsonify({"ok": False, "message": "任务不存在或服务已重启，无法修复内存中的任务"}), 404
        if task.get("repairing") or task.get("status") in {"running", "repairing"}:
            return jsonify({"ok": False, "message": "任务正在运行或修复中"}), 409
        if task.get("status") not in {"partial", "error", "skipped"}:
            return jsonify({"ok": False, "message": "当前任务状态不需要修复"}), 400

    threading.Thread(target=_repair_task, args=(task_id,), daemon=True).start()
    return jsonify({"ok": True, "message": "已开始检测并修复，请稍后查看任务状态"})


@app.post("/api/tasks/clear")
def api_tasks_clear():
    with tasks_lock:
        to_remove = [
            task_id
            for task_id, task in tasks.items()
            if task["status"] in {"done", "error", "skipped", "partial"}
        ]
        for task_id in to_remove:
            del tasks[task_id]
    return jsonify({"ok": True, "removed": len(to_remove)})


@app.get("/api/files")
def api_files():
    config = load_config()
    out_dir = get_output_dir(config)
    files = []
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if not os.path.isfile(path):
                continue
            stat = os.stat(path)
            files.append(
                {
                    "name": name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    "kind": classify_file(name),
                }
            )
    files.sort(key=lambda item: item["modified"], reverse=True)
    return jsonify({"dir": out_dir, "files": files})


@app.post("/api/organize")
def api_organize():
    config = load_config()
    out_dir = get_output_dir(config)
    try:
        mp4_file_organizer.organize_mp4_files(out_dir)
        return jsonify({"ok": True, "message": "整理完成", "dir": out_dir})
    except Exception as exc:
        return jsonify({"ok": False, "message": f"整理失败: {exc}"}), 500


@app.post("/api/merge")
def api_merge():
    data = request.get_json(silent=True) or {}
    config = load_config()
    out_dir = get_output_dir(config)
    delete_sources = bool(data.get("delete_sources"))
    result = merge_media.merge_pairs(out_dir, delete_sources=delete_sources)
    if not result.get("ok"):
        return jsonify(result), 500
    return jsonify(result)


@app.get("/api/log")
def api_log():
    entries = []
    if os.path.exists(DOWNLOAD_LOG):
        with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
            entries = [line.strip() for line in f if line.strip()]
    return jsonify({"entries": entries, "count": len(entries)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
