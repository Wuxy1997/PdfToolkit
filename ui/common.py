"""Theme, icons and small helpers shared by the windows."""
import os
import tempfile
import traceback

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (QApplication, QColorDialog, QFileDialog, QInputDialog, QLineEdit,
                               QMessageBox, QProgressDialog, QToolButton)

from core import fonts, i18n
from core.i18n import tr
from core.version import APP_NAME

INK = "#1c2333"        # ribbon / hero
INK2 = "#262f45"
PANEL = "#2d3340"      # thumbnail panel
CANVAS = "#565b66"
ACCENT = "#e5484d"
BLUE = "#3b82f6"
TEXT = "#1f2430"

ICONS = {
    "open": "E8E5", "save": "E74E", "saveas": "E792", "print": "E749", "undo": "E7A7", "redo": "E7A6",
    "zoomin": "E8A3", "zoomout": "E71F", "fit": "E9A6", "fitpage": "E740", "rotate": "E7AD",
    "delete": "E74D", "add": "E710", "text": "E8D2", "image": "EB9F", "edittext": "E70F",
    "highlight": "E7E6", "eraser": "E75C", "lock": "E72E", "unlock": "E785", "split": "E8C6",
    "merge": "EA3C", "page": "E7C3", "copy": "E8C8", "pen": "ED63", "sign": "EE56", "rect": "E739",
    "ellipse": "EA3A", "line": "E738", "arrow": "E8AD", "underline": "E8DC", "strike": "EDE0",
    "select": "E7C9", "compress": "E73F", "folder": "E8B7", "info": "E946", "list": "E8FD",
    "up": "E74A", "down": "E74B", "close": "E711", "home": "E80F", "date": "E787", "blank": "E8A5",
    "insert": "E8F4", "extract": "E8DE", "watermark": "EDA8", "number": "E71D", "export": "E78C",
    "images": "E8B9", "totext": "E8E3", "key": "E8D7", "redact": "E8D5", "recent": "E81C",
    "help": "E9CE", "sort": "E8CB", "check": "E73E", "more": "E712", "settings": "E713",
}

_icon_family = None


def icon_family():
    global _icon_family
    if _icon_family is None:
        fams = set(QFontDatabase.families())
        _icon_family = next((f for f in ("Segoe MDL2 Assets", "Segoe Fluent Icons") if f in fams), "")
    return _icon_family


def glyph_pixmap(name, color="#ffffff", size=24, mirror=False):
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.TextAntialiasing)
    if mirror:
        p.translate(size * dpr, 0)
        p.scale(-1, 1)
    f = QFont(icon_family())
    f.setPixelSize(int(size * dpr * 0.84))
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(QRect(0, 0, size * dpr, size * dpr), Qt.AlignCenter, chr(int(ICONS[name], 16)))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name, color="#ffffff", size=24, mirror=False, disabled="#6b7488"):
    ic = QIcon()
    ic.addPixmap(glyph_pixmap(name, color, size, mirror), QIcon.Normal)
    ic.addPixmap(glyph_pixmap(name, disabled, size, mirror), QIcon.Disabled)
    return ic


