import whisper
import os
import sys


def transcribe_audio(audio_path, model_size="base", language="zh"):
    """
    将音频文件转换为文字 (使用 Whisper)
    
    参数:
        audio_path: 音频文件路径
        model_size: 模型大小 (tiny, base, small, medium, large)
        language: 语言代码 (zh=中文, en=英文)
    """
    if not os.path.exists(audio_path):
        print(f"错误: 找不到文件 {audio_path}")
        return None
    
    print(f"正在加载 Whisper {model_size} 模型...")
    model = whisper.load_model(model_size)
    
    print(f"正在转录音频: {audio_path}")
    print("这可能需要几分钟，请耐心等待...")
    
    # 执行转录
    result = model.transcribe(audio_path, language=language, fp16=False)
    
    return result["text"]


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
            print("用法: python audio_to_text_whisper.py <音频文件路径>")
            sys.exit(1)
    
    # 检查文件是否存在
    if not os.path.exists(audio_file):
        print(f"错误: 找不到音频文件: {audio_file}")
        print("用法: python audio_to_text_whisper.py <音频文件路径>")
        sys.exit(1)
    
    # 执行转录
    transcription = transcribe_audio(audio_file, model_size="base", language="zh")
    
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
