import os
import re
import shutil
import sys

import requests

from app import get_cookies_path, load_config, parse_netscape_cookies


EP_FOLDER_RE = re.compile(r"^\d+ - .+? \[(\d+)\]$")


def get_cookie_header(config):
    path = get_cookies_path(config)
    if not path:
        return ""
    cookies = parse_netscape_cookies(path)
    return "; ".join(f"{item['name']}={item['value']}" for item in cookies)


def get_course_title(ep_id, config):
    cookie_header = get_cookie_header(config)
    try:
        response = requests.get(
            "https://api.bilibili.com/pugv/view/web/season",
            params={"ep_id": ep_id},
            headers={"Cookie": cookie_header, "User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        data = response.json().get("data") or {}
        return data.get("title") or f"课程_{ep_id}"
    except Exception:
        return f"课程_{ep_id}"


def flatten_course(target_dir, dry_run=False):
    target = os.path.abspath(target_dir)
    episode_dirs = []
    for name in os.listdir(target):
        path = os.path.join(target, name)
        if not os.path.isdir(path):
            continue
        match = EP_FOLDER_RE.match(name)
        if match:
            episode_dirs.append((name, match.group(1), path))

    if not episode_dirs:
        print("未找到课程分集文件夹")
        return 0

    config = load_config()
    course_title = get_course_title(episode_dirs[0][1], config)
    course_dir = os.path.join(target, course_title)
    moved = 0

    for folder_name, _ep_id, folder_path in episode_dirs:
        for filename in os.listdir(folder_path):
            if not filename.lower().endswith(".mp4"):
                continue
            source = os.path.join(folder_path, filename)
            base_name = re.sub(r"\s*\[\d+\]$", "", folder_name)
            ext = os.path.splitext(filename)[1]
            destination = os.path.join(course_dir, base_name + ext)

            print(f"移动: {source} -> {destination}")
            if not dry_run:
                os.makedirs(course_dir, exist_ok=True)
                if os.path.exists(destination):
                    print(f"跳过，目标已存在: {os.path.basename(destination)}")
                    continue
                shutil.move(source, destination)
            moved += 1

    if not dry_run:
        for _name, _ep_id, folder_path in episode_dirs:
            try:
                os.rmdir(folder_path)
            except OSError:
                pass

    return moved


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    dry_run = "--dry-run" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--dry-run"]
    target = args[0] if args else os.getcwd()
    print(f"整理目录: {target}")
    moved = flatten_course(target, dry_run=dry_run)
    print(f"完成，移动文件数: {moved}")


if __name__ == "__main__":
    main()
