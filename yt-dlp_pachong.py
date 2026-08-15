import os
import re
import shutil
import subprocess
import sys

LOG_FILE = "downloaded_files.txt"
URLS_FILE = "urls.txt"
CONCURRENT_FRAGMENTS = 8
PLAYLIST_URL_PATTERNS = [
    r"bilibili\.com/(cheese|bangumi)/play/ss",
    r"bilibili\.com/list/",
    r"space\.bilibili\.com/.*/channel/collectiondetail",
    r"space\.bilibili\.com/.*/lists/",
]


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def get_yt_dlp_path():
    local = os.path.join(get_script_dir(), "yt-dlp.exe")
    return local if os.path.exists(local) else "yt-dlp"


def get_ffmpeg_path():
    found = shutil.which("ffmpeg")
    if found:
        return found

    base = get_script_dir()
    candidates = [
        os.path.join(base, "..", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe"),
        os.path.join(base, "ffmpeg.exe"),
        os.path.join(base, "bin", "ffmpeg.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return ""


def is_playlist_url(url):
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in PLAYLIST_URL_PATTERNS)


def load_download_log():
    path = os.path.join(get_script_dir(), LOG_FILE)
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_download_log(urls):
    path = os.path.join(get_script_dir(), LOG_FILE)
    with open(path, "w", encoding="utf-8") as f:
        for url in sorted(urls):
            f.write(url + "\n")


def load_urls():
    urls = []
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        path = os.path.join(get_script_dir(), URLS_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return urls


def download_video(url, output_dir=None):
    """
    使用 yt-dlp 下载视频
    """
    script_dir = get_script_dir()
    output_dir = output_dir or script_dir
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        get_yt_dlp_path(),
        "--windows-filenames",
        "--encoding",
        "utf-8",
    ]
    if is_playlist_url(url):
        cmd.append("--yes-playlist")
    cmd.extend(
        [
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "--concurrent-fragments",
            str(CONCURRENT_FRAGMENTS),
            "-o",
            os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s"),
            url,
        ]
    )

    # 添加 cookies 支持（如果有 cookies.txt）
    cookies_path = os.path.join(script_dir, "cookies.txt")
    if os.path.exists(cookies_path):
        cmd.extend(["--cookies", cookies_path])

    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    print(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print("下载成功！")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"下载失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误: 找不到 yt-dlp。请确保 yt-dlp.exe 在当前目录或已添加到 PATH。")
        return False


def main():
    urls = load_urls()
    if not urls:
        print("用法一: python yt-dlp_pachong.py <视频URL> [更多URL...]")
        print("用法二: 在 urls.txt 中每行填写一个视频URL，然后运行 python yt-dlp_pachong.py")
        return 1

    downloaded = load_download_log()
    success_count = 0
    skip_count = 0

    for url in urls:
        if url in downloaded:
            skip_count += 1
            print(f"跳过已下载: {url}")
            continue

        print(f"\n开始下载: {url}")
        if download_video(url):
            downloaded.add(url)
            save_download_log(downloaded)
            success_count += 1

    fail_count = len(urls) - success_count - skip_count
    print(f"\n处理完成：成功 {success_count} 个，跳过 {skip_count} 个，失败 {fail_count} 个。")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
