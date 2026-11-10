"""Start page shown while no document is open."""
import os

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (QAbstractButton, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from core.version import APP_NAME, VERSION

from .common import ACCENT, INK, glyph_pixmap, primary

TILES = [
    ("open", "打开并编辑", "加文字、改字、插图、批注\n页面旋转/删除/排序", "#e5484d", "edittext"),
    ("merge", "合并 PDF", "多个 PDF 和图片\n合成一个文件", "#2f6fed", "merge"),
    ("split", "拆分 PDF", "按范围、按页数、\n按书签拆成多个文件", "#0f9d8a", "split"),
    ("sign", "签名", "手写、照片或输入姓名\n生成签名盖到文件上", "#7a4be0", "sign"),
    ("images", "图片转 PDF", "把照片、扫描件\n拼成一个 PDF", "#e08a1a", "images"),
    ("blank", "新建空白文档", "从一张 A4 白纸开始", "#48536e", "blank"),
]


class Tile(QAbstractButton):
    def __init__(self, title, desc, color, icon_name, parent=None):
        super().__init__(parent)
        self.title, self.desc, self.color = title, desc, QColor(color)
        self.pm = glyph_pixmap(icon_name, "#ffffff", 44)
        self.ghost = glyph_pixmap(icon_name, "#ffffff", 150)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(210, 150)

    def sizeHint(self):
        return QSize(250, 170)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        base = self.color.lighter(112) if self.underMouse() else self.color
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, base)
        g.setColorAt(1, base.darker(128))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 12, 12)
        p.setClipRect(r)
        p.setOpacity(0.13)
        p.drawPixmap(int(r.right() - 128), int(r.bottom() - 118), self.ghost)
        p.setOpacity(1)
        p.drawPixmap(18, 18, self.pm)
        f = QFont(self.font())
        f.setPixelSize(20)
        f.setBold(True)
        p.setFont(f)
        p.setPen(Qt.white)
        p.drawText(QRectF(20, 70, r.width() - 30, 30), Qt.AlignLeft | Qt.AlignVCenter, self.title)
        f.setPixelSize(13)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 225))
        p.drawText(QRectF(20, 102, r.width() - 30, r.height() - 106), Qt.AlignLeft | Qt.AlignTop, self.desc)

    def enterEvent(self, e):
        self.update()

    def leaveEvent(self, e):
        self.update()


class Hero(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor("#232c44"))
        g.setColorAt(1, QColor("#141a2b"))
        p.fillRect(r, g)
        # ghost type
        f = QFont("Arial Black")
        f.setPixelSize(120)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 14))
        p.save()
        p.translate(r.width() - 10, r.height() - 30)
        p.rotate(-90)
        p.drawText(0, 0, "PDF")
        p.restore()
        # stacked sheets
        p.save()
        p.translate(46, 54)
        for i, (ang, col) in enumerate(((-9, "#3a4666"), (-3, "#55628a"), (4, "#ffffff"))):
            p.save()
            p.rotate(ang)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(col))
            p.drawRoundedRect(QRectF(0, 0, 96, 124), 6, 6)
            if i == 2:
                p.setBrush(QColor(ACCENT))
                p.drawRoundedRect(QRectF(12, 14, 46, 20), 4, 4)
                p.setPen(Qt.white)
                ff = QFont("Arial")
                ff.setPixelSize(13)
                ff.setBold(True)
                p.setFont(ff)
                p.drawText(QRectF(12, 14, 46, 20), Qt.AlignCenter, "PDF")
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#c9cfdd"))
                for k, w in enumerate((70, 60, 72, 44, 66)):
                    p.drawRoundedRect(QRectF(12, 46 + k * 11, w, 5), 2, 2)
                p.setPen(QPen(QColor("#1a3fb5"), 2.2, Qt.SolidLine, Qt.RoundCap))
                from PySide6.QtGui import QPainterPath
                path = QPainterPath()
                path.moveTo(16, 112)
                path.cubicTo(28, 92, 34, 122, 44, 104)
                path.cubicTo(52, 92, 58, 118, 80, 100)
                p.setBrush(Qt.NoBrush)
                p.drawPath(path)
            p.restore()
        p.restore()
        f = QFont(self.font())
        f.setPixelSize(30)
        f.setBold(True)
        p.setFont(f)
        p.setPen(Qt.white)
        p.drawText(QRectF(30, 214, 250, 44), Qt.AlignLeft | Qt.AlignVCenter, APP_NAME)
        f.setPixelSize(13)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#aeb6ca"))
        p.drawText(QRectF(30, 260, 250, 24), Qt.AlignLeft | Qt.AlignVCenter, f"版本 {VERSION} · 绿色免安装")
        p.setPen(QColor("#dfe3ee"))
        lines = ["✓  拆分 / 合并 / 页面整理", "✓  加文字、改字、图片、批注", "✓  手写签名、图片签名",
                 "✓  水印、页码、加密、压缩", "✓  全部在本机处理，不上传文件"]
        for i, t in enumerate(lines):
            p.drawText(QRectF(30, 304 + i * 27, 260, 24), Qt.AlignLeft | Qt.AlignVCenter, t)
        p.setPen(QPen(QColor(ACCENT), 3))
        p.drawLine(30, 294, 86, 294)


