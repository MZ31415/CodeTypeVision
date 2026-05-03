#!/usr/bin/env python
#-*- coding:UTF-8 -*-
TEXT = """
ctv v0.5.0

此包来自 https://github.com/ymz-w/CodeTypeVision

github ymz-w (https://github.com/ymz-w)
B站 云墨-w (https://space.bilibili.com/3546881812597194)

-ω-
"""
__version__ = "0.5.0"
__author__ = "ymz-w | 云墨-w"

from .config import Config
from .core import CTVField

from PyQt5.QtWidgets import QApplication
_QTAPP = QApplication([]) # 确保渲染正常

__all__ = ["Config", "CTVField"]

print(TEXT)