STYLE = f"""
* {{ font-family: @FONT@; font-size: 13px; }}
QMainWindow, QDialog {{ background: #f3f4f7; color: {TEXT}; }}
QToolBar {{ background: {INK}; border: none; padding: 3px 6px; spacing: 1px; }}
QToolBar#tools {{ background: {INK2}; border-top: 1px solid #36405a; padding: 2px 6px; }}
QToolBar#opts {{ background: #323c56; border-top: 1px solid #414b66; padding: 3px 10px; spacing: 4px; }}
QToolBar#opts QLabel#hint {{ color: #ffd88a; padding-left: 8px; }}
QToolBar#tools QToolButton {{ padding: 3px 5px; min-width: 40px; }}
QToolBar#main QToolButton {{ @MAINBTN@ }}
QToolBar QToolButton {{ color: #e8ebf3; background: transparent; border: 1px solid transparent;
    border-radius: 6px; padding: 4px 6px; min-width: 44px; font-size: 12px; }}
QToolBar QToolButton:hover {{ background: #36405a; }}
QToolBar QToolButton:pressed {{ background: #44506f; }}
QToolBar QToolButton:checked {{ background: {ACCENT}; color: white; }}
QToolBar QToolButton:disabled {{ color: #6b7488; }}
QToolBar QToolButton::menu-indicator {{ image: none; }}
QToolBar::separator {{ background: #3d4660; width: 1px; margin: 8px 5px; }}
QToolBar QLabel {{ color: #aeb6ca; padding: 0 4px; }}
QToolBar QComboBox, QToolBar QSpinBox, QToolBar QDoubleSpinBox {{ background: #121829; color: #f0f2f8;
    border: 1px solid #414b66; border-radius: 5px; padding: 3px 6px; min-height: 22px; }}
QToolBar QComboBox QAbstractItemView {{ background: white; color: {TEXT}; }}
QToolBar QToolButton#qt_toolbar_ext_button {{ background: {ACCENT}; min-width: 18px; padding: 2px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
QCheckBox::indicator:unchecked {{ image: url(@IND@/cb0.png); }}
QCheckBox::indicator:checked {{ image: url(@IND@/cb1.png); }}
QRadioButton::indicator:unchecked {{ image: url(@IND@/rb0.png); }}
QRadioButton::indicator:checked {{ image: url(@IND@/rb1.png); }}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{ image: url(@IND@/off.png); }}
QMenu {{ background: white; color: {TEXT}; border: 1px solid #c9cedb; padding: 5px; }}
QMenu::item {{ padding: 6px 28px 6px 14px; border-radius: 4px; }}
QMenu::item:selected {{ background: #e3ebfb; }}
QMenu::item:disabled {{ color: #9aa2b3; }}
QMenu::separator {{ height: 1px; background: #e1e4ec; margin: 5px 8px; }}
QStatusBar {{ background: {INK}; color: #c5cbda; }}
QStatusBar QLabel {{ color: #c5cbda; padding: 0 8px; }}
QStatusBar::item {{ border: none; }}
QPushButton {{ background: white; color: {TEXT}; border: 1px solid #c3c9d6; border-radius: 6px;
    padding: 6px 16px; min-height: 20px; }}
QPushButton:hover {{ background: #eef2fb; border-color: {BLUE}; }}
QPushButton:disabled {{ color: #a3a9b7; background: #eceef2; }}
QPushButton[primary="true"] {{ background: {ACCENT}; color: white; border: 1px solid #c53a3f; font-weight: bold; }}
QPushButton[primary="true"]:hover {{ background: #d13b40; }}
QPushButton[primary="true"]:disabled {{ background: #e9a9ab; border-color: #e9a9ab; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{ background: white; color: {TEXT};
    border: 1px solid #c3c9d6; border-radius: 5px; padding: 5px 7px; selection-background-color: {BLUE}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {BLUE}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ background: #eceef2; color: #9aa2b3; }}
QComboBox QAbstractItemView {{ background: white; color: {TEXT}; selection-background-color: #dbe6fb;
    selection-color: {TEXT}; }}
QGroupBox {{ border: 1px solid #d0d5e0; border-radius: 8px; margin-top: 12px; padding: 12px 10px 10px 10px;
    background: white; font-weight: bold; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #3a4257; }}
QGroupBox QLabel, QGroupBox QRadioButton, QGroupBox QCheckBox {{ font-weight: normal; }}
QLabel, QRadioButton, QCheckBox {{ color: {TEXT}; }}
QTableWidget, QListWidget#plain {{ background: white; color: {TEXT}; border: 1px solid #c9cedb;
    border-radius: 6px; gridline-color: #e6e9f0; alternate-background-color: #f6f8fc; }}
QTableWidget::item:selected, QListWidget#plain::item:selected {{ background: #dbe6fb; color: {TEXT}; }}
QHeaderView::section {{ background: #e9ecf3; color: #3a4257; border: none; border-right: 1px solid #d5d9e4;
    border-bottom: 1px solid #d5d9e4; padding: 6px 8px; font-weight: bold; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #9aa1b2; border-radius: 5px; min-height: 30px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #9aa1b2; border-radius: 5px; min-width: 30px; margin: 2px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QToolTip {{ background: #11151f; color: white; border: 1px solid #454e66; padding: 4px 7px; }}
QProgressBar {{ border: 1px solid #c3c9d6; border-radius: 5px; background: white; text-align: center; color: {TEXT}; }}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 4px; }}
"""


