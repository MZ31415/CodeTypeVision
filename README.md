# CodeTypeVision - 代码打字机视频生成器

## 项目简介

CodeTypeVision (简称 CTV) 是一个将代码文本转换为动态视频的工具, 通过"打字机"效果展示编程过程. 该工具适用于社交媒体分享与创意表达场景, 将静态代码转换为动态视觉内容. 使用Python语言编写.
CodeTypeVision 原名为 CodeToVideo, 简称一致.

## 演示视频

演示视频如下:
![helloWorld_c](./helloWorld_c.mp4)

相关视频也可在我的 B站空间 [一勺云墨](https://space.bilibili.com/3546881812597194) 查看.

## 特性

### 基本功能

- **实时打字动画**: 模拟逐字输入代码的过程
- **语法高亮**: 支持多种编程语言的语法着色
- **多语言支持**: Python,C,C++,C#,Java 等
- **流畅相机运动**: 光标跟随, 平滑缩放与移动
- **连体字支持**: 支持连体字体显示
- **模糊发光效果**: 代码光晕效果
- **默认高亮色**: 基于国色色系

### 性能

- **异步渲染系统**: 多核并行处理
- **缓存机制**: 减少重复计算, 优化内存使用
- **可配置并发**: 支持自定义并行任务数量上限 `MAX_CONCURRENT`

### 控制选项

- **参数化配置**: 速度,颜色,效果 可自定义
- **背景艺术生成**: 内置文字背景生成器
- **头文本**: 支持视频标题与描述添加
- **时间线控制**: 可调节打字节奏与停顿时长

## 开始使用

### 下载

可通过终端克隆仓库, 或直接下载核心文件 [codeTypeVision](./codeTypeVision0.4.7.py):

```bash
git clone https://github.com/mz31415/CodeTypeVision.git
cd CodeTypeVision
pip install -r requirements.txt
```

### 依赖

#### FFmpeg

需下载 [FFmpeg](https://ffmpeg.org/) 并添加至系统环境变量, 用于将帧序列合成为 `.mp4` 格式视频文件.

#### Python

除 Python3 外, 需通过 **pip** 安装以下库:

- **Pygments**: 语法高亮引擎
- **PyQt5**: 图形渲染 (不使用 GUI, 仅用于高质量图像绘制)
- **tqdm**: 进度条显示

可通过以下命令安装依赖:

```bash
pip install -r requirements.txt
```

若未下载 [requirements.txt](requirements.txt), 可执行:

```bash
pip install PyQt5>=5.15.0 pygments>=2.10.0 tqdm>=4.64.0
```

#### 可选依赖

- **Fira Code**: 建议安装字体 [Fira Code](https://github.com/tonsky/FiraCode), 该字体为默认配置. 若未指定新字体, 运行时会打印警告, 但不影响程序运行.
- **Windows 系统**: 代码中引入标准库 `winsound` 用于播放提示音. 非 Windows 系统下, 提示音功能不可用, 但程序仍可正常运行.

### 使用教程

#### 外部调用

在与 `codeTypeVision.py` 同级目录下新建 `.py` 文件:

```python
from PyQt5.QtGui import QImage
from codeTypeVision import Field, CodeLineRenderer

# 简单示例
# text 参数为必需项; 其他建议填写参数已标注
field = Field(
    text = "printf('Hello World')\n",             # 待转换代码文本, 须以"\n"结尾
    #video_output_dir=os.path.dirname(__file__),  # 视频输出目录
    video_name = "HelloWorld.mp4",                # 视频文件名(须以.mp4结尾)
    speed_function = lambda _:7.5,                # 字符速度函数 v = f(index),单位为字符/秒
    limit = "-60.0",                              # 限制:"*zoom" 按缩放因子控制速度;"-time(s)" 自动计算缩放因子以满足时间限制
    indentation_speed = 2.5,                      # 缩进速度倍率, 默认1.0
    start_rest = 3.0,                             # 起始停顿(秒), 默认为 0.0
    end_rest = 5.0,                               # 结束停顿(秒), 默认为 0.0
    frame = 30,                                   # 输出视频帧率, 默认 24
    background_img = QImage(r".\IMG_PATH"),       # 背景图片(QImage 对象),分辨率应与 resolution 比例一致
    head_txt = "HelloWorld.c",                    # 头文本
    language = "c",                               # 代码语言(支持文件后缀名), 默认 py
    #resolution = (1920, 1080),                   # 分辨率(宽×高), 默认(1920, 1080)
    #render = CodeLineRenderer(font0="", font1="")# 字体参数:font0 为主字体,font1 为中文字体
)
field.main() # 生成视频
```

#### 内部使用

**更建议**直接修改原代码运行:

```python
# CodeTypeVision.py 文件内...

if __name__ == "__main__": # 示例使用
    # nowtime 为全局函数
    # THIS_PATH = os.path.dirname(__file__) + "\\" # 全局变量
    
    print(nowtime() + " 程序开始运行...")
    
    bg = make_text_image([("- ω -", (238, 246, 248, 25))]) # 快速生成背景图

    make_text_image([
        ("Hello World", Field.HC["P"]),    # Field.HC 为 RGBA 颜色字典
        ],
        resolution=(2000,1500)).save(THIS_PATH + "helloWorld_cover.png") # 保存封面图片

    try:
        txt = quick_open(THIS_PATH + r"showings\helloWorld.c") # 读取代码文件
        field = Field(txt,
                    video_name = "helloWorld_c.mp4",
                    speed_function = lambda _:7.5,
                    frame = 30,
                    start_rest = 1.0,
                    end_rest = 5.0,
                    limit = "-30",
                    indentation_speed = 2.5,
                    background_img = bg,
                    head_txt = "helloWorld.c",
                    language = "c"
                )

        field.main()
    finally:  # 提示与错误处理
        for _ in range(3):
            sleep(0.5)
            MessageBeep()
        #input("按回车键退出...")

```

## 文件输出

### 默认输出

- `{output}_preview.png`: 代码全局预览图
- `{output}.mp4`: 生成的视频文件

### 自定义输出

- **封面**: 可使用 `make_text_image` 函数生成封面或其他图片文件

## 版本说明

当前最新版本为 **0.4.7**(截至 2026 年 2 月 11 日), 该版本实现了异步渲染功能.

代码注释中包含了进一步的使用说明.

过去的旧版本未上传.

### 已知问题

1. 输入代码文本**必须**以非 `\n` 开头,以 `\n` 结尾.以 `\n` 开头可能引发错误,不以 `\n` 结尾将导致最后一个字符在视频中被省略.**该问题尚未修复.**
2. 缺少异常处理, 部分代码存在报错风险或帧图像缺失可能.
3. 存在较多硬编码, 类结构有待优化.
4. 生成视频效果为顺序打字机输出, 视觉上类似于代码删除过程的倒放.
5. 工作目录管理机制不够完善.
6. 其他细节问题待改进.

**后续版本计划**: 预计将在 0.5 版本中对上述问题进行修正. (可能会在年后更新)

## 贡献

欢迎各类形式的贡献.

## 许可证

本项目采用 MIT 许可证.详见 [LICENSE](LICENSE) 文件.

## 致谢

本项目依赖以下技术实现:

- **Pygments**: 语法高亮引擎
- **PyQt5**: 图形渲染框架
- **FFmpeg**: 视频编码工具
- **Fira Code**: 编程字体

感谢 DeepSeek-AI 提供的部分编程建议与指导.

**感谢您的阅读!!**

如您使用 CTV 生成视频并发布于社交媒体, **请注明项目出处**; 若发布于 B站, 欢迎 **at我** `@一勺云墨`.

---

`-ω-`
