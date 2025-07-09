import subprocess
import os
import shutil
import time

MAX_RETRIES = 3  # 最大重试次数

def run_script_with_retries(script_name):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            print(f"开始运行 {script_name}...")
            subprocess.run(['python', script_name], check=True)
            print(f"{script_name} 运行成功。")
            return True
        except subprocess.CalledProcessError as e:
            retries += 1
            print(f"{script_name} 运行失败，第 {retries} 次重试... 错误信息: {e}")
            if os.path.exists(script_name):
                # 若脚本产生了文件，删除相关文件（这里只是简单示例，可按需调整）
                if os.path.isfile(script_name):
                    os.remove(script_name)
                elif os.path.isdir(script_name):
                    shutil.rmtree(script_name)
            time.sleep(1)  # 等待 1 秒后重试
    print(f"{script_name} 达到最大重试次数，运行失败。")
    return False

if __name__ == "__main__":
    # 运行 yt-dlp_pachong.py
    if run_script_with_retries('yt-dlp_pachong.py'):
        # 若 yt-dlp_pachong.py 运行成功，运行 mp4_file_organizer.py
        run_script_with_retries('mp4_file_organizer.py')
    else:
        run_script_with_retries('main.py')