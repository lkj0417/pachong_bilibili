import yt_dlp
import os
import re

def sanitize_filename(filename):
    # 使用正则表达式提取 p01, p02 这样的编号，并保留后面的标题部分
    match = re.search(r'p(\d+)\s*(.*)', filename)  # 匹配以 p 开头的编号
    if match:
        number = match.group(1)  # 提取编号部分
        title = match.group(2).strip()  # 提取标题部分
        return f"{number.zfill(2)} {title}"  # 使用编号和标题重新格式化文件名
    return filename  # 如果匹配失败，返回原文件名

def download_bilibili_video(url, cookies_path):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # 选择最优视频+音频，并自动合并
        'outtmpl': '%(title)s.%(ext)s',  # 先下载为原始标题
        'merge_output_format': 'mp4',  # 指定合并后的格式
        'cookiefile': cookies_path,
        'ignoreerrors': True,  # 忽略下载过程中的错误
        'postprocessors': [{  # 添加后处理器
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # 确保合并后输出为 MP4 格式
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            print(f"下载过程中出现错误: {e}")

    # 下载完成后重命名文件
    for filename in os.listdir():
        if filename.endswith(".mp4"):  # 确保只处理视频文件
            new_name = sanitize_filename(filename)
            if new_name != filename:  # 如果文件名有变化
                print(f"重命名文件: {filename} -> {new_name}")
                os.rename(filename, new_name)

if __name__ == "__main__":
    url = "https://www.bilibili.com/video/BV1HZ421U77y/?spm_id_from=333.1007.top_right_bar_window_history.content.click&vd_source=eda3cbcf7e9446aacb1cebdf3def86ca"
    cookies_path = "cookies.txt"
    download_bilibili_video(url, cookies_path)
