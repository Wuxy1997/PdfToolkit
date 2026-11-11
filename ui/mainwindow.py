"""Main window: ribbon, thumbnails, page view and the glue between them."""
import os
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QImage, QKeySequence, QPainter
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMainWindow, QMenu, QSizePolicy,
                               QSpinBox, QStackedWidget, QToolBar, QToolButton, QVBoxLayout, QWidget)

from core import config, fonts, i18n, pdfops
from core.docmodel import Doc
from core.i18n import tr
from core.version import APP_NAME, VERSION

from . import common, dialogs, signature
from .common import ColorButton, Progress, icon
from .helptext import HELP
from .home import Home
from .settings import SettingsDialog
from .thumbs import Thumbs
from .view import PdfView, image_bytes

TOOLS = [  # key, label, icon, tip
    ("select", "浏览", "select", "浏览 / 拖动页面（Esc）"),
    None,
    ("text", "加文字", "text", "在页面上点击，输入新的文字"),
    ("edittext", "改文字", "edittext", "点击页面上已有的一行文字进行修改或删除"),
    ("image", "图片", "image", "插入图片"),
    ("sign", "签名", "sign", "手写 / 图片 / 输入姓名生成签名，放到页面上"),
    ("date", "日期", "date", "插入今天的日期"),
    None,
    ("highlight", "高亮", "highlight", "拖过文字加高亮"),
    ("underline", "下划线", "underline", "拖过文字加下划线"),
    ("strike", "删除线", "strike", "拖过文字加删除线"),
    None,
    ("pen", "画笔", "pen", "自由涂画"),
    ("line", "直线", "line", "画直线（按住 Shift 画水平/垂直线）"),
    ("arrow", "箭头", "arrow", "画箭头"),
    ("rect", "方框", "rect", "画方框（按住 Shift 画正方形）"),
    ("ellipse", "圆圈", "ellipse", "画椭圆（按住 Shift 画正圆）"),
    None,
    ("erase", "擦除", "eraser", "框选区域，彻底擦掉其中的内容并涂白"),
    ("redact", "涂黑", "redact", "框选区域，彻底删除其中的内容并涂黑（用于遮盖敏感信息）"),
]
COLOR_KEY = {"text": "text_color", "date": "text_color", "highlight": "hl_color"}


