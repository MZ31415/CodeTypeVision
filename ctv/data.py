"""
ctv-data 数据
给core的各种数据类, 方便传递与使用
-ω-
"""
from .constants import KEYS_TABLE

import os
from PyQt5.QtGui import QImage # 主要作变量类型标识
from types import EllipsisType
#from .utils import ImageUtil
from dataclasses import dataclass, asdict

__all__ = [ ### 呃呃呃, 我把单复数搞混了... 不好改啊啊 # TODO: 改名
    "RenderData", "RenderDatum", # 这样不换行写挺好
    "CameraData", "CameraDatum",
    "FrameData",  "FrameDatum"
]

# TODO: 考虑写data和datum父类来统一一下, 并优化变量名称等等
# TODO: RD和RM配合得不好, 一些逻辑不太对, 后续需要在写父类时重写
@dataclass
class RenderData:
    data: list[list[tuple[str, tuple]]] | EllipsisType # 数据 ...表示继承上次
    cursor: tuple[int, int] # 光标 行索引,元素索引
    ifShowCursor: bool = None # 是否显示光标
    img_index: int = None # 图片序列
    is_running: bool = True # 是否正在打字(关于end_rest\相机计算pos)

    SSGrecord:dict = None # (这个只是给SSG类记录用的, 对其他无用)

    def __getitem__(self, index: int | tuple[int, int]): # 索引器不处理异常, 错误必须报错
        return self.data[index] if isinstance(index, int) else self.data[index[0]][index[1]]

    def __str__(self):
        return str(asdict(self))
    
    def copy(self): # 深拷贝自己
        return RenderData(
            data=self.data,
            cursor=self.cursor,
            ifShowCursor=self.ifShowCursor,
            img_index=self.img_index,
            is_running=self.is_running,
            SSGrecord=self.SSGrecord
        )

    def adjust_data_keys(self):
        if self.data is not ...:
            self.data = [
                [
                    (td[0], KEYS_TABLE[td[1]]) for td in ld
                ] for ld in self.data 
            ]

    def add_line_head(self): # 后于adjust_data_keys
        self.cursor = (self.cursor[0], self.cursor[1]+5) # 格式化时加了5个字符

        if self.data is ...: return # 忽略...
        for i in range(len(self.data)):
            c = "w" if i==self.cursor[0] else "G"
            self.data[i] = [((f"{i+1:4d}│"), c)] + self.data[i]

    def add_head_text(self, text:str): # 后于add_line_head
        if self.data is not ...:
            self.data = [[(text, "G")]] + self.data
        self.cursor = (self.cursor[0]+1, self.cursor[1]) # 加了一行

class RenderDatum:
    def __init__(self, datum:list[RenderData], headText:str|None, ifAdjust:bool=False, ifLinesign:bool=False):
        datum = self._adjust_datum_keys(datum) if ifAdjust else datum
        datum = self._add_datum_linesign(datum) if ifLinesign else datum
        datum = self._add_head_text(datum, headText) if headText else datum
        self.datum = datum
        self.list_length = len(self.datum)
        self.list_index = 0
        self.line = 0
        self._data = None
        self._last_data = None
    
    @staticmethod
    def _adjust_datum_keys(datum:list[RenderData]) -> list[RenderData]: # 将原始词元转换为颜色键
        for d in datum:
            d.adjust_data_keys() # 因为是引用类型, 改变内部作用于datum
        return datum
    @staticmethod
    def _add_datum_linesign(datum:list[RenderData]) -> list[RenderData]: # 在原始行前添加行号
        for d in datum:
            d.add_line_head() # 因为是引用类型, 改变内部作用于datum
        return datum
    @staticmethod
    def _add_head_text(datum:list[RenderData], headText:str|None) -> list[RenderData]: # 添加头文件
        for d in datum:
            d.add_head_text(headText) # 因为是引用类型, 改变内部作用于datum
        return datum

    def __getitem__(self, index:int):
        return self.datum[index]

    def __len__(self) -> int: return len(self.datum)  
    
    def _cheak(self) -> None:
        if self[self.list_index].data is not ...:
            self._last_data, self._data = self._data, self[self.list_index].data

    @property
    def data(self) -> list[list[tuple[str, tuple]]]:
        self._cheak()
        return self._data

    @property
    def is_running(self): return self[self.list_index].is_running

    @property
    def isNotUpData(self) -> bool: return self[self.list_index].data is ...

    @property
    def isDifferentData(self) -> bool:
        if self.list_index == 0: return True
        if self._last_data is None: return True
        if len(self._last_data) > self.line:
            return self._last_data[self.line]!=self.thisLine
        else: return True

    @property
    def isDifferentLine(self) -> bool:
        if self.list_index==0: return True
        if len(self._last_data)<=self.line: return True
        return self._last_data[self.line]!=self._data[self.line]

    @property
    def cursor(self) -> tuple[int, int]:
        return self[self.list_index].cursor

    @property
    def ifShowCursor(self) -> bool:
        return self[self.list_index].ifShowCursor

    @property
    def isDifferentCursor(self) -> bool:
        if self.list_index==0: return True
        return self[self.list_index].cursor != self.cursor

    @property
    def img_index(self) -> int:
        return self[self.list_index].img_index
    
    def nextData(self) -> None:
        self.list_index+=1
        self.line = 0

    @property
    def thisLine(self):
        try:
            return self.data[self.line]
        except IndexError:
            return None

