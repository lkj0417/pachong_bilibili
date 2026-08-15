import speech_recognition as sr
from pydub import AudioSegment
import os
import sys


def transcribe_audio(audio_path, language="zh-CN"):
    """
    将音频文件转换为文字 (使用 Google 语音识别)
    
    参数:
        audio_path: 音频文件路径
        language: 语言代码 (zh-CN=中文, en-US=英文)
    """
    if not os.path.exists(audio_path):
        print(f"错误: 找不到文件 {audio_path}")
        return None
    
    print(f"正在处理音频: {audio_path}")
    
    # 转换音频为 wav 格式 (Google 语音识别需要 wav)
    print("正在转换音频格式...")
    audio = AudioSegment.from_file(audio_path)
    
    # 导出为临时 wav 文件
    temp_wav = "temp_audio.wav"
    audio.export(temp_wav, format="wav")
    
    # 使用语音识别
    recognizer = sr.Recognizer()
    
    with sr.AudioFile(temp_wav) as source:
        print("正在读取音频数据...")
        audio_data = recognizer.record(source)
    
    # 删除临时文件
    os.remove(temp_wav)
    
    print("正在识别文字 (使用 Google 语音识别)...")
    print("这可能需要几分钟，请耐心等待...")
    
    try:
        # 使用 Google 语音识别
        text = recognizer.recognize_google(audio_data, language=language)
        return text
    except sr.UnknownValueError:
        print("无法识别音频内容")
        return None
    except sr.RequestError as e:
        print(f"请求错误: {e}")
        return None


def save_transcription(text, output_path):
    """保存转录结果到文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"转录结果已保存到: {output_path}")


if __name__ == "__main__":
    # 获取音频文件路径
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # 自动查找当前目录下的第一个 m4a 文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        m4a_files = [f for f in os.listdir(script_dir) if f.endswith('.m4a')]
        if m4a_files:
            audio_file = os.path.join(script_dir, m4a_files[0])
            print(f"自动找到音频文件: {m4a_files[0]}")
        else:
            print("错误: 找不到音频文件")
            print("用法: python audio_to_text_simple.py <音频文件路径>")
            sys.exit(1)
    
    # 检查文件是否存在
    if not os.path.exists(audio_file):
        print(f"错误: 找不到音频文件: {audio_file}")
        print("用法: python audio_to_text_simple.py <音频文件路径>")
        sys.exit(1)
    
    # 执行转录
    transcription = transcribe_audio(audio_file, language="zh-CN")
    
    if transcription:
        # 生成输出文件名
        base_name = os.path.splitext(audio_file)[0]
        output_file = base_name + "_转录.txt"
        
        # 保存结果
        save_transcription(transcription, output_file)
        
        # 同时在控制台输出
        print("\n" + "="*50)
        print("转录结果:")
        print("="*50)
        print(transcription)
        print("="*50)
