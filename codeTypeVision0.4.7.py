#!/usr/bin/env python
#-*- coding:UTF-8 -*-
"""
codeTypeVision v0.4.7.2026.02.11

将代码文本转换为动态视频, 展示代码输入过程, 包含语法高亮和流畅的相机移动效果.
支持自定义速度函数, 时间限制, 分辨率等参数.

这是实现异步的版本

-ω-
"""

#region 引用库
"""以下需要pip
pip install PyQt5>=5.15.0 pygments>=2.10.0 tqdm>=4.64.0
"""
import os
import subprocess
import sys

from typing import List, Tuple, Union

from time import time, sleep
from datetime import datetime
from pprint import pprint
from math import ceil, floor

from pygments import lex 
from pygments.lexers import PythonLexer, CLexer, CppLexer, CSharpLexer, JavaLexer
from pygments.token import Token

#from PIL import Image, ImageDraw, ImageFont # pillow 枕头输给了 PyQt5

from PyQt5.QtCore import Qt #, QByteArray, QBuffer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QImage #, QGuiApplication, QPixmap

import asyncio
#import aiofiles # 未使用
from tqdm.asyncio import tqdm

try: from winsound import MessageBeep # 如果非win系统需要删除相关代码
except: print("winsound未导入, 无法使用提示音提示!!")

#import numpy as np # 未使用
#from scipy import ndimage # 未使用
#from numba import jit # 未做相关处理
#endregion

#region 全局变量声明
MAX_CONCURRENT = 50 # 最大异步任务并发量; **可以进行修改**

THIS_PATH = os.path.dirname(__file__)+"\\" # 这是本文件父文件夹路径
nowtime = lambda: datetime.now().strftime("[%Y.%m.%d_%H:%M:%S]") # 简单输出时间
app = QApplication([])  # 必须的Qt应用程序实例
#endregion

#region 类&函数-
class CodeLineRenderer:
	"""
	单行代码文本渲染器
		
	支持多色文本渲染, 中英文字体混合, 连体字效果
	使用Qt进行高质量的文字渲染, 支持抗锯齿和透明背景
	"""
		
	def __init__(self, 
				default_font_size: int = 20,
				font0: Union[QFont, str] = "Fira Code Retina",  # 默认使用FiraCode稍粗体
				font1: Union[QFont, str] = "Microsoft YaHei UI",# 默认使用微软雅黑
				enable_ligatures: bool = True
			):
		"""
		初始化单行多色多字体渲染器
		
		Args:
			default_font_size: 默认字体大小(像素)
			font0: 英文字体(等宽字体,用于代码渲染)
			font1: 中文字体(用于CJK字符渲染)
			enable_ligatures: 是否启用连体字效果(仅对英文字体有效)
		"""
		self._ensure_qapp()
		
		# 初始化字体
		self.font0 = font0 if isinstance(font0, QFont) else self.creat_QFont(font0, default_font_size)
		self.font1 = font1 if isinstance(font1, QFont) else self.creat_QFont(font1, default_font_size)
		self.enable_ligatures = enable_ligatures
		
		# 设置连体字(直接通过字体特性)
		if enable_ligatures:
			self._enable_font_ligatures(self.font0)
		
		# 缓存系统以提高性能
		self._metrics_cache = {}
		self._char_width_cache = {}
		self._update_metrics_cache()
		self._precache_char_widths()
		
	def _ensure_qapp(self): # 因为外部已经初始化, 故这个函数用处不大
		"""
		确保QApplication实例存在
		
		Qt渲染需要全局的QApplication实例, 这个函数确保其存在
		"""
		if QApplication.instance() is None:
			self.app = QApplication([])  # 不知道为什么没有用(如果不声明全局变量)
		# QGuiApplication::font(): no QGuiApplication instance and no application font set.
	
	def _enable_font_ligatures(self, font: QFont):
		"""
		启用字体连体特性
		
		尝试通过Qt的字体设置启用OpenType连体字特性
		注意:PyQt5对OpenType特性支持有限,这里使用通用方法
		
		Args:
			font: 要启用连体字的字体对象
		"""
		# PyQt5 中,OpenType 特性通过字体字符串设置
		# 设置字体特性字符串
		font.setStyleStrategy(QFont.PreferAntialias)
		font.setHintingPreference(QFont.PreferNoHinting)
		
		# 尝试设置OpenType特性
		# 注意:PyQt5的QFont对OpenType特性支持有限
		# 这里设置通用属性以启用连体
		font.setStyleHint(QFont.Monospace)
		font.setFixedPitch(True)
		
		# 通过设置FontWeight让字体引擎知道我们想要更多特性
		font.setWeight(QFont.Medium)  # 中等粗细有助于启用更多特性
			
	def _calculate_layout(self, data: List[Tuple[str, Tuple[int, int, int, int]]]) -> Tuple[int, int, List[dict]]:
		"""
		计算文本布局信息(简化版,让字体引擎处理连体)
		
		将多色文本数据转换为字符布局信息,包括位置,字体,颜色等
		
		Args:
			data: 文本数据列表,每个元素为(文本,RGBA颜色)
			
		Returns:
			Tuple: (总宽度, 行高, 字符布局列表)
		"""
		char_layouts = []
		current_x = 0
		
		metrics0 = self._metrics_cache['font0']
		metrics1 = self._metrics_cache['font1']
		line_height = max(metrics0.height(), metrics1.height())
		baseline = metrics0.ascent()
		
		for text, color in data:
			if not text:
				continue
			
			# 英文或混合:整个文本段一起处理,让字体引擎处理连体
			char_layouts.append({
				'text': text,
				'font': self.font0,
				'color': QColor(*color),
				'x': current_x,
				'ascent': metrics0.ascent(),
				'baseline': baseline
			})
			# 计算整个文本段的宽度(字体引擎会自动考虑连体)
			current_x += metrics0.horizontalAdvance(text)
		
		return current_x, line_height, char_layouts
		
	def render_line(self,
				   data: List[Tuple[str, Tuple[int, int, int, int]]],
				   background_color: Tuple[int, int, int, int] = (0, 0, 0, 0)) -> QImage:
		"""
		渲染单行多色文本
		
		Args:
			data: 文本数据列表,格式为[(文本, (R,G,B,A)), ...]
			background_color: 背景色RGBA,默认为全透明
			
		Returns:
			QImage: 渲染好的图像对象(Format_ARGB32格式)
		"""
		for i, d in enumerate(data):
			data[i] = (d[0].replace("\t"," "*4), d[1])
		# 不使用加法的原因是数据不都是元组(难道列表可以加元组?)
		# 计算布局
		total_width, line_height, char_layouts = self._calculate_layout(data)
		
		if total_width == 0 or line_height == 0:
			return QImage(1, 1, QImage.Format_ARGB32)
		
		# 创建图像
		image = QImage(total_width, line_height, QImage.Format_ARGB32)
		image.fill(QColor(*background_color))
		
		# 渲染
		painter = QPainter(image)
		painter.setRenderHint(QPainter.Antialiasing)
		painter.setRenderHint(QPainter.TextAntialiasing)
		painter.setRenderHint(QPainter.SmoothPixmapTransform)
		
		for layout in char_layouts:
			color = layout['color']
			x = layout['x']
			y = layout['baseline']
			
			painter.setFont(layout['font'])
			painter.setPen(color)
			
			# 渲染整个文本段(让字体引擎处理连体)
			if 'char' in layout:
				painter.drawText(x, y, layout['char'])
			else:
				painter.drawText(x, y, layout['text'])
		
		painter.end()
		return image
		
	def _update_metrics_cache(self):
		"""更新字体度量缓存"""
		self._metrics_cache['font0'] = QFontMetrics(self.font0)
		self._metrics_cache['font1'] = QFontMetrics(self.font1)
		
	def _precache_char_widths(self):
		"""
		预计算字符宽度
		
		只预计算常用字符,复杂情况让字体引擎处理
		这样可以提高渲染性能
		"""
		# 只预计算常用字符,复杂情况让字体引擎处理
		for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
			self._char_width_cache[('font0', char)] = self._metrics_cache['font0'].horizontalAdvance(char)
		
		for char in "中文字体测试":
			self._char_width_cache[('font1', char)] = self._metrics_cache['font1'].horizontalAdvance(char)
		
	def set_font_size(self, size: int):
		"""
		设置字体大小
		
		Args:
			size: 新的字体大小(像素)
		"""
		self.font0.setPixelSize(size)
		self.font1.setPixelSize(size)
		
		# 重新应用连体字设置
		if self.enable_ligatures:
			self._enable_font_ligatures(self.font0)
		
		self._update_metrics_cache()
		self._char_width_cache.clear()
		self._precache_char_widths()

	def estimate_render(
			self,
			width:int, # 宽度
			data:list=[("0123", (255,255,255,255))],
			k:float = 0.6 # 宽度占比
		) -> int:# 估量字体大小, 调整self字号, 返回合适字体大小的CodeLineRenderer实例字号
		self.set_font_size(10)
		rw = width * k
		ow = self.render_line(data).width()
		size = round(rw/ow*10)
		self.set_font_size(size)

		return size
	
	@staticmethod
	def creat_QFont(font_name:str, size: int) -> QFont:
		"""
		根据名称创建QFont字体 静态函数
		
		Args:
			font_name: 字体名称
			size: 字体大小(像素)
			enable_ligatures: 是否启用连体字
			
		Returns:
			QFont 字体对象
		"""
		font = QFont()
		font.setStyleHint(QFont.Monospace)
		font.setPixelSize(size)
		font.setFamily(font_name)

		if font.exactMatch(): return font

		font.setFamily("Consolas")
		print(f"警告: 字体{font_name}不存在; 使用备选字体 Consolas")
		
		return font

