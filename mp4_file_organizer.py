import os
import re
import shutil

BV_PATTERN = re.compile(r"^(.*?)\s*\[BV[0-9A-Za-z]+(?:_p\d+)?\]$")


def parse_name(filename):
    stem = os.path.splitext(filename)[0]
    match = BV_PATTERN.match(stem)
    if not match:
        return stem.strip(), None

    title_part = match.group(1).strip()
    # 多 P 合集通常形如：合集名 p01 01_标题
    parts = re.split(r"\s+(p\d+)\s+", title_part, maxsplit=1)
    if len(parts) >= 3:
        collection = parts[0].strip()
        part_name = f"{parts[1]} {parts[2].strip()}"
        return collection, part_name

    return title_part, None


def organize_mp4_files(target_dir=None):
    current_dir = target_dir or os.getcwd()
    groups = {}

    # 遍历当前目录下的所有 mp4 文件
    for filename in os.listdir(current_dir):
        if not filename.lower().endswith(".mp4"):
            continue
        collection, part_name = parse_name(filename)
        folder = collection or "未分类"
        groups.setdefault(folder, []).append((filename, part_name))

    # 为每个前缀创建文件夹并移动文件
    for folder, files in groups.items():
        folder_path = os.path.join(current_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        for filename, part_name in files:
            source_path = os.path.join(current_dir, filename)
            ext = os.path.splitext(filename)[1]
            dest_name = part_name + ext if part_name else filename
            destination_path = os.path.join(folder_path, dest_name)
            try:
                shutil.move(source_path, destination_path)
            except Exception as e:
                print(f"移动文件 {filename} 时出现错误: {e}")


if __name__ == "__main__":
    organize_mp4_files()