class MainWindow(QMainWindow):
    current = None          # the window in use (a language switch replaces it)

    def __init__(self, cfg):
        super().__init__()
        MainWindow.current = self
        self.cfg = cfg
        self.dm = None
        self.acts = {}
        self.doc_acts = []
        self.resize(1360, 860)
        self.setMinimumSize(900, 560)
        self.setAcceptDrops(True)

        self.home = Home()
        self.home.action.connect(self._home_action)
        self.home.openRecent.connect(lambda p: p and self.open_file(p))
        self.thumbs = Thumbs()
        self.view = PdfView()
        editor = QWidget()
        h = QHBoxLayout(editor)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        side = QWidget()
        side.setStyleSheet(f"background: {common.PANEL};")
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        self.side_title = QLabel(tr("页面"))
        self.side_title.setStyleSheet("color: #e8ebf3; font-weight: bold; padding: 8px 12px; background: #232833;")
        sv.addWidget(self.side_title)
        sv.addWidget(self.thumbs, 1)
        tip = QLabel(tr("Ctrl/Shift 多选 · 拖动排序 · 右键更多"))
        tip.setStyleSheet("color: #8b93a7; font-size: 11px; padding: 6px 8px; background: #232833;")
        tip.setAlignment(Qt.AlignCenter)
        tip.setWordWrap(i18n.lang() == "en")       # the English line is longer than the panel
        sv.addWidget(tip)
        h.addWidget(side)
        h.addWidget(self.view, 1)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.home)
        self.stack.addWidget(editor)
        self.setCentralWidget(self.stack)

        self._build_main_bar()
        self._build_tool_bar()
        self._build_status()

        self.thumbs.pageActivated.connect(self.view.goto_page)
        self.thumbs.reordered.connect(self._reorder)
        self.thumbs.menuRequested.connect(self._thumb_menu)
        self.thumbs.deletePressed.connect(self.delete_pages)
        self.thumbs.itemSelectionChanged.connect(self._update_ui)
        self.view.pageChanged.connect(self._page_changed)
        self.view.zoomChanged.connect(self._zoom_changed)
        self.view.edited.connect(self._edited)
        self.view.failed.connect(lambda what, exc: common.error(self, what, exc))
        self.view.toolChanged.connect(self._tool_changed)
        self.view.lineClicked.connect(self._edit_line)
        self.view.hint.connect(self._hint)
        self.view.set_opts(color=cfg["color"], text_color=cfg["text_color"], width=cfg["line_width"],
                           font=cfg["font"] if cfg["font"] in fonts.names() else fonts.names()[0],
                           size=cfg["font_size"])
        self._sync_opts()
        self.home.set_recent(cfg.get("recent", []))
        self._update_ui()

    # ------------------------------------------------------------ bars
    def _act(self, key, text, ic, slot, shortcut=None, tip=None, doc=True, mirror=False):
        a = QAction(icon(ic, mirror=mirror), text, self)
        a.triggered.connect(lambda _=False: slot())
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.setToolTip((tip or text) + (tr("（{key}）", key=shortcut) if shortcut else ""))
        self.acts[key] = a
        if doc:
            self.doc_acts.append(a)
        return a

    def _bar(self, name):
        tb = QToolBar(name, self)
        tb.setObjectName(name)
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        tb.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(tb)
        return tb

    @staticmethod
    def _no_squeeze(tb):
        """Buttons keep their full width; what does not fit goes into the toolbar's » menu."""
        for b in tb.findChildren(QToolButton):
            if b.objectName() == "qt_toolbar_ext_button":
                b.setIcon(icon("more"))
                b.setToolTip(tr("更多"))
                continue
            b.ensurePolished()
            b.setMinimumWidth(b.sizeHint().width())

    def _menu_button(self, tb, text, ic, items):
        b = QToolButton()
        b.setText(text + " ▾")
        b.setIcon(icon(ic))
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(b)
        for it in items:
            if it is None:
                m.addSeparator()
            else:
                m.addAction(it)
        b.setMenu(m)
        tb.addWidget(b)
        self.doc_widgets.append(b)
        return b

    def _build_main_bar(self):
        self.doc_widgets = []
        tb = self._bar("main")
        A = self._act
        tb.addAction(A("open", tr("打开"), "open", self.open_dialog, "Ctrl+O", doc=False))
        tb.addAction(A("save", tr("保存"), "save", self.save, "Ctrl+S"))
        tb.addAction(A("saveas", tr("另存为"), "saveas", self.save_as, "Ctrl+Shift+S"))
        tb.addAction(A("print", tr("打印"), "print", self.print_doc, "Ctrl+P"))
        tb.addAction(A("close", tr("关闭"), "close", self.close_doc, "Ctrl+W", tr("关闭当前文档，回到首页")))
        tb.addSeparator()
        tb.addAction(A("undo", tr("撤销"), "undo", self.undo, "Ctrl+Z"))
        tb.addAction(A("redo", tr("重做"), "redo", self.redo, "Ctrl+Y"))
        tb.addSeparator()
        tb.addAction(A("merge", tr("合并"), "merge", self.merge, tip=tr("把多个 PDF / 图片合并成一个"), doc=False))
        tb.addAction(A("split", tr("拆分"), "split", self.split, tip=tr("把 PDF 拆成多个文件"), doc=False))
        tb.addSeparator()
        ins_file = A("ins_file", tr("从文件插入页面…"), "insert", self.insert_file)
        ins_blank = A("ins_blank", tr("插入空白页"), "blank", self.insert_blank)
        self._menu_button(tb, tr("插入"), "insert", [ins_file, ins_blank])
        tb.addAction(A("rot_l", tr("左转"), "rotate", lambda: self.rotate(-90), tip=tr("选中的页面逆时针旋转 90°"), mirror=True))
        tb.addAction(A("rot_r", tr("右转"), "rotate", lambda: self.rotate(90), tip=tr("选中的页面顺时针旋转 90°")))
        tb.addAction(A("delete", tr("删除页"), "delete", self.delete_pages, tip=tr("删除选中的页面")))
        tb.addAction(A("extract", tr("提取"), "extract", self.extract_pages, tip=tr("把选中的页面另存为一个新 PDF")))
        tb.addSeparator()
        tb.addAction(A("watermark", tr("水印"), "watermark", self.watermark))
        tb.addAction(A("number", tr("页码"), "number", self.page_numbers))
        tb.addAction(A("encrypt", tr("加密"), "lock", self.encrypt, tip=tr("设置或移除打开密码")))
        tb.addAction(A("compress", tr("压缩"), "compress", self.compress, tip=tr("缩小文件体积")))
        ex_img = A("ex_img", tr("导出为图片…"), "images", self.export_images)
        ex_txt = A("ex_txt", tr("导出文字 (.txt)…"), "totext", self.export_text)
        self._menu_button(tb, tr("导出"), "export", [ex_img, ex_txt])
        sp = QWidget()
        sp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sp.setStyleSheet("background: transparent;")
        tb.addWidget(sp)
        tb.addAction(A("settings", tr("设置"), "settings", self.show_settings, doc=False))
        tb.addAction(A("help", tr("帮助"), "help", self.show_help, "F1", doc=False))
        self._no_squeeze(tb)

    def _build_tool_bar(self):
        self.addToolBarBreak()
        tb = self.tb_tools = self._bar("tools")
        tb.setIconSize(QSize(20, 20))
        self.tool_group = QActionGroup(self)
        self.tool_acts = {}
        for spec in TOOLS:
            if spec is None:
                tb.addSeparator()
                continue
            key, label, ic, tip = spec
            a = QAction(icon(ic, size=20), tr(label), self)
            a.setToolTip(tr(tip))
            a.setCheckable(True)
            a.triggered.connect(lambda _=False, k=key: self.pick_tool(k))
            self.tool_group.addAction(a)
            self.tool_acts[key] = a
            self.doc_acts.append(a)
            tb.addAction(a)
        self.tool_acts["select"].setChecked(True)
        self._no_squeeze(tb)
        self.addToolBarBreak()
        tb = self.tb_opts = self._bar("opts")
        self.lbl_color = QLabel(tr("颜色"))
        tb.addWidget(self.lbl_color)
        self.color = ColorButton(self.cfg["color"])
        self.color.changed.connect(self._color_changed)
        tb.addWidget(self.color)
        tb.addWidget(QLabel(tr("线宽")))
        self.width = QDoubleSpinBox()
        self.width.setRange(0.3, 30)
        self.width.setSingleStep(0.5)
        self.width.setDecimals(1)
        self.width.setValue(self.cfg["line_width"])
        self.width.valueChanged.connect(lambda v: self.view.set_opts(width=v))
        tb.addWidget(self.width)
        tb.addWidget(QLabel(tr("字体")))
        self.font_box = QComboBox()
        common.fill_fonts(self.font_box)
        self.font_box.currentIndexChanged.connect(lambda _: self.view.set_opts(font=self.font_box.currentData()))
        tb.addWidget(self.font_box)
        tb.addWidget(QLabel(tr("字号")))
        self.size = QSpinBox()
        self.size.setRange(5, 200)
        self.size.valueChanged.connect(lambda v: self.view.set_opts(size=v))
        tb.addWidget(self.size)
        tb.addSeparator()
        self.lbl_hint = _Hint()
        self.lbl_hint.setObjectName("hint")
        tb.addWidget(self.lbl_hint)
        self.doc_widgets += [self.color, self.width, self.font_box, self.size]

    def _build_status(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self.lbl_path = QLabel("")
        sb.addWidget(self.lbl_path, 1)
        nav = QWidget()
        nh = QHBoxLayout(nav)
        nh.setContentsMargins(0, 0, 0, 0)
        nh.setSpacing(4)
        nh.addWidget(QLabel(tr("第")))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setFixedWidth(70)
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.valueChanged.connect(lambda v: self.view.goto_page(v - 1))
        nh.addWidget(self.page_spin)
        self.lbl_pages = QLabel(tr("/ 0 页"))
        nh.addWidget(self.lbl_pages)
        sb.addPermanentWidget(nav)
        self.lbl_size = QLabel("")
        sb.addPermanentWidget(self.lbl_size)
        zw = QWidget()
        zh = QHBoxLayout(zw)
        zh.setContentsMargins(0, 0, 6, 0)
        zh.setSpacing(2)
        for key, ic, tip, fn in (("zoomout", "zoomout", tr("缩小"), lambda: self.view.set_zoom(self.view.zoom / 1.2)),
                                 ("zoomin", "zoomin", tr("放大"), lambda: self.view.set_zoom(self.view.zoom * 1.2))):
            b = QToolButton()
            b.setIcon(icon(ic, "#e8ebf3", 18))
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(fn)
            setattr(self, "btn_" + key, b)
        self.zoom_box = QComboBox()
        self.zoom_box.setEditable(True)
        self.zoom_box.setFixedWidth(96)
        for z in (tr("适合宽度"), tr("整页"), "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%"):
            self.zoom_box.addItem(z)
        self.zoom_box.setInsertPolicy(QComboBox.NoInsert)
        self.zoom_box.activated.connect(lambda *_: self._zoom_picked())
        self.zoom_box.lineEdit().returnPressed.connect(self._zoom_picked)
        zh.addWidget(self.btn_zoomout)
        zh.addWidget(self.zoom_box)
        zh.addWidget(self.btn_zoomin)
        sb.addPermanentWidget(zw)
        for seq, fn in (("Ctrl+0", self.view.fit_width), ("Ctrl+=", lambda: self.view.set_zoom(self.view.zoom * 1.2)),
                        ("Ctrl+-", lambda: self.view.set_zoom(self.view.zoom / 1.2))):
            a = QAction(self)
            a.setShortcut(QKeySequence(seq))
            a.triggered.connect(lambda _=False, f=fn: f())
            self.addAction(a)

    # ------------------------------------------------------------ state
    def _hint(self, text):
        self.lbl_hint.setText(text)

    def _update_ui(self):
        has = self.dm is not None
        self.tb_tools.setVisible(has)
        self.tb_opts.setVisible(has)
        for a in self.doc_acts:
            a.setEnabled(has)
        for w in self.doc_widgets:
            w.setEnabled(has)
        for w in (self.page_spin, self.zoom_box, self.btn_zoomin, self.btn_zoomout):
            w.setEnabled(has)
        if has:
            self.acts["undo"].setEnabled(self.dm.can_undo())
            self.acts["redo"].setEnabled(self.dm.can_redo())
            self.acts["delete"].setEnabled(self.dm.n > 1)
            self.acts["encrypt"].setIcon(icon("lock" if self.dm.encrypt else "unlock"))
            n = self.dm.n
            self.page_spin.blockSignals(True)
            self.page_spin.setRange(1, n)
            self.page_spin.setValue(self.view.current_page() + 1)
            self.page_spin.blockSignals(False)
            self.lbl_pages.setText(tr("/ {n} 页", n=n))
            sel = len(self.thumbs.selected())
            self.side_title.setText(tr("页面　共 {n} 页", n=n) + (tr(" · 已选 {n}", n=sel) if sel > 1 else ""))
            size = ""
            if self.dm.path and os.path.exists(self.dm.path):
                size = common.human_size(os.path.getsize(self.dm.path))
            self.lbl_size.setText((tr("已加密 · ") if self.dm.encrypt else "") + size)
            self.lbl_path.setText(common.elide(self.dm.path, 90) if self.dm.path else tr("尚未保存到文件"))
            self.setWindowTitle(f"{'● ' if self.dm.dirty else ''}{self.dm.name} - {tr(APP_NAME)}")
        else:
            self.lbl_pages.setText(tr("/ 0 页"))
            self.lbl_size.setText("")
            self.lbl_path.setText(tr("全部在本机处理，文件不会上传"))
            self.setWindowTitle(f"{tr(APP_NAME)} {VERSION}")

    def _page_changed(self, i):
        self.thumbs.set_current(i)
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(i + 1)
        self.page_spin.blockSignals(False)

    def _zoom_changed(self, z):
        self.zoom_box.setEditText(f"{round(z * 100)}%")

    def _zoom_picked(self):
        t = self.zoom_box.currentText().strip()
        if t == tr("适合宽度"):
            self.view.fit_width()
        elif t == tr("整页"):
            self.view.fit_page()
        else:
            try:
                self.view.set_zoom(float(t.rstrip("%")) / 100)
            except ValueError:
                pass
        self._zoom_changed(self.view.zoom)
        self.view.setFocus()

    def _edited(self, pages):
        self.thumbs.reload(pages)
        self._update_ui()

    def _refresh_all(self, pages=None, select=None):
        self.view.refresh(pages)
        self.thumbs.reload(pages, select)
        self._update_ui()

    def targets(self):
        sel = self.thumbs.selected()
        return sel if sel else [self.view.current_page()]

    def edit(self, what, fn, pages=None, select=None):
        """Run fn(doc) as one undoable step."""
        if not self.view.commit_float():
            return False
        try:
            with self.dm.edit() as d:
                fn(d)
        except Exception as exc:
            common.error(self, what, exc)
            self._refresh_all()
            return False
        self._refresh_all(pages, select)
        return True

    # ------------------------------------------------------------ tools
    def _sync_opts(self):
        o = self.view.opts
        self.color.set_color(o[COLOR_KEY.get(self.view.tool, "color")])
        for w, v in ((self.width, o["width"]), (self.size, o["size"])):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)
        self.font_box.blockSignals(True)
        common.pick_font(self.font_box, o["font"])
        self.font_box.blockSignals(False)

    def _color_changed(self, c):
        tool = self.view.tool
        if self.view.has_float() and tool == "select":
            tool = "text"
        self.view.set_opts(**{COLOR_KEY.get(tool, "color"): c})

    def _tool_changed(self, name):
        key = name if name in self.tool_acts else None
        if name == "place":
            key = self._placing
        if key:
            self.tool_acts[key].setChecked(True)
        self._sync_opts()
        tips = {"text": tr("在页面上点击要加文字的位置"), "edittext": tr("把鼠标移到文字上，出现蓝框后点击修改"),
                "highlight": tr("按住鼠标拖过要高亮的文字"), "underline": tr("按住鼠标拖过要加下划线的文字"),
                "strike": tr("按住鼠标拖过要加删除线的文字"), "erase": tr("框选要擦除的区域（内容会被真正删除并涂白）"),
                "redact": tr("框选要涂黑的区域（内容会被真正删除）"), "pen": tr("按住鼠标自由涂画"),
                "select": ""}
        if name in tips:
            self._hint(tips[name])
        elif name in ("line", "arrow", "rect", "ellipse"):
            self._hint(tr("按住鼠标拖动绘制；按住 Shift 可画水平线 / 正方形 / 正圆"))

    _placing = "image"

    def pick_tool(self, key):
        if self.dm is None:
            return
        if key == "image":
            return self._place_image()
        if key == "sign":
            return self._place_sign()
        if key == "date":
            self.view.set_tool("text")
            c = self.view.mapToScene(self.view.viewport().rect().center())
            page = self.view.page_at(c) or self.view._nearest_page(c)
            pos = QPointF(max(page.pos().x() + 20, min(c.x() - 40, page.pos().x() + page.w - 120)),
                          max(page.pos().y() + 20, min(c.y(), page.pos().y() + page.h - 40)))
            self.view.new_text(pos, time.strftime("%Y-%m-%d"))
            return
        self.view.set_tool(key)

    def _back_to_select(self):
        self.tool_acts[self.view.tool if self.view.tool in self.tool_acts else "select"].setChecked(True)

    def _place_image(self):
        f = common.pick_open(self, tr("选择要插入的图片"), self.cfg.get("last_dir", ""), common.IMG_FILTER)
        if not f:
            return self._back_to_select()
        img = QImage(f)
        if img.isNull():
            common.warn(self, tr("无法读取这张图片。"))
            return self._back_to_select()
        self.cfg["last_dir"] = os.path.dirname(f)
        if os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg"):
            with open(f, "rb") as fh:
                data = fh.read()
        else:
            data = image_bytes(img)
        self._placing = "image"
        self.view.place_image(img, data, min(img.width() * 0.75, 320))

    def _place_sign(self):
        if not self.view.commit_float():
            return
        dlg = signature.SignatureDialog(self, self.cfg.get("last_dir", ""))
        if not dlg.exec() or not dlg.chosen:
            return self._back_to_select()
        self.use_signature(dlg.chosen)

    def use_signature(self, path):
        img = QImage(path)
        if img.isNull():
            return common.warn(self, tr("无法读取这个签名。"))
        with open(path, "rb") as fh:
            data = fh.read()
        self._placing = "sign"
        self.view.place_image(img, data, self.cfg.get("sig_width", 140))

    def _edit_line(self, index, line):
        dlg = dialogs.ReplaceTextDialog(self, line)
        if dlg.exec():
            p = dlg.params()
            self.edit(tr("修改文字"), lambda d: pdfops.replace_text(d[index], line, **p), {index})

    # ------------------------------------------------------------ files
    def _home_action(self, key):
        if key == "open":
            self.open_dialog()
        elif key in ("merge", "images"):
            self.merge()
        elif key == "split":
            self.split()
        elif key == "sign":
            if self.open_dialog():
                self.pick_tool("sign")
        elif key == "blank":
            if self.maybe_save():
                self.set_doc(Doc.blank())

    def open_dialog(self):
        f = common.pick_open(self, tr("打开 PDF 或图片"), self.cfg.get("last_dir", ""), common.ANY_FILTER)
        return bool(f) and self.open_file(f)

    def open_file(self, path):
        if not os.path.exists(path):
            common.warn(self, tr("找不到文件：\n{path}", path=path))
            return False
        if not self.maybe_save():
            return False
        try:
            dm = common.open_with_password(self, path, Doc.open)
        except Exception as exc:
            common.error(self, tr("打开文件"), exc)
            return False
        if dm is None:
            return False
        if dm.n == 0:
            common.warn(self, tr("这个文件里没有页面。"))
            return False
        self.set_doc(dm)
        if dm.path:
            config.add_recent(self.cfg, dm.path)
        return True

    def set_doc(self, dm):
        old, self.dm = self.dm, dm
        self.view.set_tool("select")
        self.view.set_doc(dm)
        self.thumbs.set_doc(dm)
        if old is not None:
            old.close()
        self.stack.setCurrentIndex(1 if dm else 0)
        if dm:
            self.view.fit_width()
            if self.view.zoom > 1.6:
                self.view.set_zoom(1.6)
            self.view.goto_page(0)
            self._zoom_changed(self.view.zoom)
            self.view.setFocus()
        else:
            self.home.set_recent(self.cfg.get("recent", []))
        self._hint("")
        self._update_ui()

    def maybe_save(self):
        """False when the user cancelled."""
        if self.dm is None:
            return True
        if not self.view.commit_float():
            return False
        if not self.dm.dirty:
            return True
        r = common.ask_save(self, tr("“{name}” 有尚未保存的修改，要保存吗？", name=self.dm.name))
        if r == "cancel":
            return False
        return self.save() if r == "save" else True

    def close_doc(self):
        if self.dm is not None and self.maybe_save():
            self.set_doc(None)

    def save(self):
        if self.dm is None or not self.view.commit_float():
            return False
        if not self.dm.path:
            return self.save_as()
        return self._save_to(self.dm.path)

    def save_as(self):
        if self.dm is None or not self.view.commit_float():
            return False
        start = self.dm.path or getattr(self.dm, "suggest", None) or os.path.join(self.cfg.get("last_dir", ""), self.dm.name)
        f = common.pick_save(self, tr("另存为"), start)
        if not f:
            return False
        if not f.lower().endswith(".pdf"):
            f += ".pdf"
        return self._save_to(f)

    def _save_to(self, path):
        try:
            self.dm.save(path)
        except Exception as exc:
            common.error(self, tr("保存"), exc)
            return False
        config.add_recent(self.cfg, path)
        self._hint(tr("已保存：{path}", path=path))
        self._update_ui()
        return True

    def print_doc(self):
        if not self.view.commit_float():
            return
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(self.dm.name)
        dlg = QPrintDialog(printer, self)
        dlg.setMinMax(1, self.dm.n)
        dlg.setOption(QPrintDialog.PrintPageRange, True)
        if not dlg.exec():
            return
        first, last = 1, self.dm.n
        if printer.printRange() == QPrinter.PageRange and printer.fromPage() > 0:
            first, last = printer.fromPage(), min(printer.toPage() or self.dm.n, self.dm.n)
        dpi = min(printer.resolution(), 300)
        p = QPainter()
        if not p.begin(printer):
            return common.warn(self, tr("无法开始打印。"))
        try:
            with Progress(self, tr("正在打印…")) as prog:
                for k, i in enumerate(range(first - 1, last)):
                    if not prog.step(k, last - first + 1):
                        break
                    if k:
                        printer.newPage()
                    pix = self.dm.doc[i].get_pixmap(dpi=dpi, alpha=False)
                    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                    area = QRectF(p.viewport())
                    s = min(area.width() / img.width(), area.height() / img.height())
                    w, h = img.width() * s, img.height() * s
                    p.drawImage(QRectF((area.width() - w) / 2, (area.height() - h) / 2, w, h), img)
        finally:
            p.end()

    # ------------------------------------------------------------ pages
    def rotate(self, delta):
        t = self.targets()
        self.edit(tr("旋转页面"), lambda d: pdfops.rotate(d, t, delta), set(t), t)

    def delete_pages(self):
        if self.dm is None:
            return
        t = self.targets()
        if len(t) >= self.dm.n:
            return common.warn(self, tr("不能删除全部页面，至少要保留一页。"))
        if len(t) > 1 and not common.ask(self, tr("删除选中的 {n} 页？（可以撤销）", n=len(t))):
            return
        self.edit(tr("删除页面"), lambda d: pdfops.delete(d, t), None, [])

    def extract_pages(self):
        if not self.view.commit_float():
            return
        t = self.targets()
        base = self.dm.path or os.path.join(self.cfg.get("last_dir", ""), self.dm.name)
        default = tr("{stem}_第{pages}页.pdf", stem=os.path.splitext(base)[0],
                     pages=pdfops.safe_name(_ranges_text(t), 30))
        f = common.pick_save(self, tr("把 {n} 页另存为", n=len(t)), default)
        if not f:
            return
        try:
            pdfops.extract(self.dm.doc, t, f if f.lower().endswith(".pdf") else f + ".pdf")
        except Exception as exc:
            return common.error(self, tr("提取页面"), exc)
        self._hint(tr("已提取 {n} 页到：{path}", n=len(t), path=f))

    def insert_file(self, at=None):
        files = common.pick_open(self, tr("选择要插入的 PDF 或图片"), self.cfg.get("last_dir", ""), common.ANY_FILTER, many=True)
        if not files:
            return
        self.cfg["last_dir"] = os.path.dirname(files[0])
        self.insert_paths(files, at)

    def insert_paths(self, files, at=None):
        at = (max(self.targets()) + 1) if at is None else at
        opened = []
        for f in files:
            box = {}

            def opener(p, pw):
                box["pw"] = pw
                return pdfops.page_count(p, pw)
            try:
                n = common.open_with_password(self, f, opener)
            except Exception as exc:
                common.error(self, tr("读取 {name}", name=os.path.basename(f)), exc)
                return
            if n is None:
                return
            opened.append((f, box.get("pw"), n))
        total = sum(n for _, _, n in opened)

        def run(d):
            pos = at
            for f, pw, _ in opened:
                pos += pdfops.insert_file(d, f, pos, pw)
        if self.edit(tr("插入页面"), run, None, list(range(at, at + total))):
            self.view.goto_page(at)
            self._hint(tr("已在第 {at} 页之后插入 {n} 页", at=at, n=total))

    def insert_blank(self, at=None):
        cur = self.view.current_page()
        at = (max(self.targets()) + 1) if at is None else at
        r = self.dm.doc[min(cur, self.dm.n - 1)].rect
        if self.edit(tr("插入空白页"), lambda d: pdfops.insert_blank(d, at, r.width, r.height), None, [at]):
            self.view.goto_page(at)

    def _reorder(self, order):
        cur = self.view.current_page()
        was = set(self.thumbs.selected())
        sel = [new for new, old in enumerate(order) if old in was]
        if not self.edit(tr("调整页面顺序"), lambda d: pdfops.reorder(d, order), None, sel):
            return
        self._hint(tr("页面顺序已调整（Ctrl+Z 可撤销）"))
        if cur in order:
            self.view.goto_page(order.index(cur))

    def _thumb_menu(self, gpos):
        if self.dm is None:
            return
        t = self.targets()
        m = QMenu(self)
        title = m.addAction(tr("第 {pages} 页", pages=_ranges_text(t)) if len(t) <= 6 else tr("已选 {n} 页", n=len(t)))
        title.setEnabled(False)
        m.addSeparator()
        for key in ("rot_l", "rot_r", "delete", "extract"):
            a = m.addAction(icon(*{"rot_l": ("rotate", "#3a4257"), "rot_r": ("rotate", "#3a4257"),
                                   "delete": ("delete", "#c62828"), "extract": ("extract", "#3a4257")}[key],
                                 mirror=(key == "rot_l")),
                            {"rot_l": tr("向左旋转 90°"), "rot_r": tr("向右旋转 90°"), "delete": tr("删除"), "extract": tr("提取为新文件…")}[key])
            a.triggered.connect(lambda _=False, k=key: self.acts[k].trigger())
            a.setEnabled(self.acts[key].isEnabled())
        m.addSeparator()
        first, last = min(t), max(t)
        m.addAction(tr("在前面插入文件…")).triggered.connect(lambda: self.insert_file(first))
        m.addAction(tr("在后面插入文件…")).triggered.connect(lambda: self.insert_file(last + 1))
        m.addAction(tr("在前面插入空白页")).triggered.connect(lambda: self.insert_blank(first))
        m.addAction(tr("在后面插入空白页")).triggered.connect(lambda: self.insert_blank(last + 1))
        m.addSeparator()
        m.addAction(tr("移到最前")).triggered.connect(lambda: self._move_to(t, 0))
        m.addAction(tr("移到最后")).triggered.connect(lambda: self._move_to(t, self.dm.n))
        m.addSeparator()
        m.addAction(tr("导出为图片…")).triggered.connect(self.export_images)
        m.addAction(tr("全选")).triggered.connect(self.thumbs.selectAll)
        m.exec(gpos)

    def _move_to(self, t, where):
        rest = [i for i in range(self.dm.n) if i not in set(t)]
        order = (t + rest) if where == 0 else (rest + t)
        if order == list(range(self.dm.n)):
            return
        start = 0 if where == 0 else len(rest)
        if self.edit(tr("移动页面"), lambda d: pdfops.reorder(d, order), None, list(range(start, start + len(t)))):
            self.view.goto_page(start)

    # ------------------------------------------------------------ whole-document tools
    def undo(self):
        if self.dm and self.view.commit_float() and self.dm.can_undo():
            self.dm.undo()
            self._refresh_all()

    def redo(self):
        if self.dm and self.view.commit_float() and self.dm.can_redo():
            self.dm.redo()
            self._refresh_all()

    def merge(self, files=()):
        if self.dm is not None and not self.view.commit_float():
            return
        dlg = dialogs.MergeDialog(self, self.cfg, files)
        if dlg.exec() and dlg.open_result and dlg.result_path:
            self.open_file(dlg.result_path)
        config.save(self.cfg)

    def split(self):
        if self.dm is not None and not self.view.commit_float():
            return
        dialogs.SplitDialog(self, self.cfg, self.dm, self.thumbs.selected() if self.dm else ()).exec()
        config.save(self.cfg)

    def _pages_args(self):
        return self.dm.n, self.view.current_page(), self.thumbs.selected()

    def watermark(self):
        if not self.view.commit_float():
            return
        dlg = dialogs.WatermarkDialog(self, *self._pages_args())
        if dlg.exec():
            p = dlg.params()
            self.edit(tr("添加水印"), lambda d: pdfops.watermark(d, dlg.idx, **p), set(dlg.idx))

    def page_numbers(self):
        if not self.view.commit_float():
            return
        dlg = dialogs.PageNumberDialog(self, *self._pages_args())
        if dlg.exec():
            p = dlg.params()
            self.edit(tr("添加页码"), lambda d: pdfops.page_numbers(d, dlg.idx, **p), set(dlg.idx))

    def encrypt(self):
        if not self.view.commit_float():
            return
        dlg = dialogs.EncryptDialog(self, self.dm.encrypt)
        if not dlg.exec() or dlg.result == self.dm.encrypt:
            return
        self.dm.encrypt = dlg.result
        self.dm.dirty = True
        self._update_ui()
        if common.ask(self, tr("已设置密码，保存文件后生效。\n现在保存吗？") if dlg.result
                      else tr("已移除密码，保存文件后生效。\n现在保存吗？")):
            self.save()

    def compress(self):
        if not self.view.commit_float():
            return
        base = self.dm.path or os.path.join(self.cfg.get("last_dir", ""), self.dm.name)
        data = self.dm.bytes()
        now = os.path.getsize(self.dm.path) if self.dm.path and os.path.exists(self.dm.path) and not self.dm.dirty else len(data)
        dlg = dialogs.CompressDialog(self, os.path.splitext(base)[0] + tr("_压缩.pdf"), now)
        if not dlg.exec():
            return
        out = dlg.out.text().strip()
        if not out.lower().endswith(".pdf"):
            out += ".pdf"
        if self.dm.path and os.path.normcase(os.path.abspath(out)) == os.path.normcase(self.dm.path):
            return common.warn(self, tr("请保存为另一个文件名，不要覆盖当前文档。"))
        self.setCursor(Qt.WaitCursor)
        try:
            size = pdfops.compress(data, out, dlg.level())
        except Exception as exc:
            return common.error(self, tr("压缩"), exc)
        finally:
            self.unsetCursor()
        pct = (1 - size / now) * 100 if now else 0
        msg = tr("压缩完成：{before} → {after}", before=common.human_size(now), after=common.human_size(size))
        msg += tr("（减小 {pct}%）", pct=f"{pct:.0f}") if pct >= 1 else tr("（这个文件已经很紧凑，几乎没有可压缩的空间）")
        if common.ask(self, msg + "\n" + out + "\n\n" + tr("打开所在文件夹吗？")):
            dialogs.open_folder(os.path.dirname(out))

    def export_images(self):
        if not self.view.commit_float():
            return
        base = self.dm.path or os.path.join(self.cfg.get("last_dir", ""), self.dm.name)
        stem = os.path.splitext(os.path.basename(base))[0]
        dlg = dialogs.ExportImagesDialog(self, *self._pages_args(), os.path.join(os.path.dirname(base), stem + tr("_图片")))
        if not dlg.exec():
            return
        folder = dlg.folder.text().strip()
        try:
            with Progress(self, tr("正在导出图片…")) as p:
                files = pdfops.export_images(self.dm.doc, dlg.idx, folder, stem, dlg.dpi.currentData(),
                                             dlg.fmt.currentData(), p.step)
        except InterruptedError:
            return
        except Exception as exc:
            return common.error(self, tr("导出图片"), exc)
        if common.ask(self, tr("已导出 {n} 张图片。\n{folder}\n\n打开这个文件夹吗？", n=len(files), folder=folder)):
            dialogs.open_folder(folder)

    def export_text(self):
        if not self.view.commit_float():
            return
        base = self.dm.path or os.path.join(self.cfg.get("last_dir", ""), self.dm.name)
        f = common.pick_save(self, tr("导出文字"), os.path.splitext(base)[0] + ".txt", tr("文本文件 (*.txt)"))
        if not f:
            return
        try:
            text = pdfops.extract_text(self.dm.doc)
            with open(f, "w", encoding="utf-8-sig") as fh:
                fh.write(text)
        except Exception as exc:
            return common.error(self, tr("导出文字"), exc)
        if not any(l.strip() and not l.startswith("=====") for l in text.splitlines()):
            common.info(self, tr("已导出，但这个文件里没有可提取的文字（可能是扫描件）。"))
        else:
            self._hint(tr("文字已导出：{path}", path=f))

    def show_help(self):
        common.info(self, HELP[i18n.lang()].format(name=tr(APP_NAME), ver=VERSION))

    # ------------------------------------------------------------ settings
    def show_settings(self):
        if self.dm is not None and not self.view.commit_float():
            return
        dlg = SettingsDialog(self, i18n.lang())
        if dlg.exec() and dlg.lang() != i18n.lang():
            self.switch_language(dlg.lang())

    def _keep_opts(self):
        o = self.view.opts
        self.cfg.update(color=o["color"], text_color=o["text_color"], line_width=o["width"],
                        font=o["font"], font_size=o["size"])

    def switch_language(self, lang):
        """Rebuild the window in the other language. The open document, its undo steps, the page and
        the zoom stay as they are. -> the new window."""
        if self.dm is not None and not self.view.commit_float():
            return self
        self._keep_opts()
        self.cfg["lang"] = lang
        config.save(self.cfg)
        i18n.set_lang(lang)
        common.apply_language(QApplication.instance())
        dm, page, zoom, sel = self.dm, 0, 1.0, []
        if dm is not None:
            page, zoom, sel = self.view.current_page(), self.view.zoom, self.thumbs.selected()
            self.dm = None                  # handed over: this window must not close it
            self.view.set_doc(None)
            self.thumbs.set_doc(None)
        new = MainWindow(self.cfg)
        if self.testAttribute(Qt.WA_DontShowOnScreen):      # the tests run their windows off screen
            new.setAttribute(Qt.WA_DontShowOnScreen)
        if self.isMaximized():
            new.showMaximized()
        else:
            new.setGeometry(self.geometry())
            new.show()
        if dm is not None:
            new.set_doc(dm)
            new.view.set_zoom(zoom)
            new.view.goto_page(page)
            new._zoom_changed(new.view.zoom)
            if sel:
                new.thumbs.reload(None, sel)
            new._update_ui()
        self.hide()
        self.close()
        self.deleteLater()
        return new

    # ------------------------------------------------------------ window events
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.isLocalFile() for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        files = [f for f in files if f.lower().endswith(".pdf") or pdfops.is_image(f)]
        if not files:
            return
        e.acceptProposedAction()
        self.handle_files(files)

    def handle_files(self, files):
        if len(files) == 1:
            self.open_file(files[0])
        else:
            self.merge(files)

    def closeEvent(self, e):
        if not self.maybe_save():
            return e.ignore()
        self._keep_opts()
        config.save(self.cfg)
        e.accept()


class _Hint(QLabel):
    """Takes whatever width is left in the bar; long text is cut, it never pushes widgets out."""

    def __init__(self):
        super().__init__("")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumWidth(60)

    def sizeHint(self):
        return QSize(260, super().sizeHint().height())

    def minimumSizeHint(self):
        return QSize(60, super().minimumSizeHint().height())


def _ranges_text(indexes):
    from core.ranges import describe
    return describe(sorted(indexes))
