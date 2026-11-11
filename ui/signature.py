"""Signatures: draw by hand, take from a photo/scan, or type. Saved as transparent PNG files."""
import math
import os
import time

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QSlider, QTabWidget, QVBoxLayout, QWidget)

from core import config, i18n
from core.i18n import tr

from . import common
from .common import primary

INKS = [("黑色", "#111111"), ("蓝黑", "#12255e"), ("蓝色", "#1a3fb5"), ("红色", "#c62828")]


# ------------------------------------------------------------ image helpers

def crop_to_ink(img, pad=6):
    """Cut away fully transparent borders."""
    img = img.convertToFormat(QImage.Format_ARGB32)
    alpha = img.convertToFormat(QImage.Format_Alpha8)
    w, h, bpl = alpha.width(), alpha.height(), alpha.bytesPerLine()
    data = bytes(alpha.constBits())
    zero = b"\x00"
    top = bottom = None
    left, right = w, -1
    for y in range(h):
        row = data[y * bpl:y * bpl + w]
        ls = row.lstrip(zero)
        if not ls:
            continue
        if top is None:
            top = y
        bottom = y
        left = min(left, w - len(ls))
        right = max(right, len(row.rstrip(zero)) - 1)
    if top is None:
        return None
    r = QRect(left, top, right - left + 1, bottom - top + 1).adjusted(-pad, -pad, pad, pad)
    return img.copy(r.intersected(img.rect()))


def remove_background(img, cutoff=200, max_side=1600):
    """Paper becomes transparent, ink stays. cutoff: gray level (0-255) from which a pixel counts as paper."""
    if max(img.width(), img.height()) > max_side:
        img = img.scaled(max_side, max_side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    rgb = img.convertToFormat(QImage.Format_RGB32)
    gray = rgb.convertToFormat(QImage.Format_Grayscale8)
    lo = max(cutoff - 70, 0)        # at or below: fully opaque
    table = []
    for g in range(256):
        a = 255 if g <= lo else (0 if g >= cutoff else int(255 * (cutoff - g) / (cutoff - lo)))
        table.append((255 << 24) | (a << 16) | (a << 8) | a)
    idx = gray.copy()
    idx.reinterpretAsFormat(QImage.Format_Indexed8)
    idx.setColorTable(table)
    alpha = idx.convertToFormat(QImage.Format_Grayscale8)
    out = rgb.convertToFormat(QImage.Format_ARGB32)
    out.setAlphaChannel(alpha)
    return crop_to_ink(out)


def text_signature(text, family, color="#111111", px=120):
    f = QFont(family)
    f.setPixelSize(px)
    fm = QFontMetricsF(f)
    w, h = int(fm.horizontalAdvance(text) + px), int(fm.height() + px * 0.4)
    img = QImage(max(w, 10), max(h, 10), QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, text)
    p.end()
    return crop_to_ink(img)


def saved():
    d = config.sig_dir()
    files = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".png")]
    return sorted(files, key=os.path.getmtime, reverse=True)


def store(img):
    name = time.strftime("sig_%Y%m%d_%H%M%S")
    path, n = os.path.join(config.sig_dir(), name + ".png"), 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(config.sig_dir(), f"{name}_{n}.png")
    img.save(path, "PNG")
    return path


