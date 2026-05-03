"""
ctv-config 配置
一些配置类, 用于构造核心中的类, 方便载入与保存配置
-ω-
"""
from .render import Renderer
from .constants import DEFAULT_BACKGROUND_COLOR
from PyQt5.QtGui import QImage, QColor
import os, json

from dataclasses import dataclass, asdict

__all__ = ["speedFunction", "Config"]

# TODO: speedFunction 不应该在此文件下
class speedFunction: # TODO: 适配音频传入获取速度函数
    def __init__(self, param:tuple[str, str]):
        try: param = tuple(param)
        except: raise ValueError("速度函数参数必须可以转换为元组")

        if len(param)!=2:
            raise ValueError("速度函数参数长度不为2")
        if not (isinstance(param[0], str) and isinstance(param[1], str)):
            raise ValueError("速度函数参数内容非字符串")

        self.param = param # 生成所需参数

        if self.param[0]=="F":
            try:
                self.f = eval(f"lambda t: {self.param[1]}")
            except Exception as e: raise ValueError(f"表达式错误:\n{e}")
            try: float(self.f(0.0))
            except: raise ValueError("表达式不能按预期使用")
        # TODO 
        else:
            raise ValueError(f"速度函数暂时不支持模式 {self.param[0]}")

    def __call__(self, time:float)->float:
        return self.f(time)

