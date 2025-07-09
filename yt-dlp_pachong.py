import yt_dlp
import os


def download_bilibili_video(url, cookies_path):
    log_file_path = 'downloaded_files.txt'
    existing_data = set()

    # 读取已有的数据
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                existing_data.add(line.strip())

    def log_download_info(d):
        nonlocal existing_data
        if d['status'] == 'finished':
            new_entry = f"{d['filename']} - {d['info_dict']['webpage_url']}"
            # 若新条目不在已有数据中，添加到集合并写入文件
            if new_entry not in existing_data:
                existing_data.add(new_entry)
                with open(log_file_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(new_entry + '\n')
            # 若已有数据中有重复条目，先清空文件，再重新写入所有数据
            else:
                with open(log_file_path, 'w', encoding='utf-8') as log_file:
                    for entry in existing_data:
                        log_file.write(entry + '\n')

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': '%(playlist_index)02d- %(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'cookiefile': cookies_path,
        'ignoreerrors': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'progress_hooks': [log_download_info]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            print(f"下载过程中出现错误: {e}")


if __name__ == "__main__":
    url = "https://www.bilibili.com/video/BV1HZ421U77y/?spm_id_from=333.1007.top_right_bar_window_history.content.click&vd_source=eda3cbcf7e9446aacb1cebdf3def86ca"
    cookies_path = "cookies.txt"
    download_bilibili_video(url, cookies_path)