@dataclass
class CameraData:
    img_index: int
    img_h_num: int
    cursor_pos: tuple[int, int]
    ifShowCursor: bool
    img_w: EllipsisType | int # ...表示不需要知道而非继承上次, 与is_running相关

class CameraDatum:
    def __init__(self, datum:list[CameraData]):
        self.datum = datum
        self.index = 0
        self._img = None
    
    @property
    def data(self):
        return self.datum[self.index]

    @property
    def cx(self): return self.data.cursor_pos[0]

    @property
    def cy(self): return self.data.cursor_pos[1]

    @property
    def cxy(self): return self.data.cursor_pos

    @property
    def is_running(self): return self.data.img_w is ...

    @property
    def img_h_num(self): return self.data.img_h_num

    @property
    def img_w(self): return self.data.img_w

    def creatFD(self, pos:tuple[int, int], cpos:tuple[int, int], vlh:int, zoom:float) -> "FrameData":
        return FrameData(self.data.img_index, self.data.ifShowCursor, self.data.img_h_num, pos, cpos, vlh, zoom)

    def nextData(self) -> None: self.index += 1 

    def __len__(self) -> int: return len(self.datum)

@dataclass
class FrameData:
    img_index: int
    ifShowCursor: bool
    img_h: int
    pos: tuple[int, int]
    cur_pos: tuple[int, int]
    vlh: int
    zoom: float

class FrameDatum:
    def __init__(self, datum:list[FrameData], tempDir:str):
        self.datum = datum
        self.tempDir = tempDir
        self.index = 0
        self._last_img_index = 0
        #self._img = ImageUtil.imread_rgb(os.path.join(self.tempDir, f"{self.datum[0].img_index}.png"))
        self._img = QImage(os.path.join(self.tempDir, f"{self.datum[0].img_index}.png"))

    @property
    def this_data(self) -> FrameData: return self.datum[self.index]

    @property
    def this_img(self) -> QImage:
        if self._last_img_index!=self.datum[self.index].img_index:
            #self._img = ImageUtil.imread_rgb(os.path.join(self.tempDir, f"{self.datum[self.index].img_index}.png"))
            self._img = QImage(os.path.join(self.tempDir, f"{self.datum[self.index].img_index}.png"))
        return self._img

    @property
    def this_img_h(self) -> int: return self.datum[self.index].img_h
    @property
    def this_vlh(self) -> int:   return self.datum[self.index].vlh

    @property
    def this_pos(self) -> tuple[int,int]: return self.datum[self.index].pos

    @property
    def this_cx(self) -> int: return self.datum[self.index].cur_pos[0]

    @property
    def this_cy(self) -> int: return self.datum[self.index].cur_pos[1]

    @property
    def this_ifShowCursor(self)->bool: return self.datum[self.index].ifShowCursor

    @property
    def this_zoom(self) -> float: return self.datum[self.index].zoom

    def nextData(self) -> None: self.index += 1

    def __len__(self) -> int: return len(self.datum)
