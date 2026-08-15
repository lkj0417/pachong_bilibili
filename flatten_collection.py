import os
import shutil
import sys

from mp4_file_organizer import parse_name


def flatten_collection(target_dir, dry_run=False):
    target = os.path.abspath(target_dir)
    files = []
    for root, _dirs, names in os.walk(target):
        for name in names:
            if name.lower().endswith(".mp4"):
                files.append(os.path.join(root, name))

    moved = 0
    for source in files:
        filename = os.path.basename(source)
        collection, part_name = parse_name(filename)
        folder = collection or "未分类"
        folder_path = os.path.join(target, folder)

        ext = os.path.splitext(filename)[1]
        dest_name = part_name + ext if part_name else filename
        destination = os.path.join(folder_path, dest_name)

        if os.path.abspath(source) == os.path.abspath(destination):
            continue
        if not dry_run and os.path.exists(destination):
            print(f"跳过，目标已存在: {dest_name}")
            continue

        print(f"移动: {source} -> {destination}")
        if not dry_run:
            os.makedirs(folder_path, exist_ok=True)
            shutil.move(source, destination)
        moved += 1

    if not dry_run:
        for root, _dirs, _names in os.walk(target, topdown=False):
            if os.path.abspath(root) == target:
                continue
            try:
                os.rmdir(root)
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
    moved = flatten_collection(target, dry_run=dry_run)
    print(f"完成，移动文件数: {moved}")


if __name__ == "__main__":
    main()
