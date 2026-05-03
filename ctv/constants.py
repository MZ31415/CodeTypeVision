"""
ctv-constants 常量
主要存一些颜色和类型键值对
-ω-
"""

# TODO: 考虑写一个静态类来管理所有的常量, 允许用户上传自定义内容 (考虑暂不考虑此想法, 毕竟需求小, 不如直接硬编码)

# 默认颜色定义(RGBA格式)
DC = {
    "R": (232,  66,  55, 255),  # #e84237 枫叶红
    "Y": (252, 151,   0, 255),  # #fc9700 橙皮黄
    "B": (124, 195, 251, 255),  # #7cc3fb 月蓝
    "b": (173, 216, 251, 255),  # #add8fb 冰山蓝
    "g": ( 73, 186, 124, 255),  # #49ba7c 空青
    "P": (163, 133, 186, 255),  # #a385ba 粉紫
    "w": (238, 246, 248, 255),  # #eef6f8 葱白
    "G": (148, 147, 150, 255),  # #949396 橄榄灰
    "D": ( 38,  45,  50, 255)   # #262d32 灯草灰
}

DEFAULT_BACKGROUND_COLOR = DC["D"] # 默认背景色
CURSOR_IMG_COLOR = DC["B"] # 光标颜色
CURSOR_LINE_COLOR = DC["G"][:-1] + (25,) # 光标 所在行 着色

KEYS_TABLE = { # 词元种类&颜色 键值对转换字典
    # 话说为什么非要有一个中间键来转换? # 一来可能后期修改颜色; 二来能避免在类内部的硬编码?
        ' ':   "w", # Token

        'T':   "w", # Token.Text
        'W':   "w", # Token.Text.Whitespace
        'ESC': "B", # Token.Escape
        'ERR': "R", # Token.Error
        'X':   "w", # Token.Other

        'K':   "R", # Token.Keyword
        'Kc':  "B", # Token.Keyword.Constant
        'Kd':  "R", # Token.Keyword.Declaration
        'Kn':  "R", # Token.Keyword.Namespace
        'Kp':  "B", # Token.Keyword.Pseudo
        'Kr':  "R", # Token.Keyword.Reserved
        'Kt':  "Y", # Token.Keyword.Type

        'N':    "w", # Token.Name
        'Na':   "w", # Token.Name.Attribute
        'Nb':   "P", # Token.Name.Builtin
        'Nbp':  "B", # Token.Name.Builtin.Pseudo
        'Nc':   "Y", # Token.Name.Class
        'No':   "B", # Token.Name.Constant
        'Nd':   "P", # Token.Name.Decorator
        'Ni':   "w", # Token.Name.Entity
        'Ne':   "Y", # Token.Name.Exception
        'Nf':   "P", # Token.Name.Function
        'Nfm':  "B", # Token.Name.Function.Magic
        'Npy':  "w", # Token.Name.Property
        'Nl':   "P", # Token.Name.Label
        'Nn':   "Y", # Token.Name.Namespace
        'Nx':   "w", # Token.Name.Other
        'Nt':   "w", # Token.Name.Tag
        'Nv':   "w", # Token.Name.Variable
        'Nvc':  "w", # Token.Name.Variable.Class
        'Nvg':  "w", # Token.Name.Variable.Global
        'Nvi':  "w", # Token.Name.Variable.Instance
        'Nvm':  "B", # Token.Name.Variable.Magic

        'L':    "w", # Token.Literal
        'Ld':   "w", # Token.Literal.Date

        'S':    "b", # Token.String
        'Sa':   "R", # Token.String.Affix
        'Sb':   "b", # Token.String.Backtick
        'Sc':   "b", # Token.String.Char
        'Sdl':  "w", # Token.String.Delimiter
        'Sd':   "b", # Token.String.Doc
        'S2':   "b", # Token.String.Double
        'Se':   "R", # Token.String.Escape
        'Sh':   "b", # Token.String.Heredoc
        'Si':   "w", # Token.String.Interpol
        'Sx':   "b", # Token.String.Other
        'Sr':   "b", # Token.String.Regex
        'S1':   "b", # Token.String.Single
        'Ss':   "b", # Token.String.Symbol

        'M':    "B", # Token.Number
        'Mb':   "B", # Token.Number.Bin # 2 0b
        'Mf':   "B", # Token.Number.Float
        'Mh':   "B", # Token.Number.Hex # 16 0x
        'Mi':   "B", # Token.Number.Integer
        'Mil':  "B", # Token.Number.Integer.Long
        'Mo':   "B", # Token.Number.Oct # 8 0o

        'O':    "R", # Token.Operator
        'Ow':   "R", # Token.Operator.Word

        'P':    "w", # Token.Punctuation
        'Pm':   "w", # Token.Punctuation.Marker
        'P0':   "B", # P0-4 五级括号
        "P1":   "g",
        "P2":   "Y",
        "P3":   "R",
        "P4":   "P",

        'C':    "G", # Token.Comment
        'Ch':   "G", # Token.Comment.Hashbang
        'Cm':   "G", # Token.Comment.Multiline
        'Cp':   "R", # Token.Comment.Preproc
        'Cpf':  "B", # Token.Comment.PreprocFile
        'C1':   "G", # Token.Comment.Single
        'Cs':   "R", # Token.Comment.Special

        'G':    "w", # Token.Generic # TODO: 考虑换颜色(不过也没有必要)
        'Gd':   "w", # Token.Generic.Deleted
        'Ge':   "w", # Token.Generic.Emph
        'Gr':   "w", # Token.Generic.Error
        'Gh':   "w", # Token.Generic.Heading
        'Gi':   "w", # Token.Generic.Inserted
        'Go':   "w", # Token.Generic.Output
        'Gp':   "w", # Token.Generic.Prompt
        'Gs':   "w", # Token.Generic.Strong
        'Gu':   "w", # Token.Generic.Subheading
        'Ges':  "w", # Token.Generic.EmphStrong
        'Gt':   "w"  # Token.Generic.Traceback
    }
