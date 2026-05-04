"""
ctv-core 核心
通过 CTVField类 - 核心控制器
管理整个代码转视频的过程, 包括以下流程:
    0. 生成帧序列数据  SequenceGenerater
    1. 渲染原始图片    RendererManager
    2. 计算视角       CameraSystem
    3. 渲染生成帧集    FrameGenerater 
    4. 合成视频       在此类进行
-ω-
"""

from .config import *
from .data import *
from .render import *
from .utils import create_video, blur_glow #, ImageUtil
from .constants import DC, DEFAULT_BACKGROUND_COLOR, CURSOR_IMG_COLOR, CURSOR_LINE_COLOR

import os, sys
from math import ceil, floor, sin, cos, pi as PI
from collections.abc import Callable

from tqdm import tqdm

from pygments import lex 
from pygments.lexers import PythonLexer, CLexer, CppLexer, CSharpLexer, JavaLexer # TODO:是否自动识别语言?;是否能不再列举?
from pygments.token import Token

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QImage

import logging # TODO: 后期把这个放到init里, 让各包调用
logging.basicConfig(
    level=logging.DEBUG, # NOTE: 目前debug
    format='%(asctime)s - %(levelname)s : %(message)s',
    datefmt='%Y.%m.%d_%H:%M:%S'
)

__all__ = ["CTVField"]

class CTVField:
    """
    CTV场域类 - 核心控制器
        
    管理整个代码转视频的过程, 包括以下流程:
    0. 生成帧序列数据  SequenceGenerater
    1. 渲染原始图片    RendererManager
    2. 计算视角       CameraSystem
    3. 渲染生成帧集    FrameGenerater 
    4. 合成视频       在本类进行
    """

    def __init__(self, config:Config):
        self.config = config

        self.codeText = config.codeText
        self.configSG = config.configSG
        self.configCS = config.configCS

        self.language = config.language
        self.headText = config.headText

        self.mp4Name = config.mp4Name
        self.fps = config.fps
        self.resolution = config.resolution

        # 渲染参数
        self.renderer = config.renderer
        self.backgrond_img_path = os.path.join(config.workDir, f"background_img.png")

        # 输出参数
        self.outputDir = config.outputDir
        self.workDir   = config.workDir
        self.tempDir   = os.path.join(self.workDir, "temp")
        self.framesDir = os.path.join(self.workDir, "frames")
        
    def _prepareDir(self): # TODO: 检验是否生成了config文件
        """
        生成工作目录, 用于保存图片, 如果目录已存在则提示用户
        """
        if not os.path.exists(self.outputDir):
            os.makedirs(self.outputDir)
        logging.info(f"输出文件夹: {self.outputDir}")

        lastod = None

        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)
        else:
            logging.warning(f"缓存文件夹已存在: {self.tempDir}")
            od = input("是否继续运行? 回车继续运行.\n(:")
            if od.lower() not in ["", "y", "yes"]:
                logging.warning(f"已退出 {self.mp4Name} 的生成任务!!")
                sys.exit(1)
            lastod = True
            logging.info("持续运行...")
        logging.info(f"缓存文件夹: {self.tempDir}")
        
        if not os.path.exists(self.framesDir):
            os.makedirs(self.framesDir)
        elif not lastod:
            logging.warning(f"帧集文件夹已存在: {self.framesDir}")
            od = input("是否继续运行? 回车继续运行.\n(:")
            if od.lower() not in ["", "y", "yes"]:
                logging.warning(f"已退出 {self.mp4Name} 的生成任务!!")
                sys.exit(1)
            logging.info("持续运行...")
        logging.info(f"帧集文件夹: {self.framesDir}\n")

    def _creatVideo(self) -> bool:
        logging.info("开始合成视频...")
        return create_video(
                self.framesDir,
                os.path.join(self.outputDir, self.mp4Name),
                self.fps,
                0,
                self.length-1
            )     

    def main(self):
        logging.info(f"开始生成视频 {self.mp4Name}")
        self._prepareDir()
        self.config.save() # 会同时保存一张背景图片

        self.renderer.set_font_size(self.config.fontSizes[1])
        standard_line_height = self.renderer.render_line([("│", CURSOR_IMG_COLOR)]).height()
        self.renderer.set_font_size(self.config.fontSizes[0])
        cursor_img = self.renderer.render_line([("│", CURSOR_IMG_COLOR)])
        logic_line_height = cursor_img.height()

        initial_zoom_for_CS = logic_line_height / standard_line_height      

        sg = SequenceGenerater.creat_son(self.codeText, self.language, self.fps, self.headText, self.configSG.data) # ...
        rd = sg.generate()
        del sg
        self.length = len(rd)

        rm = RenderManager(logic_line_height, self.renderer, rd, self.tempDir, True)
        cd = rm.generate()
        p = os.path.join(self.outputDir, f"{os.path.splitext(self.mp4Name)[0]}_preview.png")
        rm.render_preview(p) # TODO: 这预览图保存得很不合时宜, 对之后的多模式不友好
        logging.info(f"预览图片已保存到: {p}")
        del rm, rd

        if self.configCS.mode == "D":
            cs = CameraSystem(self.resolution, self.fps, standard_line_height, logic_line_height, cd, initial_zoom_for_CS, **self.configCS.data) # ...
        else:
            raise ValueError("目前不支持非默认")

        fd = FrameDatum(cs.generate(), self.tempDir)
        del cs

        fg = FrameGenerater(self.resolution, self.backgrond_img_path, self.framesDir, fd, cursor_img, CURSOR_LINE_COLOR)
        fg.generate()
        del fg

        success = self._creatVideo()
        print()
        if success:
            logging.info("完成任务!")
        else:
            logging.warning("视频未生成成功, 退出程序")

