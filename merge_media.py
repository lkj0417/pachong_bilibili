import argparse
import os
import re
import shutil
import subprocess
import sys


VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".flv", ".avi", ".mov"}
AUDIO_EXTS = {".m4a", ".mp3", ".aac", ".wav", ".flac", ".ogg"}
BV_PATTERN = re.compile(r"^(.*?)\s*\[BV[0-9A-Za-z]+\]")


def get_prefix(filename):
    stem = os.path.splitext(filename)[0]
    match = BV_PATTERN.match(stem)
    if match and match.group(1).strip():
        return match.group(1).strip()
    return stem.strip()


def get_ffmpeg_path():
    found = shutil.which("ffmpeg")
    if found:
        return found

    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "..", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe"),
        os.path.join(base, "ffmpeg.exe"),
        os.path.join(base, "bin", "ffmpeg.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return ""


def merge_pairs(target_dir, delete_sources=False):
    target_dir = os.path.abspath(target_dir)
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        return {"ok": False, "message": "找不到 ffmpeg，无法合并音视频"}
    if not os.path.isdir(target_dir):
        return {"ok": False, "message": f"目录不存在: {target_dir}"}

    groups = {}
    for name in os.listdir(target_dir):
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in VIDEO_EXTS and ext not in AUDIO_EXTS:
            continue

        prefix = get_prefix(name)
        group = groups.setdefault(prefix, {"video": None, "audio": None})
        if ext in VIDEO_EXTS and group["video"] is None:
            group["video"] = name
        elif ext in AUDIO_EXTS and group["audio"] is None:
            group["audio"] = name

    results = []
    merged_count = 0

    for prefix, files in groups.items():
        if not files["video"] or not files["audio"]:
            continue

        out_name = prefix + ".merged.mp4"
        out_path = os.path.join(target_dir, out_name)
        if os.path.exists(out_path):
            results.append({"name": out_name, "status": "skipped", "message": "已存在"})
            continue

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            os.path.join(target_dir, files["video"]),
            "-i",
            os.path.join(target_dir, files["audio"]),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c",
            "copy",
            out_path,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            results.append({"name": out_name, "status": "error", "message": proc.stderr[-200:]})
            continue

        merged_count += 1
        if delete_sources:
            os.remove(os.path.join(target_dir, files["video"]))
            os.remove(os.path.join(target_dir, files["audio"]))
            results.append({"name": out_name, "status": "done", "message": "已合并并删除源文件"})
        else:
            results.append({"name": out_name, "status": "done", "message": "已合并"})

    return {"ok": True, "merged": merged_count, "results": results}


def main():
    parser = argparse.ArgumentParser(description="合并同一视频的音视频文件")
    parser.add_argument("target_dir", nargs="?", default=os.getcwd(), help="要扫描的目录，默认当前目录")
    parser.add_argument("--delete-sources", action="store_true", help="合并成功后删除原始视频和音频文件")
    parser.add_argument("--dry-run", action="store_true", help="只显示计划，不执行")
    args = parser.parse_args()

    if args.dry_run:
        # 简单列出可合并的配对，不真正合并
        ffmpeg = get_ffmpeg_path()
        print("ffmpeg:", ffmpeg or "未找到")
        target_dir = os.path.abspath(args.target_dir)
        groups = {}
        for name in os.listdir(target_dir):
            full = os.path.join(target_dir, name)
            if not os.path.isfile(full):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in VIDEO_EXTS and ext not in AUDIO_EXTS:
                continue
            prefix = get_prefix(name)
            group = groups.setdefault(prefix, {"video": None, "audio": None})
            if ext in VIDEO_EXTS and group["video"] is None:
                group["video"] = name
            elif ext in AUDIO_EXTS and group["audio"] is None:
                group["audio"] = name
        for prefix, files in groups.items():
            if files["video"] and files["audio"]:
                print(f"{files['video']} + {files['audio']} -> {prefix}.merged.mp4")
        return 0

    result = merge_pairs(args.target_dir, delete_sources=args.delete_sources)
    if not result.get("ok"):
        print(result.get("message"))
        return 1

    for item in result.get("results", []):
        print(f"[{item['status']}] {item['name']}: {item.get('message', '')}")
    print(f"完成，合并 {result.get('merged', 0)} 个。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