class Field:
	"""
	场域类 - 代码转视频的核心控制器
		
	管理整个代码转视频的过程,包括:
	- 时间线计算和帧序列生成
	- 语法高亮分析
	- 相机移动和缩放控制
	- 图像渲染和视频合成
	"""
	# 高亮颜色定义(RGBA格式) highlight_colours
	HC = {
		"R":(232,  66,  55, 255), #e84237 枫叶红 Red
		"Y":(252, 151,   0, 255), #fc9700 橙皮黄 Yellow
		"B":(124, 195, 251, 255), #7cc3fb  月蓝   Blue
		"b":(173, 216, 251, 255), #add8fb 冰山蓝 blue
		"g":( 73, 186, 124, 255), #49ba7c  空青   Cyan->green
		"P":(163, 133, 186, 255), #a385ba  粉紫   Purple
		"w":(238, 246, 248, 255), #eef6f8  葱白   White
		"G":(148, 147, 150, 255), #949396 橄榄灰 Gray
		"D":( 38,  45,  50, 255)  #262d32 灯草灰 Dark
	}  # 默认高亮颜色 RGBA,大写深色,小写浅色
	# 语法类型与颜色对照表 comparison_table
	CT = {
		"K": HC["R"],	# Keyword - 关键字
		"S": HC["b"],	# String - 字符串
		"N": HC["B"],	# Number - 数字
		"M": HC["G"],	# Comment - 单行注释
		"O": HC["R"],	# Operator - 运算符
		"U": HC["w"],	# Punctuation - 标点
		"P0":HC["B"],	# Parentheses Level 0 - 0级括号
		"P1":HC["g"],	# Parentheses Level 1 - 1级括号
		"P2":HC["Y"],	# Parentheses Level 2 - 2级括号
		"P3":HC["R"],	# Parentheses Level 3 - 3级括号
		"P4":HC["P"],	# Parentheses Level 4 - 4级括号
		"C": HC["Y"],	# Class - 类名
		"F": HC["P"],	# Function - 函数名
		"V": HC["w"],	# Variable - 变量名
		"A": HC["w"],	# Attribute - 属性名
		"B": HC["P"],	# Builtin - 内置
		"E": HC["Y"],	# Exception - 异常
		"X": HC["w"]	# Other - 其他
	}

	def __init__(self,
			text:str,											# 要转换的文本
			video_output_dir:str = os.path.dirname(__file__),	# 视频输出目录
			video_name:str = f"output.mp4",						# 视频名称(需要mp4结尾!!)
			speed_function:callable = lambda _:5,				# 字符速度函数 v = f(index) 表示index对应的输出速率(字符每秒);
			limit:str = "*1.0",									# 限制:"*zoom"速度缩放因子zoom; "-time(s)"自动求zoom, 满足时间限制
			indentation_speed:float = 1.0,						# 缩进倍速比例系数
			start_rest:float = 0.0,								# 开始休止时长(秒)
			end_rest:float = 0.0,								# 结束休止时长(秒)
			frame:int = 24,										# 导出视频的帧率
			background_img:QImage = None,						# 背景图片
			head_txt:str = None,								# 头文本
			language:str = "Python",							# 代码语言
			resolution:tuple[int, int] = (1920, 1080),			# 分辨率(宽×高)
			render:CodeLineRenderer = CodeLineRenderer()		# 用于绘图的render 主要是为了设置字体
		):
		"""
		初始化场域对象
		
		Args:
			text: 要转换为视频的代码文本
			video_output_dir: 视频输出目录路径
			video_name: 输出视频文件名
			speed_function: 速度函数,输入时间返回字符/秒
			limit: 时间限制参数,格式:"*缩放因子"或"-总时长(秒)"
			indentation_speed: 缩进速度比例,>1表示缩进部分打字更快
			start_rest: 视频开始前的静止时间(秒)
			end_rest: 视频结束后的静止时间(秒)
			frame: 输出视频的帧率
			background_img: 背景图片
			head_txt: 头文本
			language: 代码语言
			resolution: 视频分辨率(宽度, 高度)
			render: 用于绘图
		"""
		self.txt = text.replace(" "*4,"\t") # 使视觉感觉如TAB键
		# 因为我会 在本代码 频繁把" "*4对应的字符串换成"\t"(缩进需要); 所以为了不改变上述代码, 必须要写成" "*4
		self.output = video_output_dir
		self.workDir = os.path.join(video_output_dir, "CTV_"+os.path.splitext(video_name)[0])  # 工作目录(帧图集)
		self.workDir0 = os.path.join(self.workDir,"0") # 原始代码图片集
		self.workDir1 = os.path.join(self.workDir,"1") # 视频帧集

		self.name = video_name

		self.frame = frame
		self.frame2 = round(frame/2)  # 半帧,防止重复运算
		self.t0 = 1/frame  # 一帧时长(秒)

		self.vf = speed_function  # 速度函数
		self.inf = Field.getIndentationFunc(self.txt)  # 缩进层级函数
		self.ivk = indentation_speed  # 缩进速度系数

		self.w = resolution[0]  # 视野宽度(像素)
		self.h = resolution[1]  # 视野高度(像素)

		self.headTxt = head_txt if head_txt else os.path.splitext(video_name)[0] # 现在0行有文本了!
		self.language = language

		self.starRest = int(start_rest * self.frame)  # 开始休止帧数
		self.endRest = int(end_rest * self.frame)	 # 结束休止帧数
		
		print(f"{nowtime()} {self.name}")
		print(nowtime() + " XCL预计算...")
		if limit[0] == "*":
			self.xl, self.cl, self.endI = self.getBasicXCL(float(limit[1:]))
		elif limit[0] == "-":
			self.xl, self.cl, self.endI = self.getLimitXCL(float(limit[1:]))  # 包含休止时长
		else: raise ValueError("未知限制")
		self.length = len(self.xl) # 帧数量
		print(f"{nowtime()} 预计算完成, 共 {self.length}帧, 合 {self.length/frame}s")


		# 状态变量初始化 # 其实之后会重赋值
		self.index = 0   # 帧指针(当前处理到第几帧)
		self.il  = 0	 # 行指针, 非真行号 (现在得从0开始)
		#self.li = 1     # 行号 il=li+1

		# 相机系统参数
		self.camx:float	   # 截取位置,相机左上角位置 横坐标 # 之后会初始化
		self.camy:float	   # 截取位置,相机左上角位置 纵坐标
		#self._zoom:float  # 视野缩放因子放大倍速 # 下方直接赋值
		
		# 字体
		s0 = render.estimate_render(self.w, k=0.3)
		self.render = render
		s1 = CodeLineRenderer().estimate_render(self.w, k=0.05)

		self._zoom = float(s0 / s1)

		self.isB = True  # 缩放是否到未达极限 # 还有一处需要它进行判断
		self.blh = self.render.render_line([("A0中", (0, 0, 0, 255))]).height() # 获取基础原始行高

		self.cursorImg = self.render.render_line([("│", Field.HC["b"])]) # 光标图像
		self.headImg = self.render.render_line([(self.headTxt, Field.HC["G"])]) # 头文本图像
		
		# 布局参数
		linelen = self.txt.count("\n") + 1 # 行数, 需要 +1
		self.lh = float(s1)	 # 坐标系固定行高(逻辑单位) # 声明其实际应是浮点数
		self.wl = [None for _ in range(self.length)] # 图片宽列表
		self.ew = 0 # 完整图片 宽

		# 相机运动参数
		self.vcamx = 0.0  # 相机水平速度
		self.vcamy = 0.0  # 相机垂直速度
		self.maxv = 50.0	  # 最大分速度(是在视野, 而非定坐标系)
		self.vw = self.w / self._zoom  # 视界宽度(缩放后的实际视野宽度)
		self.vh = self.h / self._zoom  # 视界高度(缩放后的实际视野高度)
		self.springk = 1.40	 # 弹簧强度
		self.damping = 0.85  # 阻尼系数, 0-1之间, 越大阻尼越强

		# 光标系统
		self._cx = 0.0  # 光标横坐标
		#self.cy 直接作为属性

		if background_img: # 背景图像
			bg = background_img.scaledToHeight(self.h)
			if bg.width() == self.w: self.bgimg = bg
			else: raise Exception("传入的背景图片分辨率 与 要求的视频分辨率 比例不一致")
		else:
			self.bgimg = QImage(self.w, self.h, QImage.Format_ARGB32)
			self.bgimg.fill(QColor(*Field.HC["D"]))  # 纯色背景图
		#self.cvimg = cover_img_path 设置封面存在问题, 可能是不了解ffmpeg方法
		
		# 初始化
		print(nowtime() + " DATA预计算...")
		self.analysisCode()  # 分析代码语法结构
		self.gainDatum()	 # 获取数据
		print(nowtime() + f" 预计算完成")

		self.prepareDir()

	@property # 截取位置, 相机左上角位置 (只读属性)
	def cam(self): return (self.camx, self.camy)
	@property # 获取可用位置 (整数坐标,只读属性)
	def rcam(self): return (round(self.camx), round(self.camy))
	@property # 截取位置,相机中心位置 (只读属性)
	def camm(self): return (self.camx + self.vw/2, self.camy + self.vh/2)

	@cam.setter  # 设置相机左上角位置
	def cam(self, value:tuple[float, float]): self.camx, self.camy = value
	@camm.setter # 设置相机中心位置
	def camm(self, value:tuple[float, float]): self.camx, self.camy = value[0] - self.vw/2, value[1] - self.vh/2

	@property # 视野宽高 (只读属性)
	def wh(self): return (self.w, self.h)
	@property # 视野缩放后的实际行高 (只读属性)
	def rblh(self): return self._zoom*self.lh
	@property # 光标中心纵坐标 (只读属性)
	def cy(self): return self.il*self.lh + self.lh/2
	@property # 光标中心横坐标 (只读属性)
	def cx(self):
		w = self.wl[self.index] # 为None说明和之前一致
		if w: self._cx = w * self.rzoom # 赋值
		return self._cx # 现在或之前的横坐标
	@property # 获取代码图片中央位置 (只读属性)
	def mxy(self): return  self.ew * self.rzoom / 2, (self.il+1) * self.lh / 2

	@property # 坐标与实际生成图片的缩放比 (只读属性)
	def rzoom(self): return self.lh / self.blh # 这个好像就是zoom倒数?
	@property # 视野缩放因子 (读写属性)
	def zoom(self): return self._zoom
		
	@zoom.setter # 保持中心不变地缩放视野大小
	def zoom(self, newz:float):
		camm = self.camm
		self._zoom = newz
		self.vw = self.w / self._zoom  # 视界宽高调整 (先调)
		self.vh = self.h / self._zoom
		self.camm = camm # (再调, 因为其逻辑相关)

	@staticmethod
	def getIndentationFunc(txt:str):
		"""
		静态方法: 获取缩进层级函数
		为文本中的每个字符计算其缩进层级
		
		Args:
			txt: 要分析的文本
			
		Returns:
			list: 缩进层级列表,每个元素对应文本中一个字符的缩进层级
		"""
		txtlist = txt.split("\n")
		ilf = [s.count('\t') for s in txtlist]
		
		indentlinelist = [None for _ in range(len(txt))]
		n = 0
		for i, c in enumerate(indentlinelist):
			if c == "\n": n += 1  # \n视为下一行,非本行
			indentlinelist[i] = ilf[n]

		return indentlinelist

	def analysisCode(self):
		"""
		分析代码结构
		使用Pygments进行语法分析,生成高亮数据
		
		Args:
			language: 代码语言,目前只支持python
			
		Raises:
			ValueError: 如果语言不被支持
		"""
		raw_data = get_pygments(self.txt, self.language)
		data = raw_data # boil(raw_data) 进行预处理
		self.hl = data  # 高亮数据表

	def prepareDir(self):
		"""
		生成工作目录,用于保存图片
		
		创建必要的目录结构,如果目录已存在则提示用户
		"""
		if not os.path.exists(self.workDir):
			os.makedirs(self.workDir)
			os.makedirs(self.workDir0)
			os.makedirs(self.workDir1)
			print(f"{nowtime()} 已创建文件夹: {self.workDir}")

		else:
			print(f"{nowtime()} 文件夹已存在: {self.workDir}")
			od = input("	是否继续运行? 回车继续运行")
			if od not in ["", "Y", "y", "YES", "yes"]:
				print("\n	请自行删除文件夹!!")
				exit(1)
			
			print("	持续运行...")

	def supplementRest(self, ix:int, num:int, cursorValue:int=0):
		"""
		补充休止时间帧数
		在视频开始或结束时添加静止帧,光标在此期间闪烁
		
		Args:
			ix: 字符索引
			num: 要补充的帧数
			cursorValue: 光标状态初始值
			
		Returns:
			tuple: (最终光标值, 字符索引列表, 光标亮熄列表)
		"""
		xl = [ix for _ in range(num)]
		cl = xl[:]
		for i in range(num):
			if cursorValue <= -self.frame2+1: cursorValue = self.frame2  # 切换为熄,在1s内转换一次,"<="防止不可能发生的事
			else: cursorValue -= 1  # 向下递减
				
			cl[i] = cursorValue <= 0
		return cursorValue, xl, cl

	def getBasicXCL(self, zoom:float=1.0):
		"""
		获取基础字符索引与光标亮熄函数
		计算基本的帧序列,包括字符索引和光标状态
		
		Args:
			zoom: 速度缩放因子
			
		Returns:
			tuple: (字符索引列表xl, 光标状态列表cl)
		"""
		cursorValue, xl, cl = self.supplementRest(0, self.starRest)
		index = self.starRest
		ix = 0
		xl.append(0)  # 不需要floor
		cl.append(True)
		v1 = 0.0  # self.vf(t1)*zoom * self.ivk**self.inf[ix]
		
		while True:
			t2 = index * self.t0  # 末
			try: v2 = self.vf(t2) * zoom * self.ivk ** self.inf[xl[-1]]  # floor(ix)
			except: break  # 正常应该由于vf(t)定义域超出导致
					
			dx = (v1 + v2) * self.t0 / 2  # 简单求字符增量
			lateix = ix
			ix += dx
			index += 1
			v1 = v2

			if ix > len(self.txt):  # 防止溢出 # ix==0 对应"",不是第一个字符索引,故ix=length为最后一个字符
				break

			if cursorValue <= -self.frame2 + 1:cursorValue = self.frame2  # 切换为熄,在1s内转换一次,"<="防止不可能发生的事
			else: cursorValue -= 1  # 向下递减
				
			if abs(ceil(ix) - ceil(lateix)) != 0:  # 适应倒退字符(没有用~)以及一次多个字符
				cursorValue = 0  # 实现打字时常亮
			
			xl.append(floor(ix))
			cl.append(cursorValue <= 0)

		endindex = len(xl) -1 # 表示索引为 endindex 时已结束打字
		_, xxl, ccl = self.supplementRest(len(self.txt)-1, self.endRest, cursorValue)
		return xl + xxl, cl + ccl, endindex

	def getLimitXCL(self, timeLimit:float):
		"""
		获取具有最大时间限制的字符索引与光标亮熄函数
		
		通过二分法找到满足时间限制的速度缩放因子
		
		Args:
			timeLimit: 时间限制(秒)
			
		Returns:
			tuple: (字符索引列表xl, 光标状态列表cl)
		"""
		indexLimit = int(timeLimit * self.frame)  # 一定要是整数
		zoom0 = 1.0
		xl, cl, ei = self.getBasicXCL()
		dif0 = indexLimit - len(xl)  # 作差
		
		if dif0 == 0: return xl, cl, ei  # 因为是整数,容易归零 # 可如果这里返回,那太凑巧了

		while True:  # 找异号点
			if dif0 > 0:  # 总帧数小了 => zoom大了
				zoom1 = zoom0 * 0.5
			else:  # dif < 0 # 总帧数大了 => zoom小了
				zoom1 = zoom0 * 2.0
				
			xl, cl, ei = self.getBasicXCL(zoom1)
			dif1 = indexLimit - len(xl)  # 作差
			
			if dif1 == 0: return xl, cl, ei  # 如果这里返回,那也是太凑巧了
			elif dif0 * dif1 > 0:  # 同号继续找
				dif0 = dif1
				zoom0 = zoom1
			else:  # dif0*dif1 < 0 # 异号开始二分
				zooms = min(zoom0, zoom1)
				zoome = max(zoom0, zoom1)
				break

		while True:  # zoom越大,速度越大,总帧数len(xcl) 越小
			zoomm = (zooms + zoome) / 2  # 二分
			xl, cl, ei = self.getBasicXCL(zoomm)
			dif = indexLimit - len(xl)  # 作差
			
			if dif == 0: return xl, cl, ei # 因为是整数,容易归零(真的吗?)
			elif dif > 0: # 总帧数小了 => zoom大了 => 舍去end
				zoome = zoomm
			else: # dif < 0 # 总帧数大了 => zoom小了 => 舍去start
				zooms = zoomm		

	def gainDatum(self): # 获取数据列表集, 避免后期运算
		txtlist = [[i, c, self.hl[i]] for i, c in enumerate(self.txt)]
		datum = [[]] # 这是数据列表"集", 包含所有data数据
		record = [[]] # 每一份的数据长度记录
		nowtp = ("", None)
		lastc = None
		line = 1
		for one in txtlist:
			if one[1] != "\n": # "\n"需要进入下一nowtp
				nowc = one[2]
				if nowtp == ("", None): # 初始化
					nowtp = [self.txt[one[0]], nowc ]
				else:
					if nowc == lastc: # lastc不可能再为None
						nowtp[0] += self.txt[one[0]] # 高亮颜色相同执行合并
					else:
						datum[-1].append(nowtp)
						record[-1].append(one[0]-1)
						nowtp = [self.txt[one[0]], nowc ] 
				#lastc = nowc
			else: # 换行
				if nowtp == ("", None): # 避免上一行为空
					datum[-1].append(("", nowc))
				else:
					datum[-1].append(nowtp)
				record[-1].append(one[0]-1)	
				
				datum.append([]) # 标记换行
				record.append([])

				line += 1
				nowtp = ("", None)	 # 使下一环进行初始化
			
			lastc = nowc # 每处尾都需要

		if nowtp[1] is None:nowtp = (nowtp[0], "X")
		datum[-1].append(nowtp) # 加上最后一组(肯定不止0组~)
		record[-1].append(one[0])

		inDataL = [None for _ in range(self.length)] # 帧-数据索引 对应列表
		# (行号, 开始数据索引, 结束数据索引, 结束数据的结束字符索引)
		dataIe = 0 # 数据结束索引
		li = 1 # 行号
		lastix = None
		#sl = [None for _ in range(self.length)]
		for index, ix in enumerate(self.xl):
			if ix == lastix: continue
				#inDataL[index] = None # None防止冗余 # 注释掉 是因为原始就是None
				#lastix = ix # 因为一致呀
				
			lastix = ix

			if ix == 0: # 需要特殊处理 因为前侧无record数据
				inDataL[index] = (li, None, None)
				continue

			rix = ix-1 # 真索引

			while rix > record[li-1][-1]+1: # while 实现适应rix增长过快
				li += 1 # 换行 (record[li-1][-1]+1 索引指向txt中的"\n")
				dataIe = 0

			if rix == record[li-1][-1]+1:
				li += 1
				dataIe = 0
				inDataL[index] = (li, None, None)
				continue
				

			while True: # 因为上一段已经说明必定可以break
				if record[li-1][dataIe] >= rix:
					inDataL[index] = (li, dataIe, rix-record[li-1][dataIe]-1) # 第三项是负值索引
					break
				else: dataIe+=1

		self.xl = None # 置空
		self.datum = datum	 # 最终"返回" 总数据列表
		self.inDataL = inDataL # 帧-数据索引 对应列表	

	async def drawCodeLine(self, nowLi:int, nowData:list, nowIndex:int=None, isDone:bool=False):
		"""
		生成指定代码单行图片
		
		Args:
			nowLi: 真行号
			nowData: 数据列表
			nowIndex: 帧索引
			isDone: 是否完整(用于行号颜色)
			
		Returns:
			int: 生成的图片宽度(像素)
		"""
		wc = Field.HC["w"]
		gc = Field.HC["G"]
		nowData = [(d[0], Field.CT[ d[1] ] ) for d in nowData] # 似乎有冗余, 但外层要用键名称
		
		#s = "".join([d[0] for d in data]) # 表示现在生成图像对应的字符串
		fli = f"{nowLi:0{4}d}" # "9999"足够了
		nowData = [
				(fli, gc if isDone else wc),
				(" │", gc)
		  	] + nowData
		
		img = self.render.render_line(nowData)
		
		if nowIndex is not None: self.wl[nowIndex] = img.width() # 该值确定 故不需要用异步锁
		
		name = f"{fli}-{nowIndex:0{5}d}.png" if nowIndex is not None else f"{fli}.png"
		# 应该没有人会生成10万帧
		img.save(os.path.join(self.workDir0, name))
		# 适度增加I/O操作 从而更好地异步操作/减少内存占用

	async def generateCodeLines(self): # 异步生成代码图片
		tasks = [limit_wrap(self.drawCodeLine(il+1, linedata, isDone=True))
		   			for il, linedata in enumerate(self.datum)] # 完整行任务生成&包装
		
		nowData = None
		for index in range(self.length):
			if self.inDataL[index] is not None:
				li, de, ni = self.inDataL[index]
				# li真行号, datum索引; ni负数索引negative number index

				if de is None: nowData = [] # 表示不需要实际内容(只生成行号)

				else:
					nowData = [row[:] for row in self.datum[li-1][:de+1]] # 注意深拷贝 # 注意li-1为索引il
					if ni!=-1:
						if nowData[-1][1] == "K": # 只使关键词进行转换
							nowData[-1][1] = "X" # 简单实现最后一项高亮更新

						nowData = nowData[:-1] + [(nowData[-1][0][:ni+1], nowData[-1][1])] # 实现更新
				
				#s = "".join([d[0] for d in nowData]) # 表示要生成图像对应的字符串

				tasks.append(self.drawCodeLine(li, nowData[:], index)) # 异步任务; 并包装任务, 以限制最大量并行数
		
		print(f"{nowtime()} {self.workDir0} 开始生成原始图片...")
		
		with tqdm(total=len(tasks)) as pbar:
			async def track_task(task):
				result = await limit_wrap(task)
				pbar.update(1)  # 更新进度条
				return result
			
			tracked_tasks = [track_task(t) for t in tasks]
			await asyncio.gather(*tracked_tasks)

		self.linkLines() # 这个线性串行能怎么优化?

		self.datum = None # 置空
		
		print(nowtime() + " 原始图片生成完毕.")
	
	def linkLines(self): # 连接多行代码图片
		print(nowtime() + " 开始连接原图片...")
		
		self.headImg.save(os.path.join(self.workDir0, f"{0:0{4}d}.png"))
		p = os.path.join(self.workDir0, f"{1:0{4}d}.png")
		codeLinesImg = concatenate_images([
			self.headImg,
			QImage(p)
			])
		codeLinesImg.save(p) # 覆盖原图

		for il in range(1, len(self.datum)):
			p = os.path.join(self.workDir0, f"{il+1:0{4}d}.png")
			img = QImage(p)
			codeLinesImg = concatenate_images([codeLinesImg, img])
			codeLinesImg.save(p) # 覆盖原图
		
		self.ew = codeLinesImg.width()
		bgimg = QImage(self.ew+100, codeLinesImg.height()+100, QImage.Format_ARGB32)
		bgimg.fill(QColor(*Field.HC["D"]))
		previewImage = paste_rgba_to_rgba(bgimg, codeLinesImg, 50, 50)
		
		p= os.path.join(self.output, os.path.splitext(self.name)[0] + "_preview.png")
		previewImage.save(p) # 预览图生成

		print(nowtime() + " 完成处理原图片, 并生成了预览图 -> " + p)

	async def takeFrame(self,
					nowLi:int,	      # 现在(真)行号
					nowIndex:int,	  # 现在帧索引
					nowShowIndex:int, # 现在展示的帧索引(对应已保存的图片)
					rblh:float,	  # 真行高(不取整)
					nowCamPos:tuple[int,int],	 # 现在相机相对坐标(取整)
					nowCurPos:tuple[float,float]  # 现在光标相对坐标(不取整), 为None表示不显示光标
		): # 照相(takePhoto) -> 生帧
		rrblh = round(rblh)
		limg = QImage(self.w, rrblh, QImage.Format_ARGB32)
		limg.fill(QColor(*Field.HC["w"][:-1],20)) # 这是用于高亮正在打字的行

		#fli = f"{nowLi:0{4}d}" # 格式化行号
		nowcodeimg = concatenate_images([
				QImage(os.path.join(self.workDir0, f"{nowLi-1:0{4}d}.png")),
				QImage(os.path.join(self.workDir0, f"{nowLi:0{4}d}-{nowShowIndex:0{5}d}.png"))
			])

		x, y = nowCamPos
		bg = paste_rgba_to_rgba(self.bgimg, limg, 0, y + round((nowLi-1) * rblh))
		fg = QImage(*self.wh, QImage.Format_ARGB32) # 前景
		fg = paste_rgba_to_rgba(fg,
						nowcodeimg.scaledToHeight(round( (nowLi+1) * rblh) ),
						x, y - rrblh) # 放置代码图片

		if nowCurPos is not None: # 绘制光标
			cx, cy = nowCurPos
			cursorImg = self.cursorImg.scaledToHeight(rrblh)
			w, h = cursorImg.width(), cursorImg.height()
			fg = paste_rgba_to_rgba(fg, cursorImg, round(cx-w/2), round(cy-h/2)) # 光标图片居中放置

		frame_img = paste_rgba_to_rgba(bg, blur_glow(fg), 0 ,0) # 代码图片 模糊发光
		frame_img.save(os.path.join(self.workDir1, f"Frame{nowIndex}.png"))
	
	async def generateFrames(self): # 异步生成帧图片
		tasks = [None for _ in range(self.length)] # 异步任务
		self.camm = (self.cx, self.cy) # 初始化坐标
		self.nowi = 0 # 要得到的图像帧索引位置
		for self.index in range(self.length):
			if self.inDataL[self.index] is not None: # None指继承之前的数据
				self.li = self.inDataL[self.index][0] # 真行号
				self.il = self.li-1 # 索引(计算要用这个值)

			# 计算缩放
			if self.isB:
				self.calculateZoom()# isB True则说明缩放因子没有达到最小值(1.0), 需要计算zoom的计算

			# 计算坐标
			self.calculatePos((self.cx, self.cy) if self.index<=self.endI else self.mxy) # 以光标为中心计算位置

			if self.inDataL[self.index] is not None: self.nowi = self.index # 继承显示图片索引
			
			tasks[self.index] = self.takeFrame(
						self.li, # 真行号
						self.index,
						self.nowi,
						self.rblh, # 真行高(不取整)
						(
							round(-self.camx * self.zoom), # 横
							round(-self.camy * self.zoom)  # 纵
						), # 反转取整后的相对相机坐标
						(
							(self.cx-self.camx) * self.zoom, # 此处不取整
							(self.cy-self.camy) * self.zoom
						) if self.cl[self.index] else None # None表示不绘制光标
					)

		self.cl = None
		self.inDataL = None

		print(f"{nowtime()} {self.workDir1} 开始生成帧集...")
		
		with tqdm(total=len(tasks)) as pbar:
			async def track_task(task):
				result = await limit_wrap(task) # 限制包装
				pbar.update(1)  # 更新进度条
				return result
			
			tracked_tasks = [track_task(t) for t in tasks]
			await asyncio.gather(*tracked_tasks)


		print(f"{nowtime()} 帧集生成完毕.")

	def calculatePos(self, aim:tuple[float, float]):
		"""
		计算相机位置(阻尼版本)
		
		使用弹簧-阻尼模型计算相机平滑移动
		位置差产生加速度, 同时给速度添加阻尼项减少振荡
		"""
		aimx, aimy = aim
		x, y = self.camm  # 目前相机中心坐标
		dx, dy = aimx - x, aimy - y  # 位置差
		
		# 弹簧系数和阻尼系数(可调整)
		# springk 弹簧强度
		# damping 阻尼系数, 0-1之间, 越大阻尼越强
		# 弹簧力 = -k * dx (指向目标)
		# 阻尼力 = -damping * v (与速度方向相反)
		maxv = self.maxv * self.zoom # 转换绝对与相对
		# X轴
		ax = self.springk * dx - self.damping * self.vcamx
		vx = self.vcamx + ax * self.t0
		cammx = x + self.t0 * (self.vcamx + vx) / 2
		self.vcamx = min(vx, maxv)
		
		# Y轴 abs(dy)
		ay = self.springk * dy - self.damping * self.vcamy
		vy = self.vcamy + ay * self.t0
		cammy = y + self.t0 * (self.vcamy + vy) / 2
		self.vcamy = min(vy, maxv)
		
		self.camm = (cammx, cammy)

	def calculateZoom(self):
		"""
		计算缩放因子 不允许放大
		
		根据相机位置和内容边界自动调整缩放级别
		确保所有内容都在视野范围内
		"""
		# 赋予camy正值向负趋势; 光标要在视野内的趋势
		dy = max(self.camy + self.vh * 0.05, self.cy - self.camy - self.vh, 0)  # 计算趋势
		# 赋予camx正值向负趋势; 光标要在视野内的趋势
		dx = max(self.camx + self.vw * 0.05, self.cx - self.camx - self.vw, 0)
		
		# zoom只缩小不扩大(所以要与0取最大值), 缩小至1.0为止
		h = dy * 2 + self.vh
		w = dx * 2 + self.vw
		hr = self.vh / h
		wr = self.vw / w
		rate = min(hr, wr)  # zoom需乘的倍数
		rrate = 1 - 0.5*(1-rate)**2 # 修正比率, 减小波动
		# 0<x=rata<=1
		# f(x) = 1-0.5(1-x)**n, n>1(n=0退化为一次函数)
		# f`(x)= 0.5n(1-x)**n, n 同上
		# f(x)满足以下要求: f(0)=0.5;f(1)=1; f`(1)=0;f`(0)随n增大而增大;f`(0)在[0,1]上单减
		# 想暂弃用
		zoom = self.zoom * rrate
		if zoom <= 1:  # 说明达到极限
			#print("zoom达到极限")
			self.zoom = 1.0
			self.isB = False
		else: self.zoom = zoom

	def creatVideo(self): # 创建视频
		print(nowtime() + " 开始合成视频...")
		p = os.path.join(self.output, self.name)
		success = create_video(self.workDir1,
					p,
					self.frame,
					end_index = self.length-1 # 因为从0开始
			)
		
		print(f"\n{nowtime()} "
			+ (f"视频生成完成! -> {p}" if success else f"视频生成失败!!")
			)

	def main(self):
		"""
		主函数:生成视频
		
		完整的视频生成流程: 预处理, 帧生成, 视频合成
		使用进度条显示生成进度
		"""
		print(nowtime() + " 开始生成视频...")

		asyncio.run(self.generateCodeLines())
		asyncio.run(self.generateFrames())
		self.creatVideo()

		try: MessageBeep() # 提醒
		except: pass

		print(f"\n{nowtime()} 完成 {self.name} - ω")
	
	#region Field外部函数