def preview_pixmap(path_or_img, size=QSize(220, 90)):
    img = QImage(path_or_img) if isinstance(path_or_img, str) else path_or_img
    pm = QPixmap(size)
    pm.fill(Qt.white)
    if img is not None and not img.isNull():
        s = img.scaled(size - QSize(16, 12), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p = QPainter(pm)
        p.drawImage((size.width() - s.width()) // 2, (size.height() - s.height()) // 2, s)
        p.end()
    return pm


# ------------------------------------------------------------ hand drawing

class SignPad(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(520, 220)
        self.setCursor(Qt.CrossCursor)
        self.strokes = []       # each: list of (QPointF, width)
        self.color = INKS[0][1]
        self.base = 3.2
        self._t = None

    def clear(self):
        self.strokes = []
        self.update()
        self.changed.emit()

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            self.update()
            self.changed.emit()

    def empty(self):
        return not any(len(s) > 1 for s in self.strokes)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.strokes.append([(e.position(), self.base)])
            self._t = time.perf_counter()

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton) or not self.strokes:
            return
        s = self.strokes[-1]
        last, lw = s[-1]
        p = e.position()
        dist = math.hypot(p.x() - last.x(), p.y() - last.y())
        if dist < 1.5:
            return
        now = time.perf_counter()
        speed = dist / max(now - self._t, 1e-3)          # px per second
        self._t = now
        # fast strokes get thinner, like a real pen; smoothed so the line does not wobble
        target = self.base * max(0.45, min(1.25, 1.35 - speed / 1800.0))
        s.append((p, lw * 0.7 + target * 0.3))
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.changed.emit()

    def _draw(self, p, scale=1.0):
        p.setRenderHint(QPainter.Antialiasing)
        col = QColor(self.color)
        for s in self.strokes:
            if len(s) == 1:
                continue
            for (a, _), (b, w) in zip(s, s[1:]):
                p.setPen(QPen(col, w * scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawLine(QPointF(a.x() * scale, a.y() * scale), QPointF(b.x() * scale, b.y() * scale))

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.white)
        p.setPen(QPen(QColor("#c3c9d6"), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        y = int(self.height() * 0.72)
        p.setPen(QPen(QColor("#d5d9e4"), 1, Qt.DashLine))
        p.drawLine(24, y, self.width() - 24, y)
        if self.empty():
            p.setPen(QColor("#b3b9c7"))
            f = p.font()
            f.setPixelSize(15)
            p.setFont(f)
            p.drawText(self.rect().adjusted(0, 0, 0, -int(self.height() * 0.3)), Qt.AlignCenter,
                       tr("按住鼠标左键在这里签名"))
        self._draw(p)

    def image(self, scale=3.0):
        if self.empty():
            return None
        img = QImage(int(self.width() * scale), int(self.height() * scale), QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        self._draw(p, scale)
        p.end()
        return crop_to_ink(img, pad=10)


# ------------------------------------------------------------ dialog

class SignatureDialog(QDialog):
    def __init__(self, parent=None, start_dir=""):
        super().__init__(parent)
        self.setWindowTitle(tr("签名"))
        self.resize(900, 520)
        self.chosen = None
        self.start_dir = start_dir
        self._photo = None
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel(tr("<b>我的签名</b>（双击可直接使用）")))
        self.lst = QListWidget()
        self.lst.setObjectName("plain")
        self.lst.setIconSize(QSize(220, 90))
        self.lst.setSpacing(4)
        self.lst.setFixedWidth(262)
        self.lst.itemDoubleClicked.connect(lambda *_: self._use())
        left.addWidget(self.lst, 1)
        row = QHBoxLayout()
        self.btn_use = primary(QPushButton(tr("使用这个签名")))
        self.btn_use.clicked.connect(self._use)
        self.btn_del = QPushButton(tr("删除"))
        self.btn_del.clicked.connect(self._delete)
        row.addWidget(self.btn_use, 1)
        row.addWidget(self.btn_del)
        left.addLayout(row)
        root.addLayout(left)

        tabs = QTabWidget()
        tabs.addTab(self._tab_draw(), tr("手写签名"))
        tabs.addTab(self._tab_photo(), tr("从图片/照片导入"))
        tabs.addTab(self._tab_type(), tr("输入姓名生成"))
        root.addWidget(tabs, 1)
        self._fill()

    # -- saved list
    def _fill(self, select=None):
        self.lst.clear()
        for path in saved():
            pm = preview_pixmap(path)
            ic = QIcon()
            ic.addPixmap(pm, QIcon.Normal)
            ic.addPixmap(pm, QIcon.Selected)      # no blue tint over the selected signature
            it = QListWidgetItem(ic, "")
            it.setData(Qt.UserRole, path)
            it.setSizeHint(QSize(236, 98))
            self.lst.addItem(it)
            if path == select:
                self.lst.setCurrentItem(it)
        if self.lst.currentRow() < 0 and self.lst.count():
            self.lst.setCurrentRow(0)
        has = self.lst.count() > 0
        self.btn_use.setEnabled(has)
        self.btn_del.setEnabled(has)

    def _use(self):
        it = self.lst.currentItem()
        if it:
            self.chosen = it.data(Qt.UserRole)
            self.accept()

    def _delete(self):
        it = self.lst.currentItem()
        if it and common.ask(self, tr("删除这个签名？")):
            try:
                os.remove(it.data(Qt.UserRole))
            except OSError:
                pass
            self._fill()

    def _save(self, img, use=False):
        if img is None or img.isNull():
            common.warn(self, tr("还没有可保存的签名。"))
            return
        path = store(img)
        self._fill(select=path)
        if use:
            self.chosen = path
            self.accept()

    def _buttons(self, getter):
        row = QHBoxLayout()
        row.addStretch(1)
        b1 = QPushButton(tr("保存到签名库"))
        b1.clicked.connect(lambda: self._save(getter()))
        b2 = primary(QPushButton(tr("保存并使用")))
        b2.clicked.connect(lambda: self._save(getter(), use=True))
        row.addWidget(b1)
        row.addWidget(b2)
        return row

    @staticmethod
    def _ink_combo():
        c = QComboBox()
        for name, col in INKS:
            pm = QPixmap(16, 16)
            pm.fill(QColor(col))
            c.addItem(QIcon(pm), tr(name), col)
        return c

    # -- draw
    def _tab_draw(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.pad = SignPad()
        v.addWidget(self.pad, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("墨水")))
        ink = self._ink_combo()
        ink.currentIndexChanged.connect(lambda: (setattr(self.pad, "color", ink.currentData()), self.pad.update()))
        row.addWidget(ink)
        row.addWidget(QLabel(tr("粗细")))
        sl = QSlider(Qt.Horizontal)
        sl.setRange(15, 70)
        sl.setValue(32)
        sl.setFixedWidth(120)
        sl.valueChanged.connect(lambda x: setattr(self.pad, "base", x / 10))
        row.addWidget(sl)
        b = QPushButton(tr("撤销一笔"))
        b.clicked.connect(self.pad.undo)
        row.addWidget(b)
        b = QPushButton(tr("清空"))
        b.clicked.connect(self.pad.clear)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        v.addLayout(self._buttons(self.pad.image))
        return w

    # -- photo
    def _tab_photo(self):
        w = QWidget()
        v = QVBoxLayout(w)
        tip = QLabel(tr("在白纸上签名后拍照或扫描，选择图片后会自动去掉纸张背景，只保留笔迹。"))
        tip.setWordWrap(True)
        v.addWidget(tip)
        self.photo_view = QLabel(tr("尚未选择图片"))
        self.photo_view.setAlignment(Qt.AlignCenter)
        self.photo_view.setMinimumHeight(220)
        self.photo_view.setStyleSheet("background: #e9ecf3; border: 1px solid #c3c9d6; color: #7a8194;")
        v.addWidget(self.photo_view, 1)
        row = QHBoxLayout()
        b = QPushButton(tr("选择图片…"))
        b.clicked.connect(self._pick_photo)
        row.addWidget(b)
        row.addWidget(QLabel(tr("去背景强度")))
        self.cut = QSlider(Qt.Horizontal)
        self.cut.setRange(90, 245)
        self.cut.setValue(190)
        self.cut.setInvertedAppearance(True)
        self.cut.setFixedWidth(160)
        self.cut.valueChanged.connect(self._photo_update)
        row.addWidget(self.cut)
        row.addStretch(1)
        v.addLayout(row)
        v.addLayout(self._buttons(self._photo_result))
        return w

    def _pick_photo(self):
        f = common.pick_open(self, tr("选择签名图片"), self.start_dir, common.IMG_FILTER)
        if f:
            self.load_photo(f)

    def load_photo(self, path):
        img = QImage(path)
        if img.isNull():
            common.warn(self, tr("无法读取这张图片。"))
            return
        self._photo = img
        self._photo_update()

    def _photo_result(self):
        return remove_background(self._photo, self.cut.value()) if self._photo is not None else None

    def _photo_update(self):
        res = self._photo_result()
        if res is None:
            if self._photo is not None:
                self.photo_view.setText(tr("没有识别到笔迹，请调低“去背景强度”"))
                self.photo_view.setPixmap(QPixmap())
            return
        self.photo_view.setPixmap(preview_pixmap(res, QSize(520, 210)))

    # -- typed
    def _tab_type(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr("输入姓名"))
        row.addWidget(self.name, 1)
        self.face = QComboBox()
        have = set(QFontDatabase.families())
        faces = [(tr("行楷"), "STXingkai"), (tr("行楷"), "华文行楷"), (tr("楷体"), "KaiTi"), (tr("华文楷体"), "STKaiti"),
                 (tr("英文手写"), "Segoe Script"), ("Ink Free", "Ink Free"), ("Lucida Handwriting", "Lucida Handwriting"),
                 (tr("仿宋"), "FangSong"), (tr("雅黑"), "Microsoft YaHei")]
        if i18n.lang() == "en":             # names typed in English: handwriting faces first
            faces = faces[4:7] + faces[:4] + faces[7:]
        for label, fam in faces:
            if fam in have and self.face.findData(fam) < 0 and self.face.findText(label) < 0:
                self.face.addItem(label, fam)
        row.addWidget(self.face)
        self.type_ink = self._ink_combo()
        row.addWidget(self.type_ink)
        v.addLayout(row)
        self.type_view = QLabel()
        self.type_view.setAlignment(Qt.AlignCenter)
        self.type_view.setMinimumHeight(220)
        self.type_view.setStyleSheet("background: white; border: 1px solid #c3c9d6;")
        v.addWidget(self.type_view, 1)
        for sig in (self.name.textChanged, self.face.currentIndexChanged, self.type_ink.currentIndexChanged):
            sig.connect(self._type_update)
        v.addLayout(self._buttons(self._type_result))
        return w

    def _type_result(self):
        t = self.name.text().strip()
        return text_signature(t, self.face.currentData(), self.type_ink.currentData()) if t else None

    def _type_update(self, *_):
        res = self._type_result()
        self.type_view.setPixmap(preview_pixmap(res, QSize(520, 210)) if res is not None else QPixmap())
