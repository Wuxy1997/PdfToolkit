"""GUI checks with screenshots. Usage: python tests/t_gui.py <scratch dir>"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = sys.argv[1]
os.makedirs(S, exist_ok=True)

import pymupdf
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core import config, pdfops

config.set_data_dir(os.path.join(S, "data"))
from ui import common, dialogs, signature
from ui.mainwindow import MainWindow
from ui.view import FloatImage, FloatText

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


app = QApplication([])
common.apply_theme(app)
# no modal questions during the test
common.ask = lambda *a, **k: True
common.info = common.warn = lambda *a, **k: print("BOX:", a[1][:120].replace("\n", " | "))
errors = []
common.error = lambda parent, what, exc: errors.append((what, repr(exc)))


def pump(ms=120):
    QTest.qWait(ms)


def shot(w, name):
    pump(250)
    w.grab().save(os.path.join(S, name + ".png"))


src = os.path.join(S, "doc.pdf")
d = pymupdf.open()
for i in range(6):
    p = d.new_page()
    p.insert_text((72, 90), f"Quarterly Report  Page {i + 1}", fontsize=22)
    p.insert_text((72, 130), "The quick brown fox jumps over the lazy dog.", fontsize=12)
    p.insert_textbox(pymupdf.Rect(72, 160, 520, 420), ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 12), fontsize=11)
    p.draw_rect(pymupdf.Rect(72, 460, 300, 600), color=(0.2, 0.4, 0.8), fill=(0.85, 0.9, 1))
    p.insert_text((72, 760), "Signature: ____________________", fontsize=12)
d.set_toc([[1, "Part One", 1], [1, "Part Two", 4]])
d.save(src)
d.close()

win = MainWindow(config.load())
win.setAttribute(Qt.WA_DontShowOnScreen)
win.show()
shot(win, "01_home")

check("open", win.open_file(src) and win.dm.n == 6)
pump(600)
shot(win, "02_editor")
v = win.view


def at(page, x, y):
    """viewport position of a page point"""
    it = v._items[page]
    return v.mapFromScene(it.pos() + QPointF(x, y))


def drag(page, a, b, mods=Qt.NoModifier):
    vp = v.viewport()
    pa, pb = at(page, *a), at(page, *b)
    QTest.mousePress(vp, Qt.LeftButton, mods, pa)
    for t in (0.3, 0.6, 1.0):
        q = QPoint(int(pa.x() + (pb.x() - pa.x()) * t), int(pa.y() + (pb.y() - pa.y()) * t))
        QTest.mouseMove(vp, q)
        pump(20)
    QTest.mouseRelease(vp, Qt.LeftButton, mods, pb)
    pump(60)


# ---- text
win.pick_tool("text")
QTest.mouseClick(v.viewport(), Qt.LeftButton, Qt.NoModifier, at(0, 330, 300))
pump()
check("float text", isinstance(v._float, FloatText))
v._float.setPlainText("批注：已审核 OK")
win.size.setValue(16)
win.color.set_color("#d32f2f", emit=True)
shot(win, "03_text_float")
tp = v._float.scenePos() - v._items[0].pos()
QTest.mouseClick(v.viewport(), Qt.LeftButton, Qt.NoModifier, at(0, 500, 700))
pump()
check("text committed", "批注：已审核 OK" in T(win.dm.doc[0]) and v._float is None, T(win.dm.doc[0])[-80:])
w = [x for x in win.dm.doc[0].get_text("words") if x[4].startswith("批注")]
check("text where placed", w and abs(w[0][0] - tp.x() - 1.5) < 3 and abs(w[0][1] - tp.y()) < 6, (w, tp))
check("dirty + undo", win.dm.dirty and win.acts["undo"].isEnabled())

# ---- shapes
for tool, a, b in (("rect", (320, 520), (520, 600)), ("ellipse", (330, 610), (500, 680)),
                   ("arrow", (300, 300), (200, 140)), ("line", (72, 136), (330, 136)), ("pen", (350, 60), (500, 100))):
    n0 = len(win.dm.doc[0].get_drawings())
    win.pick_tool(tool)
    drag(0, a, b)
    check("draw " + tool, len(win.dm.doc[0].get_drawings()) > n0)
win.pick_tool("highlight")
drag(0, (70, 75), (400, 92))
check("highlight", len(list(win.dm.doc[0].annots())) == 1)
win.pick_tool("erase")
before = T(win.dm.doc[0]).count("Lorem")
drag(0, (72, 160), (520, 200))
t = T(win.dm.doc[0])
check("erase", t.count("Lorem") < before and "Quarterly" in t, (before, t.count("Lorem")))
win.pick_tool("redact")
drag(0, (72, 220), (300, 240))
shot(win, "04_edits")

# ---- edit text
win.pick_tool("edittext")
from PySide6.QtCore import QEvent
from PySide6.QtGui import QMouseEvent
hp = QPointF(at(0, 150, 86))
# a hidden window gets no button-less move events from QTest: deliver one directly
app.sendEvent(v.viewport(), QMouseEvent(QEvent.MouseMove, hp, v.viewport().mapToGlobal(hp), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
pump(150)
check("hover box", v._hover is not None)
shot(win, "05_hover")
line = pdfops.pick_line(v.lines_of(0), 150, 86)
check("line", line and line["text"].startswith("Quarterly Report"), line)
dlg = dialogs.ReplaceTextDialog(win, line)
dlg.text.setText("年度报告 Annual Report 2026")
dlg.setAttribute(Qt.WA_DontShowOnScreen)
dlg.show()
shot(dlg, "06_replace_dialog")
p = dlg.params()
dlg.close()
win.edit("修改文字", lambda d: pdfops.replace_text(d[0], line, **p), {0})
t = T(win.dm.doc[0])
check("replace", "年度报告 Annual Report 2026" in t and "Quarterly Report  Page 1" not in t, t[:80])

# ---- signature
sd = signature.SignatureDialog(win)
sd.setAttribute(Qt.WA_DontShowOnScreen)
sd.show()
pump()
pad = sd.pad
QTest.mousePress(pad, Qt.LeftButton, Qt.NoModifier, QPoint(60, 120))
for i in range(1, 60):
    QTest.mouseMove(pad, QPoint(60 + i * 6, int(120 + 45 * math.sin(i / 3.0) * (1 - i / 80))))
    pump(4)
QTest.mouseRelease(pad, Qt.LeftButton, Qt.NoModifier, QPoint(420, 120))
check("pad has ink", not pad.empty())
img = pad.image()
check("pad image transparent + cropped", img is not None and img.hasAlphaChannel() and img.width() < pad.width() * 3
      and img.pixelColor(0, 0).alpha() == 0, img and (img.width(), img.height()))
sd._save(pad.image())
check("saved signature", len(signature.saved()) == 1)
shot(sd, "07_sign_dialog")
# photo import: dark scribble on light gray paper
photo = os.path.join(S, "photo.png")
pm = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 300))
pm.set_rect(pm.irect, (228, 226, 220))
for i in range(400):
    x = 100 + i
    y = int(150 + 50 * math.sin(i / 25))
    pm.set_rect(pymupdf.IRect(x, y, x + 5, y + 5), (20, 20, 60))
pm.save(photo)
res = signature.remove_background(QImage(photo), 190)
check("photo bg removed", res is not None and res.pixelColor(1, 1).alpha() == 0 and res.width() < 440 and res.height() < 140,
      res and (res.width(), res.height()))
dark = max(res.pixelColor(x, y).alpha() for x in range(0, res.width(), 3) for y in range(0, res.height(), 3))
check("photo ink kept", dark == 255, dark)
sd.load_photo(photo)
check("photo preview", not sd.photo_view.pixmap().isNull())
ts = signature.text_signature("张三", "KaiTi")
check("typed signature", ts is not None and ts.width() > 100)
sd.close()

win.use_signature(signature.saved()[0])
check("place mode", v.tool == "place" and win.tool_acts["sign"].isChecked())
v.verticalScrollBar().setValue(int(520 * v.k))
pump(300)
QTest.mouseClick(v.viewport(), Qt.LeftButton, Qt.NoModifier, at(0, 240, 745))
pump()
f = v._float
check("float sign", isinstance(f, FloatImage) and v.tool == "select" and abs(f.w - 140) < 1, f and f.w)
# resize by dragging the bottom-right corner
c0 = v.mapFromScene(f.mapToScene(QPointF(f.w, f.h)))
QTest.mousePress(v.viewport(), Qt.LeftButton, Qt.NoModifier, c0)
QTest.mouseMove(v.viewport(), c0 + QPoint(40, 20))
pump(30)
QTest.mouseRelease(v.viewport(), Qt.LeftButton, Qt.NoModifier, c0 + QPoint(40, 20))
check("resized keeps ratio", f.w > 150 and abs(f.w / f.h - f.image.width() / f.image.height()) < 0.02, (f.w, f.h))
# move by dragging the middle
c1 = v.mapFromScene(f.mapToScene(QPointF(f.w / 2, f.h / 2)))
x0 = f.scenePos().x()
QTest.mousePress(v.viewport(), Qt.LeftButton, Qt.NoModifier, c1)
QTest.mouseMove(v.viewport(), c1 + QPoint(30, 0))
pump(30)
QTest.mouseRelease(v.viewport(), Qt.LeftButton, Qt.NoModifier, c1 + QPoint(30, 0))
check("moved", abs(f.scenePos().x() - x0 - 30 / v.k) < 1.5 and v._float is f, (f.scenePos().x(), x0))
shot(win, "08_sign_float")
box = (f.scenePos().x() - v._items[0].pos().x(), f.scenePos().y() - v._items[0].pos().y(), f.w, f.h)
QTest.keyClick(v, Qt.Key_Return)
pump()
info = win.dm.doc[0].get_image_info()
check("sign committed", v._float is None and len(info) == 1 and abs(info[0]["bbox"][0] - box[0]) < 1
      and abs(info[0]["bbox"][2] - box[0] - box[2]) < 1, (info, box))
# Esc cancels a float
win.use_signature(signature.saved()[0])
QTest.mouseClick(v.viewport(), Qt.LeftButton, Qt.NoModifier, at(0, 400, 400))
QTest.keyClick(v, Qt.Key_Escape)
check("esc cancels", v._float is None and len(win.dm.doc[0].get_image_info()) == 1)
win.pick_tool("date")
check("date float", isinstance(v._float, FloatText) and len(v._float.toPlainText()) == 10)
v.cancel_float()
win.pick_tool("select")
shot(win, "09_after_sign")

# ---- pages
win.thumbs.clearSelection()
win.thumbs.item(1).setSelected(True)
win.thumbs.item(2).setSelected(True)
win.rotate(90)
check("rotate sel", win.dm.doc[1].rotation == 90 and win.dm.doc[2].rotation == 90 and win.dm.doc[0].rotation == 0)
check("selection kept", win.thumbs.selected() == [1, 2])
win.delete_pages()
check("delete sel", win.dm.n == 4 and "Page 4" in T(win.dm.doc[1]))
win.undo()
check("undo delete", win.dm.n == 6)
win.undo()
check("undo rotate", win.dm.doc[1].rotation == 0)
win.redo()
check("redo rotate", win.dm.doc[1].rotation == 90)
win.undo()
TH = type(win.thumbs)
check("drop order 1", TH.order_for_drop(6, [5], 0) == [5, 0, 1, 2, 3, 4])
check("drop order 2", TH.order_for_drop(6, [0, 1], 6) == [2, 3, 4, 5, 0, 1])
check("drop order 3", TH.order_for_drop(6, [1, 4], 3) == [0, 2, 1, 4, 3, 5])
check("drop order same", TH.order_for_drop(6, [2], 2) == list(range(6)) and TH.order_for_drop(6, [2], 3) == list(range(6)))
r3 = win.thumbs.visualRect(win.thumbs.model().index(1, 0))
check("drop target", win.thumbs.drop_target(r3.center() - QPoint(0, 20)) == 1 and win.thumbs.drop_target(r3.center() + QPoint(0, 20)) == 2,
      (win.thumbs.drop_target(r3.center() - QPoint(0, 20)), win.thumbs.drop_target(r3.center() + QPoint(0, 20))))
win.thumbs.clearSelection()
win.thumbs.item(5).setSelected(True)
win._reorder([5, 0, 1, 2, 3, 4])
check("reorder", "Page 6" in T(win.dm.doc[0]) and "年度报告" in T(win.dm.doc[1]) and win.thumbs.selected() == [0], win.thumbs.selected())
win.undo()
win.thumbs.clearSelection()
win.thumbs.item(4).setSelected(True)
win._move_to([4], 0)
check("move to front", "Page 5" in T(win.dm.doc[0]) and win.thumbs.selected() == [0])
win.undo()
win.thumbs.clearSelection()
other = os.path.join(S, "other.pdf")
d = pymupdf.open()
for i in range(2):
    d.new_page(width=842, height=595).insert_text((72, 100), f"INSERTED {i + 1}", fontsize=30)
d.save(other)
d.close()
win.insert_paths([other], 2)
check("insert", win.dm.n == 8 and "INSERTED 1" in T(win.dm.doc[2]) and "INSERTED 2" in T(win.dm.doc[3]))
check("layout follows", len(v._items) == 8 and abs(v._items[2].w - 842) < 1)
win.insert_blank(0)
check("blank", win.dm.n == 9 and not T(win.dm.doc[0]).strip())
pump(500)
shot(win, "10_pages")

# ---- dialogs render
dialogs.open_folder = lambda p: None
for name, dlg in (("11_merge", dialogs.MergeDialog(win, win.cfg, [src, other])),
                  ("12_split", dialogs.SplitDialog(win, win.cfg, win.dm, [1, 2, 3])),
                  ("13_watermark", dialogs.WatermarkDialog(win, win.dm.n, 0, [])),
                  ("14_numbers", dialogs.PageNumberDialog(win, win.dm.n, 0, [])),
                  ("15_encrypt", dialogs.EncryptDialog(win, None)),
                  ("16_compress", dialogs.CompressDialog(win, os.path.join(S, "c.pdf"), 123456)),
                  ("17_export", dialogs.ExportImagesDialog(win, win.dm.n, 0, [], S))):
    dlg.setAttribute(Qt.WA_DontShowOnScreen)
    dlg.show()
    shot(dlg, name)
    if name == "11_merge":
        dlg.out.setText(os.path.join(S, "gui_merged.pdf"))
        dlg.table.item(0, 2).setText("1-2")
        dlg._run()
        check("merge dialog", dlg.result_path and len(pymupdf.open(dlg.result_path)) == 4)
    if name == "12_split":
        check("split prefill", dlg.r_one.isChecked() and dlg.e_one.text() == "2-4", dlg.e_one.text())
        dlg.folder.setText(os.path.join(S, "gui_split"))
        dlg.r_every.setChecked(True)
        dlg.s_every.setValue(4)
        dlg._run()
        check("split dialog", sorted(os.listdir(os.path.join(S, "gui_split"))) ==
              ["doc_第1-4页.pdf", "doc_第5-8页.pdf", "doc_第9页.pdf"], os.listdir(os.path.join(S, "gui_split")))
    dlg.close()

win.edit("水印", lambda d: pdfops.watermark(d, list(range(win.dm.n)), "内部资料", tile=True, opacity=0.18), None)
win.edit("页码", lambda d: pdfops.page_numbers(d, list(range(win.dm.n))), None)
v.goto_page(1)
pump(500)
shot(win, "18_watermark")

# ---- save / reopen
out = os.path.join(S, "gui_saved.pdf")
check("save", win._save_to(out) and not win.dm.dirty and os.path.exists(out))
check("title", win.windowTitle().startswith("gui_saved.pdf"), win.windowTitle())
win.dm.encrypt = {"user_pw": "pw1", "owner_pw": "pw1", "allow": {"print"}}
check("save enc", win._save_to(os.path.join(S, "gui_enc.pdf")))
common.get_password = lambda *a, **k: "pw1"
check("reopen enc", win.open_file(os.path.join(S, "gui_enc.pdf")) and win.dm.n == 9 and win.dm.encrypt)
pump(400)
v.set_zoom(0.5)
pump(400)
shot(win, "19_zoom_out")
v.fit_page()
check("fit page", 0.2 < v.zoom < 2)
win.resize(980, 620)
pump(400)
shot(win, "20_small_window")
win.close_doc()
check("closed", win.dm is None and win.stack.currentIndex() == 0)
shot(win, "21_home_recent")
check("no error boxes", not errors, errors)
print(f"{ok} passed, {bad} failed")
win.close()
sys.exit(1 if bad else 0)