def get_pygments(code:str, language:str) -> list:
	"""
	直接获取 Pygments token 的简化类型序列
		
	将Pygments的复杂token类型映射为简化的单字符类型
		
	Args:
		code: 要分析的代码文本
		language: 代码语言
		
	Returns:
		list: 简化类型序列,每个字符对应一个类型
	"""
	table = { # 只列举一些部分主流语言及常用后缀
		"Python": PythonLexer,
		"py":     PythonLexer,
		"C":      CLexer,
		"c":      CLexer,
		"C++":    CppLexer,
		"cpp":    CppLexer,
		"C#":     CSharpLexer,
		"cs":     CSharpLexer,
		"Jave":   JavaLexer,
		"jave":   JavaLexer
	}
	if language not in table.keys(): raise ValueError(f"暂不支持的语言: {language}")

	tokens = list(lex(code, table[language]()))
	simple_types = []
		
	# Pygments token 到简化类型的映射
	token_map = {
		# 关键字
		Token.Keyword: 'K',
		Token.Keyword.Constant: 'K',
		Token.Keyword.Declaration: 'K',
		Token.Keyword.Namespace: 'K',
		Token.Keyword.Pseudo: 'K',
		Token.Keyword.Reserved: 'K',
		Token.Keyword.Type: 'K',
		
		# 字符串
		Token.String: 'S',
		Token.String.Single: 'S',
		Token.String.Double: 'S',
		Token.String.Triple: 'S',
		
		# 数字
		Token.Number: 'N',
		Token.Number.Integer: 'N',
		Token.Number.Float: 'N',
		Token.Number.Hex: 'N',
		Token.Number.Oct: 'N',
		Token.Number.Bin: 'N',
		
		# 注释
		Token.Comment: 'M',
		Token.Comment.Single: 'M',
		Token.Comment.Multiline: 'M',
		
		# 运算符
		Token.Operator: 'O',
		Token.Operator.Word: 'O',
		
		# 标点符号
		Token.Punctuation: 'U',
		
		# 名称相关
		Token.Name: 'V',
		Token.Name.Attribute: 'A',
		Token.Name.Builtin: 'B',
		Token.Name.Builtin.Pseudo: 'B',
		Token.Name.Class: 'C',
		Token.Name.Constant: 'V',
		Token.Name.Decorator: 'D',
		Token.Name.Entity: 'V',
		Token.Name.Exception: 'E',
		Token.Name.Function: 'F',
		Token.Name.Function.Magic: 'F',
		Token.Name.Label: 'L',
		Token.Name.Namespace: 'V',
		Token.Name.Other: 'V',
		Token.Name.Property: 'A',
		Token.Name.Tag: 'T',
		Token.Name.Variable: 'V',
		Token.Name.Variable.Class: 'V',
		Token.Name.Variable.Global: 'V',
		Token.Name.Variable.Instance: 'V',
		Token.Name.Variable.Magic: 'V',
		
		# 其他
		Token.Generic: 'X',
		Token.Error: 'X',
		Token.Other: 'X',
		Token.Text: 'X',
		Token.Whitespace: 'X',
	}
		
	for token_type, token_value in tokens:
		# 找到对应的简化类型
		simple_type = 'X'  # 默认值
		for pyg_token, simple_char in token_map.items():
			if token_type in pyg_token:
				if token_value == ".":
					simple_type = 'U'  # 其实是标点
				else:
					simple_type = simple_char
				break
		for _ in range(len(token_value)):
			simple_types.append(simple_type)

	# 处理括号层级
	ks = "([{"
	ke = ")]}"
	f = 0
	late = "e"
	for i, t in enumerate(simple_types):
		if t == "U" and code[i] in ks:
			if late == "e":
				late = "s"
			else:
				f += 1
			simple_types[i] = "P" + str(f % 5)
		elif t == "U" and code[i] in ke:
			if late == "s":
				late = "e"
			else:
				f -= 1
			simple_types[i] = "P" + str(f % 5)

	return simple_types