def _indicator_images():
    """Check box / radio button pictures for the style sheet. -> folder (forward slashes)."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QPen
    d = os.path.join(tempfile.gettempdir(), "PdfToolkit_ui")
    os.makedirs(d, exist_ok=True)
    for name in ("cb0", "cb1", "rb0", "rb1", "off"):
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        on = name.endswith("1")
        r = QRectF(2, 2, 28, 28)
        p.setPen(QPen(QColor(BLUE if on else "#8a93a8"), 2.4))
        p.setBrush(QColor(BLUE if on and name[0] == "c" else ("#e4e7ee" if name == "off" else "#ffffff")))
        if name[0] == "r":
            p.drawEllipse(r)
            if on:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(BLUE))
                p.drawEllipse(QRectF(9, 9, 14, 14))
        else:
            p.drawRoundedRect(r, 6, 6)
            if on:
                p.setPen(QPen(Qt.white, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPolyline([QPointF(8, 16.5), QPointF(14, 22), QPointF(24, 10)])
        p.end()
        pm.save(os.path.join(d, name + ".png"))
    return d.replace("\\", "/")


def apply_theme(app):
    """Light palette regardless of the Windows dark mode."""
    app.setStyle("Fusion")
    pal = QPalette()
    for role, col in ((QPalette.Window, "#f3f4f7"), (QPalette.WindowText, TEXT), (QPalette.Base, "#ffffff"),
                      (QPalette.AlternateBase, "#f6f8fc"), (QPalette.Text, TEXT), (QPalette.Button, "#ffffff"),
                      (QPalette.ButtonText, TEXT), (QPalette.Highlight, BLUE), (QPalette.HighlightedText, "#ffffff"),
                      (QPalette.ToolTipBase, "#11151f"), (QPalette.ToolTipText, "#ffffff"),
                      (QPalette.PlaceholderText, "#9aa2b3")):
        pal.setColor(role, QColor(col))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#9aa2b3"))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#9aa2b3"))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#9aa2b3"))
    app.setPalette(pal)
    family = ('"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei"' if i18n.lang() == "en"
              else '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"')
    # the whole top bar stays on one row at the default width; English labels are longer, so tighter still
    tight = "padding: 4px 3px; min-width: 38px;" if i18n.lang() == "en" else "padding: 4px 5px; min-width: 42px;"
    app.setStyleSheet(STYLE.replace("@IND@", _indicator_images()).replace("@FONT@", family).replace("@MAINBTN@", tight))


_qt_tr = None


def apply_language(app):
    """Qt's own texts (colour dialog, OK / Cancel of input boxes) and the interface font follow the language."""
    global _qt_tr
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    if _qt_tr is not None:
        app.removeTranslator(_qt_tr)
        _qt_tr = None
    if i18n.lang() == "zh":
        t = QTranslator(app)
        if t.load(QLocale(QLocale.Chinese, QLocale.China), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
            app.installTranslator(t)
            _qt_tr = t
    app.setApplicationName(tr(APP_NAME))
    apply_theme(app)


def pick_language(cfg, force=None):
    """--lang for this run, else what Settings saved, else the language of Windows."""
    from PySide6.QtCore import QLocale
    lang = force if force in i18n.LANGS else cfg.get("lang")
    if lang not in i18n.LANGS:
        lang = "zh" if QLocale.system().language() == QLocale.Chinese else "en"
    i18n.set_lang(lang)
    return lang


def fill_fonts(box):
    """Font names in the interface language; the item data is the key the PDF code uses."""
    for name in fonts.names():
        box.addItem(tr(name), name)


def pick_font(box, name):
    i = box.findData(name)
    if i >= 0:
        box.setCurrentIndex(i)


def primary(btn):
    btn.setProperty("primary", True)
    return btn


# ------------------------------------------------------------ message boxes

def _box(parent, kind, text, buttons=QMessageBox.Ok, default=None):
    box = QMessageBox(kind, tr(APP_NAME), text, buttons, parent)
    for b, label in ((QMessageBox.Ok, tr("确定")), (QMessageBox.Yes, tr("是")), (QMessageBox.No, tr("否")),
                     (QMessageBox.Cancel, tr("取消")), (QMessageBox.Save, tr("保存")), (QMessageBox.Discard, tr("不保存")),
                     (QMessageBox.Open, tr("打开"))):
        if box.button(b):
            box.button(b).setText(label)
    if default:
        box.setDefaultButton(default)
    return box.exec()


def info(parent, text):
    _box(parent, QMessageBox.Information, text)


def warn(parent, text):
    _box(parent, QMessageBox.Warning, text)


def ask(parent, text):
    return _box(parent, QMessageBox.Question, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes


def ask_save(parent, text):
    """-> "save", "discard" or "cancel"."""
    r = _box(parent, QMessageBox.Question, text,
             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
    return {QMessageBox.Save: "save", QMessageBox.Discard: "discard"}.get(r, "cancel")


def explain(exc):
    """A message a person can act on."""
    from core.pdfops import NeedPassword
    from core.ranges import RangeError
    if isinstance(exc, NeedPassword):
        return tr("密码不正确，无法打开这个文件。")
    if isinstance(exc, RangeError):
        return str(exc)
    if isinstance(exc, PermissionError):
        return tr("文件正被其他程序占用，或没有写入权限。\n请关闭正在打开它的程序（如浏览器、PDF阅读器）后再试，或换一个保存位置。")
    if isinstance(exc, FileNotFoundError):
        return tr("找不到文件：{path}", path=exc.filename or exc)
    if isinstance(exc, ValueError) and str(exc):
        return str(exc)
    return f"{type(exc).__name__}: {exc}"


def error(parent, what, exc):
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    warn(parent, tr("{what}失败。\n\n{why}", what=what, why=explain(exc)))


def get_password(parent, name, again=False):
    text = tr("“{name}” 有密码保护，请输入打开密码：", name=name)
    if again:
        text = tr("密码不正确，请重新输入。\n") + text
    pw, ok = QInputDialog.getText(parent, tr(APP_NAME), text, QLineEdit.Password)
    return pw if ok else None


def open_with_password(parent, path, opener):
    """opener(path, password) may raise NeedPassword: keep asking. -> result or None when cancelled."""
    import os

    from core.pdfops import NeedPassword
    pw, again = None, False
    while True:
        try:
            return opener(path, pw)
        except NeedPassword:
            pw = get_password(parent, os.path.basename(path), again)
            if pw is None:
                return None
            again = True


class Progress:
    """with Progress(parent, "合并中…") as p: op(progress=p.step)"""

    def __init__(self, parent, text):
        self.dlg = QProgressDialog(text, tr("取消"), 0, 100, parent)
        self.dlg.setWindowTitle(tr(APP_NAME))
        self.dlg.setWindowModality(Qt.WindowModal)
        self.dlg.setMinimumDuration(400)
        self.dlg.setAutoClose(False)
        self.dlg.setAutoReset(False)
        self.dlg.setValue(0)

    def step(self, i, n, _label=""):
        self.dlg.setMaximum(max(n, 1))
        self.dlg.setValue(i)
        QApplication.processEvents()
        return not self.dlg.wasCanceled()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.dlg.close()
        self.dlg.deleteLater()
        return False


PDF_FILTER = "PDF 文件 (*.pdf)"
IMG_FILTER = "图片 (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)"
ANY_FILTER = "PDF 和图片 (*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)"


def pick_open(parent, title, start, flt=PDF_FILTER, many=False):
    if many:
        files, _ = QFileDialog.getOpenFileNames(parent, title, start, tr(flt))
        return files
    f, _ = QFileDialog.getOpenFileName(parent, title, start, tr(flt))
    return f


def pick_save(parent, title, start, flt=PDF_FILTER):
    f, _ = QFileDialog.getSaveFileName(parent, title, start, tr(flt))
    return f


def pick_dir(parent, title, start):
    return QFileDialog.getExistingDirectory(parent, title, start)


class ColorButton(QToolButton):
    changed = Signal(str)
    PRESETS = ["#000000", "#d32f2f", "#1565c0", "#2e7d32", "#f9a825", "#ffeb3b", "#ff6f00", "#6a1b9a", "#ffffff"]

    def __init__(self, color="#d32f2f", parent=None, border="#e8ebf3"):
        super().__init__(parent)
        self._c = color
        self._border = border
        self.setFixedSize(34, 26)
        self.setToolTip(tr("颜色"))
        self.clicked.connect(self._pick)
        self._paint()

    def color(self):
        return self._c

    def set_color(self, c, emit=False):
        self._c = QColor(c).name()
        self._paint()
        if emit:
            self.changed.emit(self._c)

    def _paint(self):
        self.setStyleSheet(f"QToolButton {{ background: {self._c}; border: 2px solid {self._border}; border-radius: 5px;"
                           f" min-width: 0; padding: 0; }} QToolButton:hover {{ border-color: {BLUE}; }}")

    def _pick(self):
        dlg = QColorDialog(QColor(self._c), self.window())
        dlg.setWindowTitle(tr("选择颜色"))
        for i, c in enumerate(self.PRESETS):
            QColorDialog.setCustomColor(i, QColor(c))
        if dlg.exec():
            self.set_color(dlg.selectedColor().name(), emit=True)


def elide(text, n=46):
    return text if len(text) <= n else text[:n // 2 - 1] + "…" + text[-(n // 2):]


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
