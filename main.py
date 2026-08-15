import subprocess
import sys
import time

MAX_RETRIES = 3  # 最大重试次数

def run_script_with_retries(script_name):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            print(f"开始运行 {script_name}...")
            subprocess.run([sys.executable, script_name], check=True)
            print(f"{script_name} 运行成功。")
            return True
        except subprocess.CalledProcessError as e:
            retries += 1
            print(f"{script_name} 运行失败，第 {retries} 次重试... 错误信息: {e}")
            time.sleep(1)  # 等待 1 秒后重试
    print(f"{script_name} 达到最大重试次数，运行失败。")
    return False

if __name__ == "__main__":
    # 运行 yt-dlp_pachong.py
    if run_script_with_retries("yt-dlp_pachong.py"):
        # 若下载脚本运行成功，再运行整理脚本
        if not run_script_with_retries("mp4_file_organizer.py"):
            print("mp4_file_organizer.py 运行失败。")
    else:
        print("yt-dlp_pachong.py 运行失败，程序退出。")
