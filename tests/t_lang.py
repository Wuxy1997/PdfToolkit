"""The English interface and the language switch, with screenshots.
    python tests\\t_lang.py <scratch dir>"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = sys.argv[1]
os.makedirs(S, exist_ok=True)

import pymupdf
import shiboken6
from PySide6.QtCore import QCoreApplication, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QGroupBox, QLabel, QLineEdit, QMessageBox,
                               QTabWidget, QTableWidget, QToolBar, QToolButton, QWidget)

from core import config, fonts, i18n, pdfops, ranges
from core.docmodel import Doc
from core.i18n import tr
from core.version import VERSION

config.set_data_dir(os.path.join(S, "data"))
from ui import common, dialogs, settings, signature
from ui.helptext import HELP
from ui.mainwindow import MainWindow

CJK = re.compile("[一-鿿　-〿＀-￯“”‘’]")
ok = bad = 0


def check(name, cond, info=""):
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
        print("FAIL", name, info)


def T(page):
    return page.get_text().replace("\xa0", " ")


def pump(ms=120):
    QTest.qWait(ms)


def shot(w, name):
    pump(250)
    w.grab().save(os.path.join(S, name + ".png"))


def texts(w):
    """Every text a window shows: (where, text)."""
    out = [("title", w.windowTitle())]
    for c in [w] + w.findChildren(QWidget):
        name = type(c).__name__
        if c.toolTip():
            out.append((name + " tip", c.toolTip()))
        if isinstance(c, (QLabel, QAbstractButton)):
            out.append((name, c.text()))
        elif isinstance(c, QLineEdit):
            out.append((name + " placeholder", c.placeholderText()))
        elif isinstance(c, QComboBox):
            out += [(name + " item", c.itemText(i)) for i in range(c.count())]
        elif isinstance(c, QGroupBox):
            out.append((name, c.title()))
        elif isinstance(c, QTabWidget):
            out += [(name + " tab", c.tabText(i)) for i in range(c.count())]
        elif isinstance(c, QTableWidget):
            out += [(name + " header", c.horizontalHeaderItem(i).text()) for i in range(c.columnCount())]
    for a in w.findChildren(type(win.acts["open"])):
        out += [("action", a.text()), ("action tip", a.toolTip())]
    return out


def chinese_in(w, allow=()):
    return [(where, t) for where, t in texts(w) if t and CJK.search(t) and not any(a in t for a in allow)]


def squeezed(win):
    """Toolbar buttons narrower than their text, or pushed into the » menu."""
    out = []
    for tb in win.findChildren(QToolBar):
        if not tb.isVisible():
            continue
        for b in tb.findChildren(QToolButton):
            if b.objectName() == "qt_toolbar_ext_button":
                if b.isVisible():
                    out.append((tb.objectName(), "» menu in use"))
            elif not b.isVisible() and b.defaultAction() is not None:
                out.append((tb.objectName(), "hidden: " + b.text()))
            elif b.isVisible() and b.width() < b.sizeHint().width():
                out.append((tb.objectName(), "cut: " + b.text()))
    return out


app = QApplication([])
boxes, errors = [], []
common.ask = lambda *a, **k: True
common.info = common.warn = lambda parent, text: boxes.append(text)
common.error = lambda parent, what, exc: errors.append((what, repr(exc)))

src = os.path.join(S, "doc.pdf")
d = pymupdf.open()
for i in range(6):
    p = d.new_page()
    p.insert_text((72, 90), f"Quarterly Report  Page {i + 1}", fontsize=22)
    p.insert_text((72, 130), "The quick brown fox jumps over the lazy dog.", fontsize=12)
    p.insert_text((72, 760), "Signature: ____________________", fontsize=12)
d.set_toc([[1, "Part One", 2], [1, "Part Two", 4]])
d.save(src)
d.close()

# ------------------------------------------------------------ which language at start
check("default is a language", common.pick_language({"lang": ""}) in i18n.LANGS)
check("saved wins", common.pick_language({"lang": "en"}) == "en" and i18n.lang() == "en")
check("--lang wins", common.pick_language({"lang": "en"}, "zh") == "zh" and tr("打开") == "打开")
check("bad value falls back", common.pick_language({"lang": "fr"}, "xx") in i18n.LANGS)

# ------------------------------------------------------------ texts made by the PDF code
i18n.set_lang("en")
check("tr", tr("共 {n} 页", n=3) == "3 pages" and tr("not a key") == "not a key")
doc = pymupdf.open(src)
out = os.path.join(S, "split_en")
files = [os.path.basename(f) for f in pdfops.split(doc, [[0], [1, 2], [0, 3]], out, "doc")]
check("split names en", files == ["doc_p1.pdf", "doc_p2-3.pdf", "doc_part3.pdf"], files)
bm = pdfops.groups_bookmarks(doc)
check("bookmark groups en", bm[0][0] == "Front pages" and bm[1][0] == "Part One", [t for t, _ in bm])
check("text header en", pdfops.extract_text(doc, [1]).startswith("===== Page 2 ====="))
check("safe name en", pdfops.safe_name("??") == "Untitled")
try:
    ranges.parse_ranges("9", 6)
    msg = ""
except ranges.RangeError as exc:
    msg = str(exc)
check("range error en", msg == "Page 9 is out of range (this file has 6 pages)", msg)
try:
    pdfops.delete(doc, range(6))
    msg = ""
except ValueError as exc:
    msg = str(exc)
check("delete error en", msg == "Cannot delete every page", msg)
blank = Doc.blank()
check("blank name en", blank.name == "Untitled.pdf", blank.name)
blank.close()
i18n.set_lang("zh")
files = [os.path.basename(f) for f in pdfops.split(doc, [[0], [1, 2], [0, 3]], os.path.join(S, "split_zh"), "doc")]
check("split names zh", files == ["doc_第1页.pdf", "doc_第2-3页.pdf", "doc_部分3.pdf"], files)
check("text header zh", pdfops.extract_text(doc, [1]).startswith("===== 第 2 页 ====="))
doc.close()
check("help has both", all("{name}" in HELP[k] and "{ver}" in HELP[k] for k in i18n.LANGS)
      and not CJK.search(HELP["en"]))

# ------------------------------------------------------------ the English window
i18n.set_lang("en")
common.apply_language(app)
check("font for English", '"Segoe UI"' in app.styleSheet().split("font-family:")[1].split(";")[0].split(",")[0])
check("app name en", app.applicationName() == "PDF Toolkit")
win = MainWindow(config.load())
win.setAttribute(Qt.WA_DontShowOnScreen)
win.show()
pump(300)
check("title en", win.windowTitle() == f"PDF Toolkit {VERSION}", win.windowTitle())
check("no Chinese on the start page", not chinese_in(win), chinese_in(win)[:5])
check("start page: toolbar fits", not squeezed(win), squeezed(win))
shot(win, "en_01_home")

check("open", win.open_file(src) and win.dm.n == 6)
pump(600)
check("title with file en", win.windowTitle() == "doc.pdf - PDF Toolkit", win.windowTitle())
check("labels en", win.acts["open"].text() == "Open" and win.tool_acts["text"].text() == "Add text"
      and win.acts["settings"].text() == "Settings")
check("tooltip en", win.acts["open"].toolTip() == "Open (Ctrl+O)", win.acts["open"].toolTip())
check("side title en", win.side_title.text() == "Pages (6)", win.side_title.text())
check("page count en", win.lbl_pages.text() == "/ 6", win.lbl_pages.text())
check("no Chinese in the editor", not chinese_in(win), chinese_in(win)[:5])
check("editor: toolbars fit", not squeezed(win), squeezed(win))
check("font box shows English names", win.font_box.currentText() == "Microsoft YaHei"
      and win.font_box.currentData() == "微软雅黑" and win.view.opts["font"] == "微软雅黑",
      (win.font_box.currentText(), win.font_box.currentData()))
i = win.font_box.findData("宋体")
if i >= 0:
    win.font_box.setCurrentIndex(i)
    check("font box sets the key", win.view.opts["font"] == "宋体" and win.font_box.currentText() == "SimSun")
    win.font_box.setCurrentIndex(win.font_box.findData("微软雅黑"))
shot(win, "en_02_editor")

win.pick_tool("highlight")
pump(100)
check("hint en", win.lbl_hint.text() == "Drag across the text to highlight", win.lbl_hint.text())
win.pick_tool("text")
it = win.view._items[0]
QTest.mouseClick(win.view.viewport(), Qt.LeftButton, Qt.NoModifier, win.view.mapFromScene(it.pos() + QPointF(120, 300)))
pump(150)
check("text hint en", win.lbl_hint.text().startswith("Type the text;"), win.lbl_hint.text())
shot(win, "en_03_text_float")
win.view.cancel_float()
win.pick_tool("select")
win.zoom_box.setEditText("Fit page")
win._zoom_picked()
check("fit page by its English name", 0.2 < win.view.zoom < 1.2, win.view.zoom)
win.zoom_box.setEditText("Fit width")
win._zoom_picked()
win.thumbs.reload(None, [1, 2])
pump(150)
check("selection text en", win.side_title.text() == "Pages (6) · 2 selected", win.side_title.text())

# ---- every dialog
line = next(l for l in win.view.lines_of(0) if "quick" in l["text"])
other = os.path.join(S, "other.pdf")
d = pymupdf.open()
d.new_page()
d.save(other)
d.close()
dlgs = [("en_04_replace", dialogs.ReplaceTextDialog(win, line)),
        ("en_05_merge", dialogs.MergeDialog(win, win.cfg, [src, other])),
        ("en_06_split", dialogs.SplitDialog(win, win.cfg, win.dm, [1, 2, 3])),
        ("en_07_watermark", dialogs.WatermarkDialog(win, win.dm.n, 0, [1, 2])),
        ("en_08_numbers", dialogs.PageNumberDialog(win, win.dm.n, 0, [])),
        ("en_09_encrypt", dialogs.EncryptDialog(win, None)),
        ("en_10_compress", dialogs.CompressDialog(win, os.path.join(S, "doc_compressed.pdf"), 123456)),
        ("en_11_export", dialogs.ExportImagesDialog(win, win.dm.n, 0, [], S)),
        ("en_12_settings", settings.SettingsDialog(win, "en")),
        ("en_13_sign", signature.SignatureDialog(win))]
for name, dlg in dlgs:
    dlg.setAttribute(Qt.WA_DontShowOnScreen)
    dlg.show()
    shot(dlg, name)
    left = chinese_in(dlg, allow=("中文",) if name == "en_12_settings" else ())
    check("no Chinese in " + name, not left, left[:4])
    if isinstance(dlg, signature.SignatureDialog):
        tabs = dlg.findChild(QTabWidget)
        for k in (1, 2):
            tabs.setCurrentIndex(k)
            if k == 2:
                dlg.name.setText("Alex Morgan")
            shot(dlg, f"{name}_tab{k + 1}")
        check("handwriting face first in English", dlg.face.itemData(0) in ("Segoe Script", "Ink Free", "Lucida Handwriting"),
              dlg.face.itemText(0))
check("merge default name en", os.path.basename(dlgs[1][1].out.text()) == "Merged.pdf", dlgs[1][1].out.text())
check("merge summary en", dlgs[1][1].summary.text() == "2 files, 7 pages", dlgs[1][1].summary.text())
check("split folder en", dlgs[2][1].folder.text().endswith("doc_split"), dlgs[2][1].folder.text())
wm = dlgs[3][1]
check("watermark defaults en", wm.text.text() == "CONFIDENTIAL" and wm.params()["font_name"] in fonts.FONTS
      and wm.font.currentText() == tr(wm.params()["font_name"]), wm.params())
check("pages field en", wm.pages.combo.itemText(0) == "All pages (6)" and wm.pages.combo.currentData() == "sel")
nb = dlgs[4][1]
check("number styles en", [nb.fmt.itemText(i) for i in range(nb.fmt.count())] ==
      ["{n}", "{n} / {total}", "Page {n}", "Page {n} of {total}", "- {n} -"])
check("number positions en", nb.pos.itemText(0) == "Footer, centre" and nb.pos.itemData(0) == "bc")
rp = dlgs[0][1]
check("replace font is a key", rp.params()["font_name"] in fonts.FONTS, rp.params()["font_name"])
check("compress levels en", dlgs[6][1].grp.button(2).text().startswith("Balanced (recommended)  —  images down to 150 DPI"),
      dlgs[6][1].grp.button(2).text())
for _, dlg in dlgs:
    dlg.close()

# ---- messages
boxes.clear()
win.thumbs.selectAll()
win.delete_pages()
check("message en", boxes == ["You cannot delete every page; at least one must remain."], boxes)
boxes.clear()
win.show_help()
check("help en", len(boxes) == 1 and f"PDF Toolkit {VERSION}" in boxes[0] and not CJK.search(boxes[0]), boxes)
boxes.clear()
errors.clear()
win.thumbs.reload(None, [0])

# the real message boxes (their buttons are relabelled by hand) and Qt's own texts
seen = []
QMessageBox.exec = lambda self: seen.append((self.windowTitle(), sorted(b.text() for b in self.buttons()))) or 0
common._box(win, QMessageBox.Question, "x", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
common._box(win, QMessageBox.Question, "x", QMessageBox.Yes | QMessageBox.No)
check("message box buttons en", seen == [("PDF Toolkit", ["Cancel", "Don't save", "Save"]),
                                         ("PDF Toolkit", ["No", "Yes"])], seen)
check("Qt's own texts en", common._qt_tr is None and QCoreApplication.translate("QPlatformTheme", "Cancel") == "Cancel")

# ------------------------------------------------------------ switching with a document open
win.edit("t", lambda dd: pdfops.add_text(dd[0], 72, 400, "kept across the switch", 14, "#000000"), {0})
win.rotate(90)
check("two undo steps before", win.dm.can_undo() and win.dm.dirty)
win.view.set_zoom(0.8)
win.view.goto_page(3)
win.thumbs.reload(None, [3, 4])
pump(300)
dm, zoom = win.dm, win.view.zoom
old = win
new = old.switch_language("zh")
new.setAttribute(Qt.WA_DontShowOnScreen)
pump(500)
check("a new window took over", new is not old and MainWindow.current is new
      and (not shiboken6.isValid(old) or not old.isVisible()))
check("same document object", new.dm is dm and old.dm is None and dm.doc.page_count == 6)
check("still unsaved, undo kept", new.dm.dirty and new.dm.can_undo())
check("page and zoom kept", new.view.current_page() == 3 and abs(new.view.zoom - zoom) < 0.01,
      (new.view.current_page(), new.view.zoom))
check("selection kept", new.thumbs.selected() == [3, 4], new.thumbs.selected())
check("Chinese again", new.acts["open"].text() == "打开" and new.windowTitle() == "● doc.pdf - PDF工具箱"
      and new.side_title.text().startswith("页面"), new.windowTitle())
check("font for Chinese", '"Microsoft YaHei UI"' in app.styleSheet().split("font-family:")[1].split(",")[0])
check("font box Chinese", new.font_box.currentText() == "微软雅黑" and new.font_box.currentData() == "微软雅黑")
check("Chinese editor: toolbars fit", not squeezed(new), squeezed(new))
seen.clear()
common._box(new, QMessageBox.Question, "x", QMessageBox.Yes | QMessageBox.No)
check("message box buttons zh", seen == [("PDF工具箱", ["否", "是"])], seen)
check("Qt's own texts zh", common._qt_tr is not None
      and CJK.search(QCoreApplication.translate("QPlatformTheme", "Cancel")), QCoreApplication.translate("QPlatformTheme", "Cancel"))
boxes.clear()
new.show_help()
check("help zh", len(boxes) == 1 and f"PDF工具箱 {VERSION}" in boxes[0] and "界面语言" in boxes[0])
boxes.clear()
with open(os.path.join(S, "data", "config.json"), encoding="utf-8") as f:
    check("choice saved", json.load(f)["lang"] == "zh")
check("the edit is there before undo", "kept across" in T(new.dm.doc[0]))
new.undo()
new.undo()
check("undo works after the switch", not new.dm.can_undo() and "kept across" not in T(new.dm.doc[0]))
new.redo()
check("redo works after the switch", "kept across" in T(new.dm.doc[0]))
shot(new, "zh_14_after_switch")

# through the Settings window, as a person would
settings.SettingsDialog.exec = lambda self: (self.r_en.setChecked(True), True)[1]
new.show_settings()
win = MainWindow.current
win.setAttribute(Qt.WA_DontShowOnScreen)
pump(500)
check("Settings switched to English", win is not new and i18n.lang() == "en" and win.acts["save"].text() == "Save"
      and win.dm is dm, win.acts["save"].text())
check("no Chinese after switching", not chinese_in(win), chinese_in(win)[:5])
settings.SettingsDialog.exec = lambda self: True       # OK without changing anything
win.show_settings()
check("same language: same window", MainWindow.current is win)
shot(win, "en_15_after_switch")

# a text box being typed is written to the page first, never lost
win.pick_tool("text")
it = win.view._items[win.view.current_page()]
QTest.mouseClick(win.view.viewport(), Qt.LeftButton, Qt.NoModifier, win.view.mapFromScene(it.pos() + QPointF(150, 200)))
pump(150)
QTest.keyClicks(win.view.viewport(), "typed before switching")
pump(100)
page = win.view.current_page()
win = win.switch_language("zh")
win.setAttribute(Qt.WA_DontShowOnScreen)
pump(300)
check("text being typed is kept", "typed before switching" in T(win.dm.doc[page]),
      win.dm.doc[page].get_text()[:80])

# save in English, start page in English
win = win.switch_language("en")
win.setAttribute(Qt.WA_DontShowOnScreen)
out = os.path.join(S, "lang_saved.pdf")
check("save", win._save_to(out) and not win.dm.dirty)
check("saved hint en", win.lbl_hint.text() == "Saved: " + out, win.lbl_hint.text())
win.close_doc()
pump(300)
check("recent list en", win.home.recent.count() >= 1 and not chinese_in(win), chinese_in(win)[:5])
shot(win, "en_16_home_recent")
win = win.switch_language("zh")              # with no document open
win.setAttribute(Qt.WA_DontShowOnScreen)
pump(300)
check("switch on the start page", win.dm is None and win.windowTitle() == f"PDF工具箱 {VERSION}", win.windowTitle())
check("Chinese start page: toolbar fits", not squeezed(win), squeezed(win))
shot(win, "zh_17_home")

check("no error boxes", not errors and not boxes, (errors, boxes))
print(f"{ok} passed, {bad} failed")
win.close()
sys.exit(1 if bad else 0)
