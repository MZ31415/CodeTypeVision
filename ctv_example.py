"""
ctv 调用示例
-ω-
"""
from ctv import *
from ctv.utils import make_text_image
from ctv.constants import DC
import os

from winsound import MessageBeep

if __name__ == "__main__":
    bgi = make_text_image([("- ω -", (238, 246, 248, 25))])
    bgip = os.path.join(os.path.dirname(__file__), "example_bgi.png")
    bgi.save(bgip) # 保存背景图片
    del bgi

    codetext = """\
print("Hello World!")
"""
    cdict = {
        "codeText": codetext,
        "configSG": {
            "mode": "S", # 目前仅有 S模式 (展示)
            "speed_function": [
                "F", # 目前仅有 F模式 (普通函数)
                "7.5" # 填f(t)的表达式, 如"0.5*t", t是时间
            ],
            "indentation_speed_index": 2.0, # 缩进速度指数
            "time_limit": "*1", # 限制时间
            "start_rest": 1.0,
            "end_rest": 7.0
        },
        "configCS": {
            "mode": "D", # 目前仅D模式 (默认)
            "spring_k": 2.5,
            "damping": 0.8,
            "shaking_ks": [
                0.75,
                0.75
            ],
            "cycle": 5.0
        },
        "language": "Python",
        "headText": "example.py",
        "mp4Name": "example.mp4",
        "fps": 30,
        "resolution": (1920,1080),
        "background_img": bgip
    }

    c = Config(**cdict)
    f = CTVField(c)
    try:
        f.main()
    finally:
        MessageBeep()