@dataclass
class Config:
    """集中管理所有配置"""
    codeText: str # 代码文本
    
    # 模式配置
    configSG: "ConfigSG" # 可传 dict (因为写成 "ConfigSG"|dict 会对IDE注解产生影响, 这里就这么写了)
    configCS: "ConfigCS" # 可传 dict (这种最后都会初始化为对应的类)

    # 代码语言 # 正常应该位于代码文本下一个的, 但是为了给默认值只能置后
    language: str = "python"

    # 视频参数    
    mp4Name: str = "output.mp4"
    fps: int = 30
    resolution: tuple[int, int] = (1920, 1080)

    headText: str | None = None

    # 渲染参数
    fonts: list[str] = None
    renderer: Renderer = None    # 之后会初始化为 Renderer

    fontSizes: tuple[int,int] = None # (最大, 标准) 字号组
    fontProportion: tuple[float, float] = (0.3, 0.1) # 通过比例来自动获取字号组 (最大, 标准)

    background_img: QImage = None # 可以传路径字符串 # 要求图像分辨率比例必须和resolution一致(不会 调整比例或  进行自适应等)

    # 输出参数
    outputDir: str = ""
    workDir: str = ""

    #step: str = ""  # SRCF 所在步骤(尚未完成的步骤), ""空表示未开始 # TODO: 如字符串所示
    # TODO: 补全可能的剩余参数

    def __post_init__(self):
        """验证配置有效性"""
        # 视频参数
        if not (self.codeText and isinstance(self.codeText, str)):
            raise ValueError("代码文档codeText必须有效, 必须为非空字符串")
        self.codeText = self.codeText.replace(" "*4, "\t") # 使用\t换4空格缩进 # 问题是如果不是4缩进?(难以考虑)
        
        if type(self.configSG) is not ConfigSG and issubclass(type(self.configSG), ConfigSG):
            pass # 只准子类通过
        elif isinstance(self.configSG, dict):
            try:
                self.configSG = ConfigSG.creat_son(self.configSG)
            except Exception as e:
                raise ValueError(f"验证参数 序列获取器配置configSG 时, 发生错误:\n{e}")
        else: raise TypeError("序列获取器配置configSG类型不支持")

        if type(self.configCS) is not ConfigCS and issubclass(type(self.configCS), ConfigCS):
            pass # 只准子类通过
        elif isinstance(self.configCS, dict):
            try:
                self.configCS = ConfigCS.creat_son(self.configCS)
            except Exception as e:
                raise ValueError(f"验证参数 相机系统配置configCS 时, 发生错误:\n{e}")
        else: raise TypeError("相机系统配置configCS类型不支持")


        if not isinstance(self.language, str):
            raise TypeError("代码语言language类型必须有效, 必须为字符串")
        else:
            table = { # 目前只列举一些部分主流语言及常用后缀
                "python": "Python",
                "py":     "Python",
                "c":      "C",
                "c++":    "Cpp",
                "cpp":    "Cpp",
                "c#":     "CSharp",
                "csharp": "CSharp",
                "cs":     "CSharp",
                "jave":   "Java",
                "txt":    "", # 这仅仅是文本, 不算语言
                "text":   "",
                "":       ""
            }
            try:
                self.language = table[self.language.lower()]
            except KeyError:
                raise ValueError(f"代码语言language必须是可用的, {self.language}不可用")
            except Exception as e:
                raise ValueError(f"验证参数 代码语言language 时, 发生未知错误:\n{e}")
            
        if not isinstance(self.headText, str) and self.headText is not None:
            raise TypeError("头文本headText类型必须有效, 必须为字符串或None")

        if (not isinstance(self.fps, int)) or self.fps <= 0:
            raise ValueError("帧率fps必须有效")
        
        try: self.resolution = tuple(self.resolution)
        except: raise TypeError("分辨率resolution必须可以转换为元组")
        if len(self.resolution)!=2 or self.resolution[0]<=0 or self.resolution[1]<=0:
            raise ValueError("分辨率resolution必须有效")
        
        
        if not (self.mp4Name and isinstance(self.mp4Name, str)):
            raise TypeError("输出视频名称mp4Name类型必须有效, 必须为非空字符串")
        elif self.mp4Name[-4:] != ".mp4":
            if "." not in self.mp4Name:
                self.mp4Name += ".mp4"
                #logging.warning("输出视频名称mp4Name目前必须要以'.mp4'为结尾, 已自动添加文件名后缀") # TODO: 警告
            else:
                raise ValueError("输出视频名称mp4Name目前必须要以'.mp4'为结尾")

        # 渲染参数
        if not isinstance(self.renderer, Renderer) and self.fonts is not None:
            if not isinstance(self.fonts, list):
                raise TypeError("字体fonts类型必须有效, 必须为列表")
            if not all(isinstance(f, str) for f in self.fonts):
                raise TypeError("字体fonts元素类型必须有效, 必须为字符串")
            
            try:
                self.renderer = Renderer(fonts=self.fonts)
            except Exception as e:
                raise Exception(f"生成渲染器实例错误:\n{e}") # 最可能是缺失字体
        else:
            if not isinstance(self.renderer, Renderer):
                self.renderer = Renderer()
            self.fonts = self.renderer.font_families
        
        if self.fontSizes is not None:
            try: self.fontSizes = tuple(self.fontSizes)
            except: raise TypeError("字体字号组需要可以转换为元组")
            if len(self.fontSizes)!=2: raise ValueError("字体字号组需要长度为2")
            if not all(isinstance(fs, int) for fs in self.fontSizes):
                raise TypeError("字体字号组需要为两个整形")
            if not all(fs>0 for fs in self.fontSizes):
                raise ValueError("字体字号组需要为两个正值")
            if self.fontSizes[0]<self.fontSizes[1]:
                raise ValueError("字体字号组中, 第一个为最大值, 第二个为标准值, 前者需要大于等于后者")
            self.renderer.set_font_size(self.fontSizes[0])
        else:
            try: self.fontProportion = tuple(self.fontProportion)
            except: raise TypeError("字体尺寸比例组需要可以转换为元组")
            if len(self.fontProportion)!=2: raise ValueError("字体尺寸比例组需要长度为2")
            try: self.fontProportion = tuple(float(fs) for fs in self.fontProportion) # 吐槽: 为什么这颗糖返回生成器
            except: raise TypeError("字体尺寸比例组需要为两个浮点数")
            if any(fs<=0 for fs in self.fontProportion):
                raise ValueError("字体尺寸比例组需要为两个正值")
            if self.fontProportion[0]<self.fontProportion[1]:
                raise ValueError("字体尺寸比例组中, 第一个为最大值, 第二个为标准值, 前者需要大于等于后者")
            if any(fs>1.0 for fs in self.fontProportion):
                ... # TODO: 警告
                #logging.warning(f"字体尺寸比例组中, 数值不建议超过1.0, 目前值 {self.fontProportion}")
            sf = self.renderer.estimate_render(self.resolution[0], k=self.fontProportion[1])   
            mf = self.renderer.estimate_render(self.resolution[0], k=self.fontProportion[0])
            self.fontSizes = (mf, sf)
        self.fontProportion = None

        if (not self.background_img) or not isinstance(self.background_img, QImage) or self.background_img.isNull():
            if isinstance(self.background_img, str):
                if not os.path.exists(self.background_img):
                    raise FileNotFoundError(f"背景图片background_img {self.background_img} 不存在")
                try: self.background_img = QImage(self.background_img)
                except Exception as e: raise Exception(f"背景图片background_img 输入的str不能用于构造QImage对象:\n{e}")
                
                self.background_img = self.background_img.scaledToWidth(self.resolution[0])
                if self.background_img.height() != self.resolution[1]:
                    raise ValueError("背景图片background_img比例与视频分辨率不一致")

            else:
                self.background_img = QImage(*self.resolution, QImage.Format_ARGB32)
                self.background_img.fill(QColor(*DEFAULT_BACKGROUND_COLOR))
            
        # 输出参数
        if not isinstance(self.outputDir, str):
            raise TypeError("输出目录outputDir类型必须有效, 必须为字符串")
        if not isinstance(self.workDir, str):
            raise TypeError("工作目录workDir类型必须有效, 必须为字符串")
        
        dp = os.path.dirname(os.path.dirname(__file__))
        self.outputDir = self.outputDir or dp # 使用短路将""切换为默认值
        name = os.path.splitext(self.mp4Name)[0]
        self.workDir = self.workDir or os.path.join(dp, f"ctv_{name}")
        
        # TODO: 三个目录是否可用

        # TODO: ?

    def save(self, save_path:str="", save_name:str="congfig.json") -> bool: # 保存路径不含文件名
        if not save_path: save_path = self.workDir
        if not os.path.exists(save_path): # 如果你传路径+文件名...懒得改
            os.makedirs(save_path)

        bgpath = os.path.join(save_path, f"background_img.png")
        self.background_img.save(bgpath)

        config_dic = { # asdict 似乎不好使了(对那些不能pickle的, 但是我本来就要忽略它们 换其他值...)
            "codeText":       self.codeText,
            "configSG":       self.configSG.json_data,
            "configCS":       self.configCS.json_data,
            "language":       self.language,
            "headText":       self.headText,
            "mp4Name":        self.mp4Name,
            "fps":            self.fps,
            "resolution":     self.resolution,
            "fonts":          self.fonts,
            "renderer":       None,
            "background_img": bgpath,
            "outputDir":      self.outputDir,
            "workDir":        self.workDir
        }

        sp = os.path.join(save_path, save_name)
        
        try:
            with open(sp, 'w', encoding='utf-8') as f:
                json.dump(config_dic, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置config数据时发生错误:\n{e}")
            #logging.warning(f"保存配置config数据时发生错误:\n{e}") # TODO: 警告
            return False

    @classmethod
    def load(cls, json_path:str) -> "Config":
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            return cls(**loaded_data)
        
        except FileExistsError as e:
            raise FileExistsError(f"载入数据:{json_path}文件不存在:\n{e}")
        except Exception as e:
            raise Exception(f"载入数据时发生未知错误:\n{e}")

    @classmethod
    def creat_default(cls) -> "Config":
        return cls("print('Hello World!')\n", ConfigSG.creat_default(), ConfigCS.creat_default())
    
    @classmethod
    def save_example(cls, save_path:str="", save_name="congfig.json") -> bool:
        c = cls.creat_default()
        return c.save(save_path, save_name)

class ConfigMode:
    @property
    def mode(self): raise NotImplementedError

    @property
    def json_data(self) -> dict: return {"mode":self.mode} | asdict(self)

    @property
    def data(self) -> dict: return {"mode":self.mode} | asdict(self)

    @classmethod
    def creat_son(cls) -> "ConfigMode": raise NotImplementedError

    @classmethod
    def creat_default(cls) -> "ConfigMode": raise NotImplementedError

class ConfigSG(ConfigMode):
    @classmethod
    def creat_son(cls, kv:dict) -> "ConfigSG":
        if kv["mode"]=="S":
            del kv["mode"]
            return ConfigShowingModeSG(**kv)
        #elif mode=="E":
        else:
            raise ValueError(f"模式 {kv["mode"]} 未实现")

    @classmethod
    def creat_default(cls) -> "ConfigSG":
        return cls.creat_son({"mode":"S"})

@dataclass
class ConfigShowingModeSG(ConfigSG):
    speed_function: speedFunction = speedFunction(("F", "7.5")) # 可传列表
    indentation_speed_index: float = 2.0
    time_limit: str = ""
    start_rest: float = 5.0
    end_rest: float = 5.0

    @property
    def mode(self): return "S"

    @property
    def json_data(self) -> dict:
        return {
                "mode": self.mode,
                "speed_function": self.speed_function.param,
                "indentation_speed_index": self.indentation_speed_index,
                "time_limit": self.time_limit,
                "start_rest": self.start_rest,
                "end_rest": self.end_rest
            }

    def __post_init__(self):
        if not isinstance(self.speed_function, speedFunction):
            self.speed_function = speedFunction(self.speed_function)

        if not isinstance(self.indentation_speed_index, float):
            raise TypeError("缩进速度指数 必须是float类型")

        if not isinstance(self.time_limit, str):
            raise TypeError("时间限制 必须是str类型")
        if self.time_limit!="":
            if self.time_limit[0] not in "-*":
                raise ValueError("时间限制 格式错误")
            try: float(self.time_limit[1:])
            except Exception as e: raise ValueError("时间限制 值错误")

@dataclass
class ConfigExecutionModeSG(ConfigSG): ... # TODO: v0.6做

class ConfigCS(ConfigMode):
    @classmethod
    def creat_son(self, kv:dict) -> "ConfigCS":
        if kv["mode"]=="D":
            del kv["mode"]
            return ConfigDefaultCS(**kv)
        #elif mode=="E":
        else:
            raise ValueError(f"模式 {kv["mode"]} 未实现")
        
    @classmethod
    def creat_default(cls) -> "ConfigSG":
        return cls.creat_son({"mode":"D"})

@dataclass
class ConfigDefaultCS(ConfigCS):
    spring_k: float = 1.75
    damping: float = 0.85
    shaking_ks: tuple[float,float] = (1.0, 1.6)
    cycle: float = 5.0
    
    @property
    def mode(self) -> str: return "D"

    def __post_init__(self):
        try: self.spring_k = float(self.spring_k)
        except: raise TypeError("弹簧系数类型必须为数值")
        if self.spring_k<=0: raise ValueError("弹簧系数必须为正数")

        try: self.damping = float(self.damping)
        except: raise TypeError("阻尼值类型必须为数值")
        if not (0.0<=self.damping<=1.0): raise ValueError("阻尼值必须在[0,1]内")
        
        try: self.shaking_ks = tuple(self.shaking_ks)
        except: raise TypeError("晃动振幅类型必须可以转为元组")

        if len(self.shaking_ks)!=2:
            raise ValueError("晃动振幅类型必须可以元组, 并且有且仅有两个值")
        for v in self.shaking_ks:
            try: float(v)
            except: raise ValueError("晃动振幅元素类型必须为数值")
            if v<0: raise ValueError("晃动振幅元素必须为非负数")
        
        try: self.cycle = float(self.cycle)
        except: raise ValueError()
        if self.cycle<=0: raise ValueError("晃动振幅必须为正数")
        