class Home(QWidget):
    action = Signal(str)
    openRecent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("Home { background: #e9ecf3; }")
        self.setAutoFillBackground(True)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(Hero())

        mid = QVBoxLayout()
        mid.setContentsMargins(26, 22, 14, 22)
        mid.setSpacing(14)
        head = QLabel("想做什么？")
        head.setStyleSheet("font-size: 22px; font-weight: bold; color: #1c2333;")
        mid.addWidget(head)
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (key, title, desc, color, ic) in enumerate(TILES):
            t = Tile(title, desc, color, ic)
            t.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            grid.addWidget(t, i // 3, i % 3)
        mid.addLayout(grid, 1)
        drop = QLabel("也可以把 PDF 或图片直接拖进这个窗口：拖一个文件打开，拖多个文件合并")
        drop.setAlignment(Qt.AlignCenter)
        drop.setStyleSheet("background: #dfe4ee; border: 2px dashed #a7b0c4; border-radius: 10px; padding: 16px;"
                           " color: #48536e; font-size: 14px;")
        mid.addWidget(drop)
        root.addLayout(mid, 1)

        right = QVBoxLayout()
        right.setContentsMargins(12, 22, 22, 22)
        lab = QLabel("最近打开")
        lab.setStyleSheet("font-size: 16px; font-weight: bold; color: #1c2333;")
        right.addWidget(lab)
        self.recent = QListWidget()
        self.recent.setFixedWidth(300)
        self.recent.setWordWrap(True)
        self.recent.setStyleSheet(
            "QListWidget { background: white; border: 1px solid #cdd3df; border-radius: 10px; outline: none; padding: 4px; }"
            "QListWidget::item { border-bottom: 1px solid #edf0f5; padding: 8px 8px; color: #1f2430; }"
            "QListWidget::item:hover { background: #eef3fd; }"
            "QListWidget::item:selected { background: #dbe6fb; color: #1f2430; }")
        self.recent.itemClicked.connect(lambda it: self.openRecent.emit(it.data(Qt.UserRole)))
        right.addWidget(self.recent, 1)
        b = primary(QPushButton("打开文件…"))
        b.setMinimumHeight(34)
        b.clicked.connect(lambda: self.action.emit("open"))
        right.addWidget(b)
        root.addLayout(right)

    def set_recent(self, paths):
        self.recent.clear()
        for p in paths:
            if not os.path.exists(p):
                continue
            it = QListWidgetItem(f"{os.path.basename(p)}\n{os.path.dirname(p)}")
            it.setData(Qt.UserRole, p)
            it.setToolTip(p)
            self.recent.addItem(it)
        if not self.recent.count():
            it = QListWidgetItem("还没有打开过文件")
            it.setFlags(Qt.NoItemFlags)
            self.recent.addItem(it)