def concatenate_images(images, spacing=0):
	"""
	垂直拼接多个QImage,背景为全透明,左对齐
		
	Args:
		images: QImage列表
		spacing: 图像间距(像素)
		
	Returns:
		QImage: 透明背景的拼接图像
	"""
	if not images:
		return QImage()
		
	# 计算总高度和最大宽度
	total_height = sum(img.height() for img in images) + spacing * (len(images) - 1)
	max_width = max(img.width() for img in images) if images else 0
		
	if total_height <= 0 or max_width <= 0:
		return QImage()
		
	# 创建全透明的结果图像
	result = QImage(max_width, total_height, QImage.Format_ARGB32)
	result.fill(Qt.transparent)
		
	# 创建QPainter进行绘制
	painter = QPainter(result)
		
	# 依次绘制每个图像(左对齐)
	y_offset = 0
	for img in images:
		painter.drawImage(0, y_offset, img)
		y_offset += img.height() + spacing
		
	painter.end()
	return result

def paste_rgba_to_rgba(background:QImage, foreground:QImage, x, y, blend_mode=QPainter.CompositionMode_SourceOver):
	"""
	将RGBA前景图粘贴到RGBA背景图的指定坐标
		
	Args:
		background: 背景图像(QImage,必须有Alpha通道)
		foreground: 前景图像(QImage,必须有Alpha通道)
		x, y: 粘贴坐标(左上角位置)
		blend_mode: 混合模式,默认为SourceOver
		
	Returns:
		QImage: 粘贴后的图像(与背景图分辨率一致)
		
	Note:
		- 前景图超出背景图边界的部分会被裁剪
		- 保持背景图和前景图的透明度
		- 使用指定的混合模式进行合成
	"""
	if background.isNull() or foreground.isNull():
		return QImage()
		
	bg_copy = QImage(background)
	painter = QPainter(bg_copy)  # 创建QPainter进行绘制
	painter.setCompositionMode(blend_mode)  # 设置混合模式
	painter.drawImage(x, y, foreground)  # 绘制前景图(超出边界的部分QPainter会自动裁剪)
	painter.end()
		
	return bg_copy