# TODO: 考虑再为4个工作类拆分文件

#region 帧序列生成器
class SequenceGenerater:
    """
    帧序列生成器
    生成FrameData列表, 索引表示帧索引, 总长为视频总长
    """
    def __init__(self, codeText:str, language:str, fps:int, headText:str|None):
        self.codeText = codeText
        self.language = language
        self.fps = fps
        self.headText = headText

    def generate(self) -> RenderDatum:
        raise NotImplementedError

    @classmethod
    def creat_son(cls, codeText:str, language:str, fps:int, headText:str|None, kv:dict):
        mode = kv["mode"]
        del kv["mode"]
        if mode == "S":
            return ShowingModeSG(codeText, language, fps, headText, **kv)
        else:
            raise ValueError("模式非法")

class ShowingModeSG(SequenceGenerater):
    """展示模式(打字模式)"""
    def __init__(
            self,
            codeText:str,
            language:str,
            fps:int,
            headText:str|None,
            speed_function:Callable[[float], float],
            indentation_speed_index:int,
            time_limit:str,
            start_rest:float,
            end_rest:float
        ):
        super().__init__(codeText, language, fps, headText)
        self.speedFunc = speed_function
        self.indentSpeedIndex = indentation_speed_index
        self.limit = time_limit
        self.start_rest = start_rest
        self.end_rest =end_rest

        self.blink_duration = 1.0 # 光标闪烁周期时长(s) # NOTE: 此处硬编码
        self.blink_duration = self.blink_duration * self.fps / 2 # 转换成帧数
 
    def _get_pygments(self):
        """
        直接获取 Pygments token 的简化类型序列
            
        将Pygments的复杂token类型映射为简化的单字符类型
            
        Args:
            self: 主要是codeText,language
            
        Returns:
            list: 简化类型序列, 每个字符对应一个类型
        """
        table = { # 只列举一些部分主流语言
            "Python": PythonLexer,
            "C":      CLexer,
            "Cpp":    CppLexer,
            "CSharp": CSharpLexer,
            "Jave":   JavaLexer
        }
        if self.language not in table.keys(): raise ValueError(f"暂不支持的语言: {self.language}")

        tokens = list(lex(self.codeText, table[self.language]()))
        simple_types = []
            
        # Pygments 类型的映射 # 与ctv-constants对应
        STANDARD_TYPES = {
            Token.Text.Whitespace:        'W',
            Token.Text:                   'T',
            Token.Escape:                 'ESC',
            Token.Error:                  'ERR',
            Token.Other:                  'X',

            Token.Keyword.Constant:       'Kc',
            Token.Keyword.Declaration:    'Kd',
            Token.Keyword.Namespace:      'Kn',
            Token.Keyword.Pseudo:         'Kp',
            Token.Keyword.Reserved:       'Kr',
            Token.Keyword.Type:           'Kt',
            Token.Keyword:                'K',

            Token.Name.Attribute:         'Na',
            Token.Name.Builtin.Pseudo:    'Nbp',
            Token.Name.Builtin:           'Nb',
            Token.Name.Class:             'Nc',
            Token.Name.Constant:          'No',
            Token.Name.Decorator:         'Nd',
            Token.Name.Entity:            'Ni',
            Token.Name.Exception:         'Ne',
            Token.Name.Function.Magic:    'Nfm',
            Token.Name.Function:          'Nf',
            Token.Name.Property:          'Npy',
            Token.Name.Label:             'Nl',
            Token.Name.Namespace:         'Nn',
            Token.Name.Other:             'Nx',
            Token.Name.Tag:               'Nt',
            Token.Name.Variable.Class:    'Nvc',
            Token.Name.Variable.Global:   'Nvg',
            Token.Name.Variable.Instance: 'Nvi',
            Token.Name.Variable.Magic:    'Nvm',
            Token.Name.Variable:          'Nv',
            Token.Name:                   'N',

            Token.Literal.Date:           'Ld',
            Token.Literal:                'L',

            Token.String.Affix:           'Sa',
            Token.String.Backtick:        'Sb',
            Token.String.Char:            'Sc',
            Token.String.Delimiter:       'Sdl',
            Token.String.Doc:             'Sd',
            Token.String.Double:          'S2',
            Token.String.Escape:          'Se',
            Token.String.Heredoc:         'Sh',
            Token.String.Interpol:        'Si',
            Token.String.Other:           'Sx',
            Token.String.Regex:           'Sr',
            Token.String.Single:          'S1',
            Token.String.Symbol:          'Ss',
            Token.String:                 'S',

            Token.Number.Bin:             'Mb',
            Token.Number.Float:           'Mf',
            Token.Number.Hex:             'Mh',
            Token.Number.Integer.Long:    'Mil',
            Token.Number.Integer:         'Mi',
            Token.Number.Oct:             'Mo',
            Token.Number:                 'M',

            Token.Operator.Word:          'Ow',
            Token.Operator:               'O',

            Token.Punctuation.Marker:     'Pm',
            Token.Punctuation:            'P',

            Token.Comment.Hashbang:       'Ch',
            Token.Comment.Multiline:      'Cm',
            Token.Comment.Preproc:        'Cp',
            Token.Comment.PreprocFile:    'Cpf',
            Token.Comment.Single:         'C1',
            Token.Comment.Special:        'Cs',
            Token.Comment:                'C',            

            Token.Generic.Deleted:        'Gd',
            Token.Generic.Emph:           'Ge',
            Token.Generic.Error:          'Gr',
            Token.Generic.Heading:        'Gh',
            Token.Generic.Inserted:       'Gi',
            Token.Generic.Output:         'Go',
            Token.Generic.Prompt:         'Gp',
            Token.Generic.Strong:         'Gs',
            Token.Generic.Subheading:     'Gu',
            Token.Generic.EmphStrong:     'Ges',
            Token.Generic.Traceback:      'Gt',
            Token.Generic:                'G',

            Token:                        ' '
        }
        
        codeText = ""   
        for token_type, token_value in tokens:
            # 找到对应的简化类型 # 认为.是标点
            simple_type = 'U' if token_value == "." else STANDARD_TYPES[token_type]
            simple_types += [simple_type for _ in range(len(token_value))]
            codeText += token_value

        if codeText!=self.codeText:
            logging.warning(f"词元字符串{repr(codeText)}, 代码文本字符串{repr(self.codeText)}," \
                            "并不相等!!(如果只是略微不同, 可以忽略这个警告)")
            self.codeText = codeText

        # 处理括号层级
        ks = "([{"
        ke = ")]}"
        f = 0
        is_end = True

        for i, t in enumerate(simple_types):
            if t=="P":
                if self.codeText[i] in ks:
                    if is_end: is_end = False
                    else: f += 1
                    simple_types[i] = "P" + str(f % 5) # 只分5层 # 此处能用t赋值吗? 大概不能吧?
                elif self.codeText[i] in ke:
                    if not is_end: is_end = True
                    else: f -= 1
                    simple_types[i] = "P" + str(f % 5)
        """# 废弃
            elif t[0]=="S":
                if self.codeText[i] in "'\"" and (i==0 or simple_types[i-1][0]!="S" 
                        or i+1==len(simple_types)-1 or simple_types[i+1][0]!="S"):
                    simple_types[i] = "S " # 认为前后的字符串标识是特殊的字符串
        """
        if f!=0: # 这只是简单检验, 如果产生错误...
            logging.warning(f"提供的代码文本 {repr(self.codeText)} 存在括号层级错误!!")
            raise ValueError(f"代码文本参数 {repr(self.codeText)} 存在的括号层级错误 现在无法被忽略")

        self.types = simple_types
        self.length = len(simple_types)

    def _get_basis_for_split(self): # 划分依据
        pl = "([{'\"}])"
        ctl = list(filter(lambda t: t[0] in pl, zip(self.codeText, self.types)))

        result_l = [None for _ in range(len(ctl))]
        ptable = {")":"(", "]":"[", "}":"{"} # 右转左括号转换表
        record_d = {}
        for i, t in enumerate(ctl): # 这里问题超级多 # 但只要输入简单合理,就能正常处理
            if t[1] not in record_d.keys(): # 初始化
                record_d[t[1]] = {"(":[], "[":[], "{":[], "'":[], '"':[]}

            if t[0] in "([{":
                record_d[ t[1] ][ t[0] ].append(i)
            elif t[0] in ")]}":
                pk = ptable[t[0]]
                index = record_d[ t[1] ][pk][-1]
                result_l[index] = i
                result_l[i] = True # 说明有对应的左括号 # 但是对括号无实际用途
                record_d[ t[1] ][pk].pop(-1)


            elif t[0] in "'\"":
                if len(record_d[ t[1] ][ t[0] ])==0:
                    record_d[ t[1] ][ t[0] ].append(i)
                else:
                    index = record_d[ t[1] ][ t[0] ][-1]
                    result_l[index] = i
                    result_l[i] = True # 说明前面有对应的 # 这个对引号有实际作用
                    record_d[ t[1] ][ t[0] ].pop(-1)
            #else:不可能!!      

        self.records = result_l
    
    # address相关很不成熟, 只是基本完成任务, TODO: 考虑再写一类专门细化处理括号字符的处理
   
    def _address(self):
        self.extraEndList = []
        self.record_i = -1
        self.indentLevel = 0
        self.inMainContent = False
        self.lastData = [[]]
        self.lastType = None
        self.rawDatum = [RenderData(
                    data=[[]],
                    cursor=(0, -1), # -1 表示无(非 负索引) # TODO: 是否对renderer有问题? (如果不加行号)
                    SSGrecord = {"indent": 0, "char": None}
                )]
        line = 0 # 注意这个是索引行, 非行号(需要+1)
        lindex = 0
        self.recolastrd_index = -1
        for i, t in enumerate(self.types):
            if self.codeText[i] == "\n":
                line += 1
                lindex = -1
            nexttype = self.types[i+1] if i<len(self.types)-1 else None
            self._wrap_data(self.codeText[i], t, nexttype)
            self._address_one(line, lindex, self.codeText[i], t, i)
            lindex += 1

    @staticmethod
    def static_wrap_data(text:str, types:str) : # 默认认为两者长度一致 # 这个方法基本不用 因为是'静态'的而非动态
        index = 0
        length = len(types)
        data = [[]]
        while index<length:
            print(index)
            if text[index]=="\n":
                data.append([])
                index+=1
            else:
                nowt = types[index]
                for i in range(index, length-1):
                    if types[i+1]!=nowt:
                        break
                data[-1].append((text[index:i+1], nowt))
                index = i+1
        
        return data

    def _wrap_data(self, newchar:str, newtype:str, nexttype:str): # 动态包装
        if newchar=="\n":
            self.lastData.append([])
            self.lastType = None
        else:
            if self.lastType == 'Sa': # 表示f-string的'识别' (t-string同理) # 莫名联想到"草台班子"...
                self.lastData[-1][-1] = (self.lastData[-1][-1][0], 'Sa')

            if self.lastType != newtype:
                if newtype != nexttype:
                    self.lastData[-1].append((newchar, newtype if newtype!='Sa' else ' '))
                else:
                    temporary_type = ' ' if newtype[0] in "KN" else newtype # 只有字符串允许直接使用颜色
                    self.lastData[-1].append((newchar, temporary_type)) # 在最后一行 加入新元素
                self.lastType = newtype
            elif newtype != nexttype:
                self.lastData[-1][-1] = (self.lastData[-1][-1][0] + newchar, newtype)     
            else: # 在最后一行 的 最后一个元素 第一个元素(字符串)加入新字符
                self.lastData[-1][-1] = (self.lastData[-1][-1][0]+newchar, self.lastData[-1][-1][1])   

    def _address_one(self, line:int, lindex:int, tchar:str, kind:str, alli:int):
        self._address_one_for_indent(tchar)
        need_supplement = self._address_one_to_split(tchar, kind)
        
        if tchar == "\n": self._address_one_to_breakline()
        
        extra_data = [(t[1], t[2]) for t in self.extraEndList]
        SSGrecord = {"indent": self.indentLevel, "char": tchar}
        if need_supplement: # 删除多余字符'动画'
            extra_char = {"(":")", "[":"]", "{":"}", "'":"'", '"':'"'}[tchar]
            extra_data0 = [(extra_char, kind)] + extra_data
            data0 = [d[:] for d in self.lastData] # 深拷贝
            data0[-1] = data0[-1] + extra_data0
            self.rawDatum += [
                RenderData(
                    data=data0,
                    cursor=(line, lindex),
                    SSGrecord = SSGrecord
                ),
                RenderData(
                    data=data0,
                    cursor=(line, lindex+1),
                    SSGrecord = {"indent": self.indentLevel, "char": extra_char}
                )
            ]

        data = [d[:] for d in self.lastData] # 深拷贝
        data[-1] = data[-1] + extra_data
        self.rawDatum.append(
            RenderData(
                data=data,
                cursor=(line, lindex),
                SSGrecord = SSGrecord
            )
        )

    def _address_one_to_split(self, tchar:str, kind:str):
        self.record_i += 1 # 先认为需要加1
        signbool = False
        if tchar in "([{":
            if self.records[self.record_i] is not None:
                self.extraEndList= [(
                        self.records[self.record_i],
                        {"(":")", "[":"]", "{":"}"}[tchar], # 左转右
                        kind
                    )]  + self.extraEndList
            else: signbool = True
            
        elif tchar in ")]}":
            if self.extraEndList[0][0]!=self.record_i:
                raise Exception("_address_one:未考虑的情况, 疑是括号结构本就不合法")
            #else:...# 已经raise
            self.extraEndList.pop(0)

        elif tchar in "'\"":
            if self.records[self.record_i] is True: # 说明这是后引号
                if self.extraEndList[0][0]!=self.record_i:
                    raise Exception("_address_one:未考虑的情况, 疑是引号结构本就不合法")
                self.extraEndList.pop(0)
            elif self.records[self.record_i] is not None:
                self.extraEndList = [(
                    self.records[self.record_i],
                    tchar,
                    kind
                )] + self.extraEndList
            else: # 说明这是一个单独的引号
                signbool=True

        else: # 不是特殊字符 就 减回去
            self.record_i -= 1
            
        return signbool # 传递是否需要补充"删除 后括号的'动画'数据"

    def _address_one_for_indent(self, tchar:str):
        if self.inMainContent:
            pass
        elif tchar=="\t":
            self.indentLevel+=1
        else:
            self.inMainContent=True

    def _address_one_to_breakline(self):
        self.indentLevel = 0
        if len(self.extraEndList)>0: # TODO
            ...


    def _assign(self): # 按照时间分配原始数据
        if self.limit == "":
            self._assign_by_factor(1.0)
            index_len = len(self.datum)
            time_len = index_len / self.fps
            logging.info(f"默认帧数: {index_len}; 时长: {time_len} s")
            od = input("是否指定时长? (回车否定; 直接输入数值进行限制时长(s))\n(:")
            if od != "":
                try: t = float(od)
                except: logging.warning("非法输入, 视为不指定时长")
                else:
                    self._assign_by_limit(t)
                    self.limit = f"-{t}"
        
        elif self.limit[0] == "*":
            self._assign_by_factor(float(self.limit[1:]))
        elif self.limit[0] == "-":
            self._assign_by_limit(float(self.limit[1:]))
        else:
            raise ValueError("_assign:非法的时间限制")
        
        index_len = len(self.datum)
        time_len = index_len / self.fps
        logging.info(f"帧数: {index_len}; 时长: {time_len} s")
    
    def _assign_by_factor(self, factor:float):
        self.datum = []
        index = 0
        last_v = 0.0
        time1 = 1 / self.fps
        total_offset = -1.0
        indent_level = 0
        max_offset = len(self.rawDatum)-1 # 这是最大索引
        cursor_record = 0
        xi = -1 # 从-1开始
        while True:
            try: nowv = self.speedFunc(index * time1) * factor * \
                        (self.indentSpeedIndex ** indent_level)
            except:
                logging.warning("_assign_by_factor:疑是速度函数超出定义域")
                break
            
            dx = (last_v+nowv)/2 * time1
            nowx = total_offset + dx

            if nowx>=max_offset: break # 正常到达最大值
            
            last_xi, xi = xi, ceil(nowx)
            rdata = self.rawDatum[xi].copy()
            if last_xi==xi: rdata.data = ... # 表示未更新 继承上次的
            rdata.img_index = xi
            rdata.SSGrecord = None # 置空
            
            if abs(xi - last_xi) != 0:  # 适应倒退字符(没有用~)以及一次多个字符
                cursor_record = 0  # 实现打字时常亮
            else:
                if cursor_record <= -self.blink_duration/2 + 1: # 在原blink_duration s内转换一次 "<="防止不可能发生的事
                    cursor_record = int(self.blink_duration)  # 切换为熄(>0熄)
                else:
                    cursor_record -= 1  # 向下递减
            
            rdata.ifShowCursor = cursor_record <= 0 # 小于等于0亮
            self.datum.append(rdata)
            
            total_offset = nowx
            index += 1

        self._supplement_blank(0, self.start_rest, -1)
        self._supplement_blank(-1, self.end_rest, cursor_record, False)

    def _assign_by_limit(self, time_limit:float):
        index_limit = time_limit * self.fps
        factor0 = 1.0

        self._assign_by_factor(factor0)
        dif0 = index_limit - len(self.datum)  # 作差
        if dif0 == 0: return # 因为是整数,容易归零 # 可如果这里返回,那太凑巧了

        while True:  # 找异号点
            # dif > 0 总帧数小了 => factor大了
            # dif < 0 总帧数大了 => factor小了
            factor1 = factor0 * (0.5 if dif0 > 0 else 2.0)
            self._assign_by_factor(factor1)
            dif1 = index_limit - len(self.datum)
            
            if dif1 == 0: return # 如果这里返回, 那也是太凑巧了
            elif dif0 * dif1 > 0:  # 同号继续找
                dif0 = dif1
                factor0 = factor1
            else:  # dif0*dif1 < 0 # 异号开始二分
                factorb = min(factor0, factor1)
                factore = max(factor0, factor1)
                break

        while True: # 二分法找factor
            factor = (factorb + factore) / 2  # 二分
            self._assign_by_factor(factor)
            dif = index_limit - len(self.datum)
            
            if dif == 0: return # 因为是整数,容易归零(真的吗?)
            elif dif > 0: # 总帧数小了 => zoom大了 => 舍去end
                factore = factor
            else: # dif < 0 # 总帧数大了 => zoom小了 => 舍去begin
                factorb = factor  

    def _supplement_blank(self, index:int, time:float, cursor_record:int, is_running:bool=True):
        # 补充空白
        t = round(time * self.fps)
        od = self.datum[index].copy()
        od.data = ...
        od.is_running = is_running
        ds = []
        
        for _ in range(t):
            if cursor_record <= -self.blink_duration/2 + 1: # 在原blink_duration s内转换一次 "<="防止不可能发生的事
                cursor_record = int(self.blink_duration)  # 切换为熄(>0熄)
            else:
                cursor_record -= 1  # 向下递减
            d = od.copy()
            d.ifShowCursor = cursor_record <= 0 # 小于等于0亮
            ds.append(d)
        
        index = index if index>=0 else len(self.datum) + index
        self.datum = self.datum[:index+1] + ds + self.datum[index+1:]

    def generate(self) -> RenderDatum: # TODO: 关于返回配置修改(限制因子等)
        self._get_pygments() # 划分词元
        self._get_basis_for_split() # 获取划分括号结构的依赖
        self._address() # 预处理, 生成原始数据集
        self._assign() # 按照时间分配原始数据

        return RenderDatum(self.datum, self.headText, True, True)

