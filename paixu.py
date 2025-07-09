import os
import re


def reverse_numbering():
    current_dir = os.getcwd()
    mp4_files = [f for f in os.listdir(current_dir) if f.endswith('.mp4')]
    mp4_files.sort()
    num_files = len(mp4_files)
    for i, file in enumerate(mp4_files):
        new_index = str(num_files - i).zfill(2)
        new_file = re.sub(r'^\d{2}-', f'{new_index}-', file)
        old_path = os.path.join(current_dir, file)
        new_path = os.path.join(current_dir, new_file)
        try:
            os.rename(old_path, new_path)
            print(f"已将 {file} 重命名为 {new_file}")
        except Exception as e:
            print(f"重命名 {file} 时出错: {e}")


if __name__ == "__main__":
    reverse_numbering()