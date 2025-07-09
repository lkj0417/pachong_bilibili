import os
import shutil
import re


def get_prefix(filename):
    # 尝试使用正则表达式提取从 - 到 p 之间的前缀
    match = re.search(r'-\s*(.*?)\s+p', filename)
    if match:
        return match.group(1)
    # 若没有匹配到 - p 结构，尝试从序号后的 - 开始提取完整部分作为前缀
    parts = filename.split('-', 1)
    if len(parts) > 1:
        return parts[1].replace('.mp4', '').strip()
    return None


def organize_mp4_files():
    current_dir = os.getcwd()
    prefix_dict = {}

    # 遍历当前目录下的所有文件
    for filename in os.listdir(current_dir):
        if filename.endswith('.mp4'):
            prefix = get_prefix(filename)
            if prefix:
                if prefix not in prefix_dict:
                    prefix_dict[prefix] = []
                prefix_dict[prefix].append(filename)

    # 为每个前缀创建文件夹并移动文件
    for prefix, files in prefix_dict.items():
        folder_name = os.path.join(current_dir, prefix)
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        for file in files:
            source_path = os.path.join(current_dir, file)
            destination_path = os.path.join(folder_name, file)
            try:
                shutil.move(source_path, destination_path)
            except Exception as e:
                print(f"移动文件 {file} 时出现错误: {e}")


if __name__ == "__main__":
    organize_mp4_files()