from pathlib import Path
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
		
	print(f"📊 视频信息:")
	print(f"  工作目录: {work_dir}")
	print(f"  帧范围: {start_index} - {end_index} (共{end_index - start_index + 1}帧)")
	print(f"  帧率: {frame_rate} FPS")
	print(f"  输出: {video_name}")
		
	# 构建FFmpeg命令
	input_pattern = str(work_path / "Frame%d.png")
		
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
		
	print(f"🔧 FFmpeg命令: {' '.join(cmd)}")
		
	# 调试:检查文件是否存在
	print("\n🔍 检查文件...")
	frames_found = 0
	for i in range(start_index, end_index + 1):
		frame_file = work_path / f"Frame{i}.png"
		if frame_file.exists():
			frames_found += 1
		else:
			print(f"❌ 找不到帧: {frame_file.name}")
			# return False
		
	print(f"  总共找到 {frames_found}/{end_index - start_index + 1} 个帧文件")
		
	if frames_found < (end_index - start_index + 1) / 2:  # 如果缺失超过一半的帧
		print("⚠️  警告: 缺少很多帧文件")
		
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
		print("\n🚀 开始视频合成...")
		for line in process.stdout:
			line = line.rstrip()
			if "frame=" in line:
				print("\033[2K\r" + line, end="")
			else: logtext += line + "\n"

		# 等待进程完成
		process.wait()
		
		if process.returncode == 0:
			print(f"\n✅ 视频合成完成: {work_path / video_name}")
			
			# 检查输出文件
			output_file = work_path / video_name
			if output_file.exists():
				file_size = output_file.stat().st_size
				print(f"📁 文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
				return True
			else:
				print("❌ 输出文件未生成")
				return False
		else:
			print("-"*10+logtext+"-"*10)
			print(f"\n❌ FFmpeg失败,返回码: {process.returncode}")
			return False
			
	except FileNotFoundError:
		print("❌ 找不到ffmpeg, 请确保已安装并添加到PATH")
		return False
	except Exception as e:
		print(f"❌ 执行失败: {e}")
		return False
	
	#endregion

	#region 异步相关
semaphore = asyncio.Semaphore(MAX_CONCURRENT)
async def limit_wrap(task): # 异步限制包装
	async with semaphore:
		return await task
	
	#endregion

	#region 实用函数

def quick_open(txt_input_path:str) -> str: # 快速打开文本文件
	with open(txt_input_path, "r", encoding='utf-8') as f: 
		txt = f.read()
	return txt

def make_text_image(txtData:list,
				font_size_k:float=0.6,
				color:tuple[int, int, int, int] = Field.HC["D"],
				resolution:tuple[int, int] = (1920, 1080),
				blurglow:bool=True,
				render = CodeLineRenderer()
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

def blur_glow(img:QImage, rate:float=10.0, alpha:float=0.6, num:int=3) -> QImage: # 简单地用模糊来发光
	bluring = QImage(img.size(), QImage.Format_ARGB32_Premultiplied)
	bluring.fill(Qt.transparent)
	painter = QPainter(bluring)  # 创建QPainter进行绘制
	painter.setCompositionMode(QPainter.CompositionMode_SourceOver)  # 设置混合模式
	painter.setOpacity(alpha)	# 设置画笔不透明度
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
	
	#endregion

#endregion

if 0 and __name__ == "__main__":  # 手动合成视频
	success = create_video(
		work_dir=THIS_PATH+"CTV_helloWorld_c\\1", # 帧集
		video_name=THIS_PATH+"helloWorld_c.mp4",
		frame_rate=30, # 帧率
		end_index=2000 # 最后的索引, 非总帧数
	)

if 0 and __name__ == "__main__": # 模版主程序入口
	print(nowtime() + " 程序正式运行...")
	txt = """\
print("Hello World!")
#
"""# quick_open(YourCodePath) # 或者用这个函数获取代码文本 (直接再写with打开也成, 用这个函数省一些语句)
	
	bg = make_text_image(
		[("- ω -", (238, 246, 248, 25))],
		render = CodeLineRenderer(font0="Consolas")
		)    # 生成背景图

	field = Field(
				text=txt,					 # 用于生成视频的原始代码
				video_name=f"output.mp4",    # 保存的名称; 需要带.mp4
				speed_function=lambda _:7.5, # 速度(需要传函数) # ~~为了以后尝试卡点~~
				frame=15,			  # 帧率15-40为合适范围;15偏向于测试
				start_rest=1.0,		  # 开始打字前悬停时长(秒)
				end_rest=5.0,		  # 打字完成后悬停时长(秒)
				#limit="-60",		  # 限制因子 "*{k}"表示倍速k倍; "-{t}"表示时长为t秒
				indentation_speed=2.5,# 缩进速度因子(每缩进一次要多乘它一次)
				background_img=bg,    # 背景图
				head_txt="output.py", # 头文本
				#language="py", # 可以直接输语言的(常用)后缀名 默认py
				#resolution=(1920, 1080), # 分辨率, 默认是这个值  # (1080, 1920) 一般竖版分辨率
				render = CodeLineRenderer(font0="Consolas") # 传render; 主要是字体
			)

	field.main() # 开始生成

if 0 and __name__ == "__main__": # 示例主程序入口
	print(nowtime() + " 程序正式运行...")
	#THIS_PATH = os.path.dirname(__file__) +"\\" # 这是全局变量
	
	bg = make_text_image([("- ω -", (238, 246, 248, 25))]) # 生成背景图

	make_text_image([
		("Hello World", Field.HC["P"]),	# Field.HC是一个rbga颜色字典
		],
		resolution=(2000,1500)).save(THIS_PATH+"helloWorld_cover.png") # 保存一个封面

	try:
		txt = quick_open(THIS_PATH+r"showings\helloWorld.c")
		field = Field(txt,
					video_name=f"helloWorld_c0.mp4",
					speed_function=lambda _:7.5,
					frame=10,
					start_rest=1.0,
					end_rest=7.0,
					limit="-10",
					indentation_speed=2.5,
					background_img=bg,
					head_txt="helloWorld.c",
					language="c",
					resolution=(1920, 1080)
				)

		field.main()
	finally:  # 进行提醒,并保持可能的报错处理
		for _ in range(3):
			sleep(0.5)
			MessageBeep()
		#input("等待回车...")
