# CodeTypeVision (CTV) - 代码打字机视频生成器

## 项目简介

**CodeTypeVision**(简称 `ctv`)是一个将代码文本转换为动态视频的工具, 以**打字机效果**逐字展示编程过程, 并自动添加语法高亮, 光标跟随与平滑相机运动. 为了拟合录屏效果而制作.

原项目名 `CodeToVideo`, 现重构成模块化框架, 支持配置文件, 多语言, 艺术化背景等特性.

你可以在我的 B 站空间 [云墨-w](https://space.bilibili.com/3546881812597194) 查看一些相关投稿视频.

---

## 主要特性

### 核心功能

- **实时打字动画** – 逐字模拟输入, 支持自定义速度曲线
- **语法高亮** – 基于 Pygments, 支持 Python / C / C++ / C# / Java 等语言
- **光标跟随 + 行高亮** – 自动追踪当前行与当前字符位置
- **平滑相机系统** – 弹簧‑阻尼模型, 光标居中, 自动缩放
- **连体字支持** – 完美显示 `→` `=>` 等 Fira Code 连体
- **内置视觉效果** – 代码模糊发光, 行高亮块

### 可配置性

- **参数化配置** – 速度, 缩放, 阻尼, 颜色均可自由调节
- **JSON 配置文件** – 一键保存/加载完整设置, 适合批量生成
- **命令行接口** – 支持 `ctv -c config.json` 无交互运行
- **背景/封面生成** – `make_text_image` 快速生成艺术字图片

### 性能与架构(v0.5.0)

- **模块化分层** – config / data / render / core / utils 清晰分离
- **QTextLayout 渲染** – 精确处理连体字与字符边界
- **无异步依赖** – 稳定串行处理(未来可扩展多进程)
- **缓存机制** – 行图片增量更新, 避免重复渲染

---

## 开始使用

### 1. 获取代码

```bash
git clone https://github.com/mz31415/CodeTypeVision.git
cd CodeTypeVision
```

或直接下载最新 Release 中的 `ctv-0.5.0.zip`,解压后得到 `ctv/` 文件夹.

### 2. 安装依赖

#### Python 包

```bash
pip install PyQt5>=5.15.0 pygments>=2.10.0 tqdm>=4.64.0
```

#### FFmpeg(必需)

用于将生成的帧序列合成为 `.mp4` 视频.  

- 官网下载:[FFmpeg](https://ffmpeg.org/)  
- 添加 `bin` 目录到系统环境变量 `PATH`,确保终端输入 `ffmpeg -version` 能正确显示.

#### 字体

- **Fira Code** – 默认英文字体(连体字效果最佳).  
  可从 [GitHub](https://github.com/tonsky/FiraCode) 下载安装.  
- 默认状态系统会自动 fallback 到 `Consolas` 或 `Microsoft YaHei` 等中文字体.
- 调整配置 `fonts` 进行自定义字体修改

### 3. 快速生成视频

#### 方式一:使用配置文件(推荐)

```bash
# 生成示例配置文件(在 ./example_config.json)
ctv -e

# 编辑 example_config.json,然后执行
ctv -c example_config.json
```

#### 方式二:Python 脚本调用

```python
from ctv import Config, CTVField

# 构建配置对象
config = Config(
    codeText='printf("Hello World\\n");',
    language='c',
    mp4Name='hello_c.mp4',
    headText='hello.c',
    start_rest=1.0,
    end_rest=5.0,
    # 更多参数见 config.py 中的 Config 类
)

field = CTVField(config)
field.main()
```

---

## 配置文件说明

`Config` 类 (`config.py`) 支持以下主要字段:

| 字段 | 类型 | 说明 |
|------|------|------|

| `codeText` | str | 要转换的代码文本(必需) |
| `language` | str | 代码语言(py / c / cpp / cs / java),默认 "python" |
| `mp4Name` | str | 输出视频文件名(自动补 `.mp4`) |
| `fps` | int | 帧率(建议 24~60) |
| `resolution` | (w,h) | 视频分辨率,默认 (1920,1080) |
| `headText` | str | 显示在代码上方的标题文字, 默认无 |
| `background_img` | QImage / str | 背景图片(路径或 QImage 对象) |
| `speed_function` | tuple[str, str] | 速度函数 `v = f(t)`,默认 `lambda t: 7.5` |
| `indentation_speed_index` | float | 缩进速度指数,默认 2.0 |
| `time_limit` | str | `"*1.5"` 缩放因子 / `"-30"` 限制时长(秒) / 为 `""` 时可动态调整|
| `start_rest` / `end_rest` | float | 开头 / 结尾静置时间(秒) |
| `fonts` | list[str] | 字体家族列表(fallback) |

关于`speed_function`, 目前请填入 ["F", `{f(t)}`], 如 ["F", "7.5"], ["F", "t"]

完整配置可通过 `ctv -e` 生成示例 JSON,亦可在 Python 中动态修改.

---

## 输出文件

- **视频文件** – `{mp4Name}` 保存在 `outputDir`(默认项目根目录)
- **预览图** – `{mp4Name}_preview.png` 展示完整代码长图(缓存图片在 `temp/` 目录)
- **中间文件** – 默认在项目根目录生成 `ctv_{视频名}/` 文件夹,包含:
  - `temp/` – 渲染的原始行图片(`*.png`)
  - `frames/` – 合成的视频帧(`0.png`, `1.png`, …)

> 目前请自行清理 `ctv_*` 临时文件夹以释放磁盘空间.

---

## 版本说明

### v0.5.0(当前版本)– 框架重置

- **完全模块化**: 分离 config/data/render/core/utils,代码结构清晰
- **QTextLayout 渲染**: 支持连体字与精确光标定位
- **配置文件系统**: 支持 JSON 保存/加载, 提供 CLI 工具
- **移除异步依赖**: 串行处理更稳定
- **已知问题**: 暂未恢复异步/多进程加速; 部分极端括号嵌套可能影响渲染; 不支持 Execution 模式(预留).

### 历史版本(v0.4.7 及更早)

- `v0.4.7` 异步并发设计; 对括号等字符无特殊处理; 字体支持有限; 语法高亮有限.
- 代码为单文件结构, 现已废弃.
- v0.4即以前的代码不在此仓库保留

---

## PS

> 0.5.0版本基本实现框架 并且可以运行, 但部分不合理, 部分仅存在预留模式接口 而没有实现; 下次更新可能很久(预计1年后, 2027.7)

---

## 贡献与许可证

- **贡献**:欢迎提交 Issue / PR, 或分享你的创意视频作品.
- **许可证**:MIT [LICENSE](./LICENSE).

---

## 致谢

- **Pygments** – 语法高亮引擎
- **PyQt5** – GUI提供高质量图形渲染
- **FFmpeg** – 视频编码
- **Fira Code** – 优美的编程字体
- **DeepSeek AI** – 提供部分代码建议与思路

> 如果本项目对你有所帮助, 欢迎给个 ⭐ Star.  
> 若你在 B站 发布使用 CTV 制作的视频, 欢迎 **@云墨-w**.

---

`-ω-`
