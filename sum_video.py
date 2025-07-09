import os
import subprocess


def merge_mp4_videos_ffmpeg():
    current_dir = os.getcwd()
    mp4_files = [f for f in os.listdir(current_dir) if f.endswith('.mp4')]

    # 智能排序（支持带数字前缀的文件名，如 lesson1.mp4）
    mp4_files.sort(key=lambda x: int(''.join([i for i in x if i.isdigit()])))

    if not mp4_files:
        print("当前目录下没有 .mp4 文件。")
        return

    # 创建临时目录
    temp_dir = os.path.join(current_dir, 'temp_merge')
    os.makedirs(temp_dir, exist_ok=True)

    # 第一步：预处理所有视频（统一编码并修复时间戳）
    print("正在预处理视频文件...")
    processed_files = []
    for i, file in enumerate(mp4_files):
        input_path = os.path.join(current_dir, file)
        output_path = os.path.join(temp_dir, f"processed_{i:04d}.mp4")

        # 使用严格的编码参数，统一为 H.264 + AAC
        command = [
            'ffmpeg',
            '-i', input_path,
            '-vcodec', 'libx264',
            '-acodec', 'aac',
            '-strict', 'experimental',
            '-reset_timestamps', '1',
            '-y',
            output_path
        ]
        subprocess.run(command, check=True)
        processed_files.append(output_path)

    # 第二步：生成合并列表
    list_file_path = os.path.join(temp_dir, 'file_list.txt')
    with open(list_file_path, 'w', encoding='utf-8') as f:
        for file in processed_files:
            f.write(f"file '{file}'\n")

    # 第三步：合并视频（添加视频滤镜处理可能的不兼容）
    output_file = os.path.join(current_dir, 'merged_video_fixed.mp4')
    try:
        command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file_path,
            '-vf', 'pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2',  # 修复奇数分辨率
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-y',
            output_file
        ]
        subprocess.run(command, check=True)
        print(f"视频已合并并保存为 {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"合并视频时出错: {e}")
    finally:
        # 清理临时文件
        for f in processed_files + [list_file_path]:
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(temp_dir)


if __name__ == "__main__":
    merge_mp4_videos_ffmpeg()