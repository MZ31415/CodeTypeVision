"""
ctv-render 渲染(器)
Renderer类实现字体家族渲染文本图片
通过 Vibe coding 修改之前的Renderer
-ω-
"""

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QFontMetricsF, QFontInfo,
    QImage, QTextLayout
)
import math

__all__ = ["Renderer"]

class Renderer:
    """
    单行多色多字体渲染器
    - 真正通过 setFamilies 实现多字体 fallback
    - 支持连体字(OpenType 标准连体)
    - 提供精确字符右边界查询
    """

    DEFAULT_FONTS = ["Fira Code Retina", "Microsoft YaHei UI", "Consolas"]

    def __init__(self,
                 default_font_size: int = 20,
                 fonts: list[str] | None = None,
                 enable_ligatures: bool = True):
        self.default_font_size = default_font_size
        self.font_families = fonts if fonts else self.DEFAULT_FONTS
        self.enable_ligatures = enable_ligatures

        self.font = self._create_font()
        self.metrics = QFontMetricsF(self.font)

    # ─── 私有方法 ─────────────────────────
    def _create_font(self) -> QFont:
        """根据当前配置创建统一的 QFont(多字体 fallback)"""
        font = QFont()
        font.setFamilies(self.font_families)
        font.setPixelSize(self.default_font_size)

        font.setStyleHint(QFont.Monospace)
        font.setStyleStrategy(QFont.PreferAntialias)
        font.setHintingPreference(QFont.PreferNoHinting)

        if not self.enable_ligatures:
            font.setFixedPitch(True)
            font.setWeight(QFont.Normal)   # 明确正常字重，避免干扰
        # 连体模式下，不加任何可能禁用连体的属性
        return font

    def _measure_segments(self,
                          data: list[tuple[str, tuple[int, int, int, int]]]
                          ) -> tuple[float, float, list[dict]]:
        """
        计算每个字符的几何信息(仅用于边界查询,不渲染)
        返回: (总宽, 行高, 字符布局列表)
        每个布局 dict:
            'x': float       左边界绝对横坐标
            'width': float   字符宽度(考虑了连体)
        """
        layouts = []
        current_x = 0.0
        line_height = self.metrics.height()

        for text, _color in data:
            if not text:
                continue
            layout = QTextLayout(text, self.font)
            layout.beginLayout()
            line = layout.createLine()
            if not line.isValid():
                layout.endLayout()
                continue
            line.setLineWidth(1e6)
            line.setPosition(QPointF(0, 0))
            layout.endLayout()

            for i in range(len(text)):
                x_left, _ = line.cursorToX(i)      # 解包元组 (float, int)
                x_right, _ = line.cursorToX(i + 1)
                char_width = x_right - x_left
                layouts.append({
                    'x': current_x + x_left,
                    'width': char_width,
                })
            current_x += line.naturalTextWidth()

        return current_x, line_height, layouts
    
    def _render_segments(self,
                         data: list[tuple[str, tuple[int, int, int, int]]],
                         image: QImage) -> None:
        """按原始文本段整段绘制(保留连体)"""
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        x_cursor = 0.0
        for text, color in data:
            if not text:
                continue
            layout = QTextLayout(text, self.font)
            layout.beginLayout()
            line = layout.createLine()
            if not line.isValid():
                layout.endLayout()
                continue
            line.setLineWidth(1e6)
            line.setPosition(QPointF(0, 0))
            layout.endLayout()
            seg_width = line.naturalTextWidth()

            painter.setFont(self.font)
            painter.setPen(QColor(*color))
            painter.drawText(int(x_cursor), int(self.metrics.ascent()), text)
            x_cursor += seg_width

        painter.end()

    # ─── 公共接口 ─────────────────────────
    def render_line(self,
                    data: list[tuple[str, tuple[int, int, int, int]]],
                    background_color: tuple[int, int, int, int] = (0, 0, 0, 0)
                    ) -> QImage:
        """纯渲染:返回图像(保留连体)"""
        total_w, line_h, _ = self._measure_segments(data)

        if total_w == 0 or line_h == 0:
            return QImage(1, 1, QImage.Format_ARGB32)

        img_w = int(math.ceil(total_w))
        img_h = int(math.ceil(line_h))
        image = QImage(img_w, img_h, QImage.Format_ARGB32)
        image.fill(QColor(*background_color))

        self._render_segments(data, image)
        return image

    def render_line_with_char_rect(self,
                                   data: list[tuple[str, tuple[int, int, int, int]]],
                                   char_index: int,
                                   background_color: tuple[int, int, int, int] = (0, 0, 0, 0)
                                   ) -> tuple[QImage, int]:
        """渲染并返回指定字符右边界 x 坐标"""
        total_w, line_h, layouts = self._measure_segments(data)

        if total_w == 0 or line_h == 0:
            return QImage(1, 1, QImage.Format_ARGB32), 0

        img_w = int(math.ceil(total_w))
        img_h = int(math.ceil(line_h))
        image = QImage(img_w, img_h, QImage.Format_ARGB32)
        image.fill(QColor(*background_color))

        self._render_segments(data, image)

        if 0 <= char_index < len(layouts):
            item = layouts[char_index]
            right_edge = int(item['x'] + item['width'])
        else:
            right_edge = 0

        return image, right_edge

    def set_font_size(self, size: int) -> None:
        """动态修改字号"""
        self.default_font_size = size
        self.font = self._create_font()
        self.metrics = QFontMetricsF(self.font)

    def estimate_render(self,
                        width: int,
                        data: list = [("0123", (255, 255, 255, 255))],
                        k: float = 0.6) -> int:
        """估算并设置适合给定宽度的字号"""
        self.set_font_size(10)
        rw = width * k
        ow = self.render_line(data).width()
        size = round(rw / ow * 10)
        self.set_font_size(size)
        return size

    @staticmethod
    def creat_QFont(font_families: list[str],
                    size: int,
                    enable_ligatures: bool = True) -> QFont:
        """静态工厂:根据字体列表创建 QFont"""
        font = QFont()
        font.setFamilies(font_families)
        font.setPixelSize(size)
        font.setStyleHint(QFont.Monospace)
        font.setStyleStrategy(QFont.PreferAntialias)
        font.setHintingPreference(QFont.PreferNoHinting)
        if enable_ligatures:
            font.setWeight(QFont.Medium)
            font.setFixedPitch(True)

        fi = QFontInfo(font)
        if fi.family() not in font_families:
            font.setFamilies(["Consolas"])
        return font
