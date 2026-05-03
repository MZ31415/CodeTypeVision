"""
ctv-utils 工具集
生成视频; 制作图像; 模糊发光
-ω-
"""
from .render import *
from .constants import DC
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QImage 

from pathlib import Path

__all__ = ["create_video", "make_text_image", "blur_glow"]

def create_video(work_dir, video_name, frame_rate=30, start_index=0, end_index=None, 
                codec='libx264', preset='medium', crf=0, pix_fmt='yuv420p',
                ):
    """
    使用FFmpeg将PNG帧序列合成视频
        
    Args:
        work_dir: 工作目录,包含Frame0.png, Frame1.png等
        video_name: 输出视频文件名(带扩展名)
        frame_rate: 帧率
        start_index: 起始帧索引(默认0)
        end_index: 结束帧索引(None表示自动检测)
        codec: 视频编码器
        preset: 编码预设
        crf: 质量参数(0-51,越小质量越好)
        pix_fmt: 像素格式
        
    Returns:
        bool: 是否成功
    """
        
    # 转换为Path对象
    work_path = Path(work_dir)
    if end_index is None:
        raise ValueError("必须指定结束帧索引")
        
    print(f"视频信息:")
    print(f"  工作目录: {work_dir}")
    print(f"  帧范围: {start_index} - {end_index} (共{end_index - start_index + 1}帧)")
    print(f"  帧率: {frame_rate} FPS")
    print(f"  输出: {video_name}")
        
    # 构建FFmpeg命令
    input_pattern = str(work_path / "%d.png")
        
    # 构建完整的FFmpeg命令
    cmd = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-framerate', str(frame_rate),  # 输入帧率
        '-start_number', str(start_index),  # 起始编号
        '-i', input_pattern,  # 输入文件模式
        '-frames:v', str(end_index - start_index + 1),  # 总帧数
        '-c:v', codec,  # 视频编码器
        '-preset', preset,  # 编码预设
        '-crf', str(crf),  # 质量参数
        '-pix_fmt', pix_fmt,  # 像素格式
    ]
        
    cmd.append(str(work_path / video_name))
        
    print(f"FFmpeg命令: {' '.join(cmd)}")
        
    # 调试:检查文件是否存在
    print("\n检查文件...")
    frames_found = 0
    for i in range(start_index, end_index + 1):
        frame_file = work_path / f"{i}.png"
        if frame_file.exists():
            frames_found += 1
        else:
            print(f"找不到帧: {frame_file.name}")
            # return False
        
    print(f"  总共找到 {frames_found}/{end_index - start_index + 1} 个帧文件")
        
    if frames_found < (end_index - start_index + 1) / 2:  # 如果缺失超过一半的帧
        print("警告: 缺少很多帧文件")
        
    try:
        # 运行FFmpeg并显示实时输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
            universal_newlines=True,  # 文本模式
            bufsize=1,  # 行缓冲
            encoding='utf-8',
            errors='replace'
        )
        
        # 实时读取输出
        logtext = ""
        print("\n开始视频合成...")
        for line in process.stdout:
            line = line.rstrip()
            if "frame=" in line:
                print("\033[2K\r" + line, end="")
            else: logtext += line + "\n"

        # 等待进程完成
        process.wait()
        
        if process.returncode == 0:
            print(f"\n视频合成完成: {work_path / video_name}")
            
            # 检查输出文件
            output_file = work_path / video_name
            if output_file.exists():
                file_size = output_file.stat().st_size
                print(f"文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
                return True
            else:
                print("输出文件未生成")
                return False
        else:
            print("-"*10+logtext+"-"*10)
            print(f"\nFFmpeg失败,返回码: {process.returncode}")
            return False
            
    except FileNotFoundError:
        print("找不到ffmpeg, 请确保已安装并添加到PATH")
        return False
    except Exception as e:
        print(f"执行失败: {e}")
        return False

def make_text_image(txtData:list,
                font_size_k:float=0.6,
                color:tuple[int, int, int, int] = DC["D"],
                resolution:tuple[int, int] = (1920, 1080),
                blurglow:bool=True,
                render = Renderer()
            ) -> QImage: # 制作居中的文字图片
    render.estimate_render(resolution[0], txtData, font_size_k)
    origin = render.render_line(txtData)

    if blurglow: origin = blur_glow(origin) # 模糊发光
        
    bgimg = QImage(*resolution, QImage.Format_ARGB32)
    bgimg.fill(QColor(*color))

    bw, bh = resolution
    x = round( bw/2 - origin.width() /2 ) # 居中
    y = round( bh/2 - origin.height()/2 )
    painter = QPainter(bgimg)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    painter.drawImage(x, y, origin)
    painter.end()

    render = None
    return bgimg

# 模糊发光很粗糙 TODO: 考虑复用专业库实现功能 比如OpenCV的高斯模糊
def blur_glow(img:QImage, rate:float=10.0, alpha:float=0.6, num:int=3) -> QImage: # 简单地用模糊来发光
    bluring = QImage(img.size(), QImage.Format_ARGB32_Premultiplied)
    bluring.fill(Qt.transparent)
    painter = QPainter(bluring)  # 创建QPainter进行绘制
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)  # 设置混合模式
    painter.setOpacity(alpha)   # 设置画笔不透明度
    painter.drawImage(0, 0, img)
    painter.end()
    # 多次缩放 实现膨胀/抗锯齿效果 (差强人意)
    for _ in range(num):  # num在5左右效果最好;过小锯齿强, 过大导致膨胀"错误"
        bluring = bluring.scaled(
            int(img.width() * 1.5),
            int(img.height() * 1.5),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation # 模糊放大
        ).scaled(
            int(img.width() / rate),
            int(img.height() / rate),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation # 直接缩小
        )
    bluring = bluring.scaled(
            img.width(),
            img.height(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation # 放回原分辨率
        )
    glowing = QImage(img.size(), QImage.Format_ARGB32_Premultiplied)
    glowing.fill(Qt.transparent)

    painter = QPainter(glowing)  # 创建QPainter进行绘制
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)  # 设置混合模式
    painter.drawImage(0, 0, bluring)
    painter.drawImage(0, 0, img)
    painter.end()

    return glowing