class ExecutionModeSG(SequenceGenerater):... # 执行模式 # TODO: 后续做

#endregion

class RenderManager:
    """管理渲染器, 生成原始图片"""
    def __init__(self, logical_lh:int, renderer:Renderer, rdatum:RenderDatum, tempDir:str, ifCache:bool=True):
        self.logical_lh = logical_lh
        self.renderer = renderer

        self.rdatum = rdatum
        self._render_one = self._render_one_with_cache if ifCache else self._render_one_without_cache
        self.tempDir = tempDir

        self.thisImg = None
        self.thisImg_h = 0
        self.thisImg_totalline = 0
        self.thisImg_w = 0

        self.cxys = []
    
    def add_new_cx(self, v: int) -> None: # 均为逻辑值, 未处理为显示值
        self.cxys.append((v, self.rdatum.cursor[0] * self.logical_lh))

    def add_old_cx(self) -> None:
        self.cxys.append((self.cxys[-1][0],  self.rdatum.cursor[0] * self.logical_lh))

    @property
    def cxy(self): return self.cxys[-1]
    
    def _add_line_img(self, img:QImage) -> None:
        if self.thisImg is None:
            self.thisImg = img
            self.thisImg_h = img.height()
            self.thisImg_w = img.width()
        else:
            total_height = self.thisImg_h + img.height()
            max_width = max(self.thisImg.width(), img.width())
            
            result = QImage(max_width, total_height, QImage.Format_ARGB32)
            result.fill(Qt.transparent)
                
            # 创建QPainter进行绘制
            painter = QPainter(result)
            # 依次绘制每个图像(左对齐)
            painter.drawImage(0, 0, self.thisImg)
            painter.drawImage(0, self.thisImg_h, img)
            painter.end()

            self.thisImg = result
            self.thisImg_h = total_height
            self.thisImg_w = max_width

        self.thisImg_totalline +=1

    def _edit_line_img(self, line:int, img:QImage) -> None:
        if img.width() > self.thisImg.width(): # 扩大画幅
            thisImg = QImage(img.width(), self.thisImg.height(), QImage.Format_ARGB32)
            painter = QPainter(thisImg)
            painter.drawImage(0, 0, self.thisImg)
            painter.setCompositionMode(QPainter.CompositionMode_Source) # 完全替换, 画幅足够
            painter.drawImage(0, self.logical_lh*line, img)
            painter.end()
            self.thisImg = thisImg
            self.thisImg_w = img.width()
        else:
            painter = QPainter(self.thisImg)
            painter.setCompositionMode(QPainter.CompositionMode_Clear) # 清空而非替换, 防止部分超出范围的区域未被清除
            painter.fillRect(0, self.logical_lh*line, self.thisImg.width(), self.logical_lh, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawImage(0, self.logical_lh*line, img)
            painter.end()

    def _render_adjust(self, linedata:list) -> list:
        for i, d in enumerate(linedata):
            linedata[i] = (d[0].replace("\t"," "*4), DC[d[1]])
        # 不使用加法的原因是数据不都是元组(难道列表可以加元组?) # 已经忘了为什么这么注释了...
        return linedata

    def _render_line(self, linedata:list) -> QImage:
        linedata = self._render_adjust(linedata)
        return self.renderer.render_line(linedata)

    def _render_line_with_char_rect(self, linedata:list, findci:int) -> tuple[QImage, int]:
        s = "".join(c[0] for c in linedata)
        tabn = s.count("\t", 0, findci) # 一个字符"\t" 转为4个" ", 净增加 3*tabn
        linedata = self._render_adjust(linedata)
        return self.renderer.render_line_with_char_rect(linedata, findci+3*tabn)

    def _render_one_without_cache(self) -> bool:
        if self.rdatum.isNotUpData:
            if self.rdatum.isDifferentCursor:
                self.line = self.rdatum.cursor[0]
                _, lcx = self._render_line_with_char_rect(self.rdatum.thisLine, self.rdatum.cursor[1])
                self.add_new_cx(lcx)
            else:
                self.add_old_cx()
            return False # 未更新
        
        for self.rdatum.line, ld in enumerate(self.rdatum.data):
            if self.rdatum.cursor[0] == self.rdatum.line:
                img, lcx = self._render_line_with_char_rect(ld, self.rdatum.cursor[1])
                self.add_new_cx(lcx)
                self._add_line_img(img)
            else:
                self._add_line_img(self._render_line(ld))

        name = f"{self.rdatum.img_index:05d}.png"
        self.thisImg.save(os.path.join(self.tempDir, name))

        self.thisImg = None # 置空
        return True

    def _render_one_with_cache(self) -> bool: # RM 和 RD 配合不太好, 以一种冗余方式完成任务的(竟然生成无误?)
        _ = self.rdatum.img_index
        if self.rdatum.isNotUpData:
            if self.rdatum.isDifferentCursor:
                self.line = self.rdatum.cursor[0]
                _, lcx = self._render_line_with_char_rect(self.rdatum.thisLine, self.rdatum.cursor[1])
                self.add_new_cx(lcx)
            else:
                self.add_old_cx()
            return False # 未更新
        
        if_updata = False
        for self.rdatum.line, ld in enumerate(self.rdatum.data[:self.thisImg_totalline]):
            if self.rdatum.isDifferentLine:
                if self.rdatum.cursor[0] == self.rdatum.line:
                    img, lcx = self._render_line_with_char_rect(ld, self.rdatum.cursor[1])
                    self.add_new_cx(lcx)
                    self._edit_line_img(self.rdatum.line, img)
                else:
                    self._edit_line_img(self.rdatum.line, self._render_line(ld))
                if_updata = True
            elif self.rdatum.cursor[0] == self.rdatum.line:
                self.add_old_cx()

        for self.rdatum.line, ld in enumerate(self.rdatum.data[self.thisImg_totalline:], self.thisImg_totalline):
            if self.rdatum.cursor[0] == self.rdatum.line:
                img, lcx = self._render_line_with_char_rect(ld, self.rdatum.cursor[1])
                self.add_new_cx(lcx)
                self._add_line_img(img)
                if_updata = True
            else:
                self._add_line_img(self._render_line(ld))
                if_updata = True

        if if_updata:
            name = f"{self.rdatum.img_index}.png"
            self.thisImg.save(os.path.join(self.tempDir, name))

        return if_updata # 缓存不置空thisImg

    def render_preview(self, path:str) -> QImage:
        # 只在with_cache用 有些临时性质
        for d in self.rdatum[::-1]:
            if d.data is not ...:
                break
        d.data[-1] = [((f"{len(d.data)-1:4d}│"), "G")] + d.data[-1][1:]
        self._edit_line_img(len(d.data)-1, self._render_line(d.data[-1]))
        # 保存预览图片
        result = QImage(self.thisImg.width()+100, self.thisImg.height()+100, QImage.Format_ARGB32)
        result.fill(QColor(*DEFAULT_BACKGROUND_COLOR))
        painter = QPainter(result)
        painter.drawImage(50, 50, self.thisImg)
        painter.end()

        result.save(path) # TODO: 如果没成功呢(一般来说不会)

    def _render(self) -> list:
        cdatum = []
        for _ in tqdm(range(self.rdatum.list_length)):
            if_updata = self._render_one() # 返回值到底有没有用呢

            cdatum.append(
                    CameraData(
                        self.rdatum.img_index,
                        self.thisImg_totalline,
                        self.cxy,
                        self.rdatum.ifShowCursor,
                        ... if self.rdatum.is_running else self.thisImg_w 
                    )
                )

            self.rdatum.nextData()
        
        return cdatum

    def generate(self) -> CameraDatum:
        logging.info("开始渲染原始图片...")
        cd = self._render()
        logging.info("渲染原始图片完成!")
        if len(self.cxys)!=self.rdatum.list_length:
            from pprint import pprint
            logging.warning(f"光标异常! 长度 cxys {len(self.cxys)} != rdatum {self.rdatum.list_length}")
            pprint(self.cxys)
            raise # 这目前来说是多虑
        return CameraDatum(cd)

class CameraSystem: # TODO: 是否拆分成多个子类 以模式化
    """管理相机系统, 生成视频帧数据"""
    def __init__(self,
                resolution:tuple[int,int],
                fps:int,             
                standard_line_height:int,
                logic_line_height:int,
                cdatum:CameraDatum,
                initial_zoom:float=5.0,
                spring_k:float = 1.40,
                damping:float = 0.85,
                shaking_ks:tuple[float,float] = (1.0, 1.6),
                cycle:float = 5.0,
                mode:str = "D" # TODO:亟待区分为多个模式,进而写成多个类
        ):
        self.cdatum = cdatum
        self.fps = fps
        self.t0 = 1/self.fps  # 一帧时长(秒)
        
        self.spring_k = spring_k
        self.damping = damping
        self.shaking_ks = shaking_ks # 晃动的幅度
        self.cycle = cycle # 晃动的周期

        self._wh = resolution
        self._w:int; self._h:int       # 分辨率横纵(属性)
        self._lcwh = (self._w / initial_zoom, self._h / initial_zoom) # 坐标系中的逻辑视野长宽(属性)
        self._lcw:float; self._lch:float # _lcwh (属性)
        
        self._slh = standard_line_height # 显示坐标系中最终的固定行高
        self._llh = logic_line_height # 原图片的逻辑行高, 在逻辑坐标系中固定
        self._vlh:float               # 视野中的行高(属性)

        self.initial_zoom = initial_zoom # 原始缩放值 = 显示 / 标准
        self._zoom = initial_zoom    # 缩放值 = 显示 / 标准; zoom = view / standard
        self.zoom:float              # 包装缩放值(属性)

        self.cam = (0.0, 0.0)        # 相机坐标(此初始化数值无用)
        self.camx:float              # 相机横坐标(属性)
        self.camy:float              # 相机纵坐标(属性)
        self.camm:tuple[float,float] # 相机中心坐标(属性)
        self.camm = self.cdatum.cxy  # 通过中心坐标进行初始化

        self.camv = (0.0, 0.0)       # 相机移动速度
        self.camvx:float             # 相机横向移动速度(属性)
        self.camvy:float             # 相机纵向移动速度(属性)
    
    #region CS属性
    @property
    def _w(self)->int:      return self._wh[0]
    @property
    def _h(self)->int:      return self._wh[1]
    @property # 视界宽高 = 显示分辨率 / rzoom
    def _lcw(self)->int:     return self._lcwh[0]
    @property
    def _lch(self)->int:     return self._lcwh[1]
    
    # 无v前缀均为逻辑值, v表示视觉显示值
    @property
    def camx(self)->float:  return self.cam[0]
    @property
    def camy(self):         return self.cam[1]
    @camx.setter
    def camx(self,v:float): self.cam = (v, self.cam[1])
    @camy.setter
    def camy(self,v:float): self.cam = (self.cam[0], v)
    @property
    def camm(self)->tuple[float,float]:
        return (self.camx + self._lcw / 2, self.camy + self._lch / 2)
    @camm.setter
    def camm(self,v:tuple[float,float]):
        self.camx, self.camy = v[0]-self._lcw/2, v[1]-self._lch/2
    @property
    def camvx(self)->float:  return self.camv[0]
    @property
    def camvy(self)->float:  return self.camv[1]
    @camvx.setter
    def camvx(self,v:float): self.camv = (v, self.camv[1])
    @camvy.setter
    def camvy(self,v:float): self.camv = (self.camv[0], v)

    @property # zoom = view / standard
    def zoom(self)->float:  return self._zoom
    @zoom.setter
    def zoom(self, v: float):
        camm = self.camm
        self._zoom = v
        self._lcwh = (self._w / self.rzoom, self._h / self.rzoom)
        self.camm = camm  # 保持中心不变（camm setter 会使用新的 _lcw/_lch）
    @property # rzoom = logic / view
    def rzoom(self)->float: return self._zoom / self.initial_zoom
    @property
    def _vlh(self)->float: return self._llh * self.rzoom
    
    @property # 这些光标坐标值是在逻辑坐标系
    def cx(self) -> float: return self.cdatum.cx # 暂认为无宽(或可以忽略) (返回实际为int)
    @property
    def cy(self) -> float: return self.cdatum.cy + self._llh/2 # 锁定中心
    @property
    def cxy(self) -> tuple[float, float]: return (self.cx, self.cy)
    
    @property
    def midpos(self) -> tuple[float, float]: # 不能在self.cdatum.is_running为假时调用
        return (self.cdatum.img_w / 2, self.cdatum.img_h_num * self._llh / 2)

    @property
    def vpos(self) -> tuple[int, int]:
        """代码图片在显示画面中的左上角坐标"""
        return (
            round(-self.camx * self.rzoom),
            round(-self.camy * self.rzoom)
        )
    @property
    def vcpos(self) -> tuple[int, int]:
        """光标中心在显示画面中的坐标"""
        return (
            round((self.cdatum.cx - self.camx) * self.rzoom),
            round((self.cdatum.cy - self.camy) * self.rzoom)
        )

    @property
    def now_time(self) -> float: return self.cdatum.index / self.fps

    #endregion

    def _calculate(self) -> list[FrameData]:
        fd = []
        for _ in range(len(self.cdatum)):
            fd.append(self._calculate_one())

            self.cdatum.nextData()
        return fd

    def _calculate_one(self) -> FrameData:
        self._calculate_pos(self.cxy if self.cdatum.is_running else self.midpos)
        self._calculate_zoom()

        return self.cdatum.creatFD(self.vpos, self.vcpos, round(self._vlh), self.zoom)

    def _calculate_pos(self, aim:tuple[float, float]):
        """
        计算相机位置(阻尼版本)
        
        使用弹簧-阻尼模型计算相机平滑移动
        位置差产生加速度, 同时给速度添加阻尼项减少振荡
        """
        aimx, aimy = aim
        #self.camm = (aimx, aimy)
        #return

        x, y = self.camm  # 目前相机中心坐标
        dx, dy = aimx - x, aimy - y  # 位置差
        
        # 弹簧系数和阻尼系数(可调整)
        # springk 弹簧强度
        # damping 阻尼系数, 0-1之间, 越大阻尼越强
        # 弹簧力 = -k * dx (指向目标)
        # 阻尼力 = -damping * v (与速度方向相反)
        
        angle = 2 * PI / self.cycle * self.now_time
        svx, cvy = self.shaking_ks[0] * sin(angle), self.shaking_ks[1] * cos(angle)

        # X轴
        ax = self.spring_k * dx - self.damping * (self.camvx + svx)
        self.camvx = self.camvx + ax * self.t0
        cammx = x + self.t0 * (self.camvx + svx) / 2
        
        # Y轴
        ay = self.spring_k * dy - self.damping * (self.camvy + cvy)
        self.camvy = self.camvy + ay * self.t0
        cammy = y + self.t0 * (self.camvy + cvy) / 2
        
        self.camm = (cammx, cammy)

    def _calculate_zoom(self):
        """
        计算缩放因子 不允许放大
        
        根据相机位置和内容边界自动调整缩放级别
        确保所有内容都在视野范围内
        """
        if self.zoom <= 1: return

        # 赋予camy正值向负强趋势; 光标要在视野内的趋势
        dy = max(self.camy + self._lch * 0.05, self.cy - self.camy - self._lch, 0)  # 计算趋势
        # 赋予camy正值向负弱趋势; 光标要在视野内的趋势
        dx = max((self.camx - self._lcw * 0.1)*0.5, self.cx - self.camx - self._lcw, 0)
        
        # zoom只缩小不扩大(所以要与0取最大值), 缩小至1.0为止
        h = dy * 2 + self._lch
        w = dx * 2 + self._lcw
        hr = self._lch / h
        wr = self._lcw / w
        rate = min(hr, wr)  # zoom需乘的倍数
        rrate = max(1 - 0.5*(1-rate)**2, 0.99) # 修正比率, 减小波动
        # 0<x=rata<=1
        # f(x) = 1-0.5(1-x)**n, n>1(n=0退化为一次函数)
        # f`(x)= 0.5n(1-x)**n, n 同上
        # f(x)满足以下要求: f(0)=0.5;f(1)=1; f`(1)=0;f`(0)随n增大而增大;f`(0)在[0,1]上单减
        zoom = self.zoom * rrate
        if zoom <= 1:  # 说明达到极限
            #print("zoom达到极限")
            self.zoom = 1.0
        else: self.zoom = zoom

    def generate(self) -> list[FrameData]:
        fd = self._calculate()
        return fd

# 使用QImage直接处理
class FrameGenerater: # TODO: 考虑更换图像处理库, 毕竟QT本质是GUI, 可能存在冗余, 速度可能有限制
    """根据视频帧数据合成帧图片"""
    def __init__(self,
                resolution:tuple[int,int],
                back_ground_path:str,
                framesDir:str,
                fdatum:FrameDatum,
                cursor_img:QImage,
                curlc:tuple[int, int, int, int]
            ):
        self.wh = resolution
        self.bgimg = QImage(back_ground_path)
        self.framesDir = framesDir
        self.fdatum = fdatum
        self.last_zoom = self.fdatum.this_zoom
        
        self.__cursimg = cursor_img
        self._cursimg = self.__cursimg.scaledToHeight(self.fdatum.this_vlh)
        
        self.curlc = QColor(*curlc)
        self._curlimg = QImage(self.bgimg.width(), self.fdatum.this_vlh, QImage.Format_ARGB32)
        self._curlimg.fill(self.curlc)

    @property
    def cursimg(self) -> QImage:
        if self.last_zoom!=self.fdatum.this_zoom:
            self._cursimg = self.__cursimg.scaledToHeight(self.fdatum.this_vlh)
        return self._cursimg

    @property
    def curlimg(self) -> QImage:
        if self.last_zoom!=self.fdatum.this_zoom:
            self._curlimg = QImage(self.bgimg.width(), self.fdatum.this_vlh, QImage.Format_ARGB32)
            self._curlimg.fill(self.curlc)
        return self._curlimg

    def _render(self):
        
        for i in tqdm(range(len(self.fdatum))):
            img = self._render_one()
            name = os.path.join(self.framesDir, f"{i}.png")
            img.save(name)

            self.fdatum.nextData()

    def _render_one(self) -> QImage:
        material_img = self.fdatum.this_img.scaledToHeight(self.fdatum.this_vlh * self.fdatum.this_img_h)
        img = QImage(self.bgimg)
        fg = QImage(*self.wh, QImage.Format_ARGB32)

        painter = QPainter(fg)
        painter.drawImage(*self.fdatum.this_pos, material_img)
        if self.fdatum.this_ifShowCursor:
            painter.drawImage(round(self.fdatum.this_cx-self.cursimg.width()/2), self.fdatum.this_cy, self.cursimg)
        painter.end()

        # fg发光特性 # NOTE: 此处硬编码

        fg = blur_glow(fg)

        painter = QPainter(img)
        painter.drawImage(0, self.fdatum.this_cy, self.curlimg) # 显示光标所在行
        painter.drawImage(0, 0, fg) # 前景 代码图片层
        painter.end()

        return img # 完整的帧图片

    def generate(self):
        logging.info("开始生成帧集...")
        self._render()

# TODO: 为RM和FG考虑多进程式生成图片
# TODO: 为SG和CS加进度条(目前速度快, 暂不加)
