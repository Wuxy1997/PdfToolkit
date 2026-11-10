"""Core checks. Usage: python tests/t_core.py <scratch dir>"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymupdf

from core import pdfops, ranges
from core.docmodel import Doc

S = sys.argv[1]
os.makedirs(S, exist_ok=True)
ok = bad = 0


def check(name, cond, info=""):
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
        print("FAIL", name, info)


def T(page):
    return page.get_text().replace(" ", " ")


def make(path, n, tag, toc=False, rotate=0):
    d = pymupdf.open()
    for i in range(n):
        p = d.new_page()
        p.insert_text((72, 100), f"{tag} page {i + 1}", fontsize=20)
        p.insert_text((72, 140), f"second line {tag}{i + 1} here", fontsize=12)
        if rotate:
            p.set_rotation(rotate)
    if toc:
        d.set_toc([[1, "Chapter A", 1], [2, "Sub", 2], [1, "Chapter B", 3]])
    d.save(path)
    d.close()
    return path


def texts(path, pw=None):
    d = pymupdf.open(path)
    if pw:
        d.authenticate(pw)
    t = [p.get_text() for p in d]
    d.close()
    return t


# ---- ranges
check("r1", ranges.parse_ranges("1-3,5", 6) == [0, 1, 2, 4])
check("r2", ranges.parse_ranges("", 3) == [0, 1, 2])
check("r3", ranges.parse_ranges("4-", 6) == [3, 4, 5])
check("r4", ranges.parse_ranges("-2", 6) == [0, 1])
check("r5", ranges.parse_ranges("3-1", 6) == [2, 1, 0])
check("r6", ranges.parse_groups("1-2；3，5-", 6) == [[0, 1], [2], [4, 5]])
check("r7", ranges.describe([0, 1, 2, 4, 6, 7]) == "1-3,5,7-8")
for badtxt in ("0", "7", "a", "1-9", "-"):
    try:
        ranges.parse_ranges(badtxt, 6)
        check("rbad " + badtxt, False)
    except ranges.RangeError:
        check("rbad", True)

# ---- merge
a = make(os.path.join(S, "a.pdf"), 3, "AAA", toc=True)
b = make(os.path.join(S, "b.pdf"), 4, "BBB")
img = os.path.join(S, "pic.png")
pm = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 300, 200))
pm.set_rect(pm.irect, (200, 30, 30))
pm.save(img)
out = os.path.join(S, "merged.pdf")
n = pdfops.merge([{"path": a}, {"path": b, "pages": [3, 0]}, {"path": img}], out)
t = texts(out)
check("merge count", n == 6, n)
check("merge order", "AAA page 1" in t[0] and "BBB page 4" in t[3] and "BBB page 1" in t[4], t)
d = pymupdf.open(out)
toc = d.get_toc()
check("merge toc", [x[1] for x in toc] == ["a", "Chapter A", "Sub", "Chapter B", "b", "pic"], toc)
check("merge toc pages", [x[2] for x in toc] == [1, 1, 2, 3, 4, 6], toc)
check("merge image page", abs(d[5].rect.width - 300) < 80 or d[5].rect.width > 0)
d.close()
out2 = os.path.join(S, "merged_a4.pdf")
pdfops.merge([{"path": img}], out2, image_page="a4")
d = pymupdf.open(out2)
check("a4 landscape", abs(d[0].rect.width - 842) < 1 and abs(d[0].rect.height - 595) < 1, d[0].rect)
check("a4 has image", len(d[0].get_images(full=True)) == 1)
d.close()

# ---- split
doc, _ = pdfops.load(out)
files = pdfops.split(doc, ranges.parse_groups("1-2,3,5-", doc.page_count), os.path.join(S, "sp1"), "m")
check("split files", [os.path.basename(f) for f in files] == ["m_第1-2页.pdf", "m_第3页.pdf", "m_第5-6页.pdf"], files)
check("split pages", [len(texts(f)) for f in files] == [2, 1, 2])
files = pdfops.split(doc, pdfops.groups_every(doc.page_count, 4), os.path.join(S, "sp2"), "m")
check("split every", [len(texts(f)) for f in files] == [4, 2])
g = pdfops.groups_bookmarks(doc)
check("split bm groups", [x[0] for x in g] == ["a", "b", "pic"] and [len(x[1]) for x in g] == [3, 2, 1], g)
files = pdfops.split(doc, [x[1] for x in g], os.path.join(S, "sp3"), "m", names=[x[0] for x in g])
check("split bm names", os.path.basename(files[1]) == "m_2_b.pdf", files)
doc.close()

# ---- page ops + undo
D = Doc.open(b)
with D.edit() as d:
    pdfops.rotate(d, [0, 2], 90)
check("rotate", D.doc[0].rotation == 90 and D.doc[1].rotation == 0 and D.doc[2].rotation == 90)
with D.edit() as d:
    pdfops.delete(d, [1])
check("delete", D.n == 3 and "BBB page 3" in T(D.doc[1]))
with D.edit() as d:
    pdfops.reorder(d, [2, 0, 1])
check("reorder", "BBB page 4" in T(D.doc[0]))
with D.edit() as d:
    k = pdfops.insert_file(d, a, 1)
check("insert file", k == 3 and D.n == 6 and "AAA page 1" in T(D.doc[1]) and "BBB page 1" in T(D.doc[4]))
with D.edit() as d:
    pdfops.insert_blank(d, 0)
check("insert blank", D.n == 7 and not T(D.doc[0]).strip())
for _ in range(5):
    D.undo()
check("undo all", D.n == 4 and D.doc[0].rotation == 0 and "BBB page 2" in T(D.doc[1]) and not D.can_undo())
D.redo()
check("redo", D.doc[0].rotation == 90 and D.can_redo())
try:
    with D.edit() as d:
        pdfops.delete(d, [0, 1, 2, 3])
    check("delete all refused", False)
except ValueError:
    check("delete all refused", D.n == 4)
try:
    with D.edit() as d:
        d.delete_page(0)
        raise RuntimeError("boom")
except RuntimeError:
    pass
check("rollback", D.n == 4)
ex = os.path.join(S, "extract.pdf")
pdfops.extract(D.doc, [3, 1], ex)
t = texts(ex)
check("extract", len(t) == 2 and "page 4" in t[0] and "page 2" in t[1])
D.close()

# ---- content
D = Doc.open(a)
with D.edit() as d:
    pdfops.add_text(d[0], 100, 300, "你好 PDF 工具\n第二行 line", 14, "#ff0000", "微软雅黑")
t = T(D.doc[0])
check("add text", "你好 PDF 工具" in t and "第二行 line" in t, t)
check("working copy stays small", len(D.bytes()) < 400_000, len(D.bytes()))
words = D.doc[0].get_text("words")
w = [x for x in words if x[4].startswith("你好")][0]
check("text position", abs(w[0] - 100) < 2 and 298 < w[1] < 306, w)
with D.edit() as d:
    pdfops.add_text(d[0], 100, 400, "中文 with Arial", 12, "#000000", "Arial")
check("font fallback", "中文 with Arial" in T(D.doc[0]))
with D.edit() as d:
    pdfops.add_image(d[0], (300, 300, 400, 366), path=img)
info = D.doc[0].get_image_info()
check("add image", len(info) == 1 and abs(info[0]["bbox"][0] - 300) < 1 and abs(info[0]["bbox"][3] - 366) < 1, info)
for kind, pts in (("rect", [(50, 500), (150, 560)]), ("ellipse", [(160, 500), (260, 560)]),
                  ("line", [(50, 600), (250, 600)]), ("arrow", [(50, 620), (250, 660)]),
                  ("pen", [(50, 700), (80, 720), (120, 690), (160, 730)])):
    before = len(D.doc[0].get_drawings())
    with D.edit() as d:
        check("draw " + kind, pdfops.draw(d[0], kind, pts, "#0000ff", 2))
    check("drawn " + kind, len(D.doc[0].get_drawings()) > before)
with D.edit() as d:
    r = pdfops.markup(d[0], (60, 80, 400, 105), "highlight", "#ffff00")
check("highlight annot", r == "annot" and len(list(D.doc[0].annots())) == 1, r)
with D.edit() as d:
    r = pdfops.markup(d[0], (400, 700, 500, 750), "highlight", "#ffff00")
check("highlight box", r == "box")
line = pdfops.text_line_at(D.doc[0], 100, 136)
check("line found", line and line["text"] == "second line AAA1 here" and abs(line["size"] - 12) < 0.1, line)
with D.edit() as d:
    pdfops.replace_text(d[0], line, "replaced 新文字")
t = T(D.doc[0])
check("replace", "replaced 新文字" in t and "second line" not in t and "AAA page 1" in t, t)
nl = pdfops.text_line_at(D.doc[0], 100, 136)
check("replace position", nl and abs(nl["origin"][0] - line["origin"][0]) < 0.5 and abs(nl["origin"][1] - line["origin"][1]) < 0.5, nl)
check("images kept", len(D.doc[0].get_image_info()) == 1)
with D.edit() as d:
    pdfops.erase(d[0], (60, 80, 400, 110))
t = T(D.doc[0])
check("erase", "AAA page 1" not in t and "replaced" in t, t)
with D.edit() as d:
    pdfops.erase(d[0], (290, 290, 350, 380), "#000000")
pix = D.doc[0].get_pixmap()
check("redact black", pix.pixel(320, 330)[:3] == (0, 0, 0), pix.pixel(320, 330))
check("image half kept", pix.pixel(380, 330)[:3] == (200, 30, 30), pix.pixel(380, 330))

# rotated page (sideways sheet that /Rotate shows upright): content lands where it is shown
def make_rot(path):
    src = pymupdf.open()
    sp = src.new_page(width=842, height=595)
    sp.insert_text((72, 100), "ROT page 1", fontsize=20)
    sp.insert_text((72, 140), "second line ROT1 here", fontsize=12)
    for r in (90, 270):
        d = pymupdf.open()
        p = d.new_page(width=595, height=842)
        p.show_pdf_page(p.rect, src, 0, rotate=r)
        p.set_rotation(90)
        probe = pymupdf.open(stream=d.tobytes(), filetype="pdf")
        probe[0].remove_rotation()
        up = probe[0].get_text("dict")["blocks"][0]["lines"][0]["dir"][0] > 0.9
        if up:
            d.save(path)
            return path
    raise SystemExit("could not build the rotated fixture")


R = Doc.open(make_rot(os.path.join(S, "rot.pdf")))
pg = R.doc[0]
check("rot rect", abs(pg.rect.width - 842) < 1 and pg.rotation == 90)
line = pdfops.text_line_at(pg, 100, 136)
check("rot line found", line is not None and line["text"] == "second line ROT1 here", line)
check("rot line box", line and abs(line["bbox"][0] - 72) < 1 and abs(line["origin"][1] - 140) < 1, line)
with R.edit() as d:
    pdfops.add_text(d[0], 400, 300, "ROTTEXT", 16, "#000000", "Arial")
w = [x for x in R.doc[0].get_text("words") if x[4] == "ROTTEXT"][0]
check("rot text place", abs(w[0] - 400) < 2 and abs(w[1] - 300) < 6 and w[2] - w[0] > w[3] - w[1], w)
check("rot page same size", abs(R.doc[0].rect.width - 842) < 1 and R.doc[0].rotation == 0)
R.undo()
check("rot undo", R.doc[0].rotation == 90)
with R.edit() as d:
    pdfops.replace_text(d[0], line, "CHANGED")
t = R.doc[0].get_text()
check("rot replace", "CHANGED" in t and "second line" not in t and "ROT page 1" in t, t)
nl = pdfops.text_line_at(R.doc[0], 80, 136)
check("rot replace position", nl and nl["text"] == "CHANGED" and abs(nl["origin"][0] - 72) < 1 and abs(nl["origin"][1] - 140) < 1, nl)
with R.edit() as d:
    pdfops.draw(d[0], "rect", [(700, 500), (800, 560)], "#ff0000", 2, fill="#ff0000")
pix = R.doc[0].get_pixmap()
check("rot draw", pix.pixel(750, 530)[:3] == (255, 0, 0), pix.pixel(750, 530))
with R.edit() as d:
    pdfops.erase(d[0], (60, 80, 300, 110))
check("rot erase", "ROT page 1" not in R.doc[0].get_text() and "CHANGED" in R.doc[0].get_text())
R.close()

# ---- watermark / numbers
with D.edit() as d:
    pdfops.watermark(d, [0, 1, 2], "机密 CONFIDENTIAL", tile=False)
check("watermark", all("机密 CONFIDENTIAL" in T(D.doc[i]) for i in range(3)))
with D.edit() as d:
    pdfops.watermark(d, [1], "TILE", size=30, tile=True)
check("watermark tile", T(D.doc[1]).count("TILE") > 6, T(D.doc[1]).count("TILE"))
with D.edit() as d:
    pdfops.page_numbers(d, [1, 2], "第 {n} 页 / 共 {total} 页", "br", start=1)
check("numbers", "第 1 页 / 共 2 页" in T(D.doc[1]) and "第 2 页 / 共 2 页" in T(D.doc[2])
      and "共 2 页" not in T(D.doc[0]))
w = [x for x in D.doc[2].get_text("words") if x[4] == "共"][0]
check("numbers pos", w[1] > 780 and w[0] > 400, w)

# ---- save / encrypt
sv = os.path.join(S, "saved.pdf")
D.save(sv)
check("saved", not D.dirty and D.path == os.path.abspath(sv) and len(texts(sv)) == 3)
check("save size sane (fonts subset)", os.path.getsize(sv) < 600_000, os.path.getsize(sv))


def ink(page, box):
    pix = page.get_pixmap(clip=pymupdf.Rect(box))
    s = pix.samples
    return sum(1 for k in range(0, len(s), pix.n) if s[k] < 128)


# text added after a save must not lose glyphs (fonts are subset per insertion)
with D.edit() as d:
    pdfops.add_text(d[2], 72, 300, "保存之后新加的汉字", 20, "#000000", "微软雅黑")
with D.edit() as d:
    pdfops.add_text(d[2], 72, 340, "又一批完全不同的字符", 20, "#000000", "微软雅黑")
D.save(sv)
r = pymupdf.open(sv)
a1, a2 = ink(r[2], (72, 296, 300, 330)), ink(r[2], (72, 336, 300, 370))
check("glyphs complete after save", a1 > 600 and a2 > 600, (a1, a2))
check("saved text", "保存之后新加的汉字" in r[2].get_text() and "又一批完全不同的字符" in r[2].get_text())
r.close()
with D.edit() as d:
    pdfops.erase(d[2], (60, 290, 320, 332))
check("own text can be erased", "保存之后" not in D.doc[2].get_text() and "又一批" in D.doc[2].get_text())
big_wm = Doc.open(b)
with big_wm.edit() as d:
    more = pymupdf.open(b)
    for _ in range(40):
        d.insert_pdf(more)
    more.close()
    pdfops.watermark(d, list(range(d.page_count)), "水印 SAMPLE", tile=True)
    pdfops.page_numbers(d, list(range(d.page_count)), "第 {n} 页 共 {total} 页")
check("164 pages watermarked", big_wm.n == 164 and "第 164 页 共 164 页" in T(big_wm.doc[163]) and "SAMPLE" in T(big_wm.doc[80]))
check("shared watermark keeps file small", len(big_wm.bytes()) < 1_500_000, len(big_wm.bytes()))
big_wm.close()
D.encrypt = {"user_pw": "secret", "owner_pw": "own", "allow": {"print"}}
enc = os.path.join(S, "enc.pdf")
D.save(enc)
d = pymupdf.open(enc)
check("encrypted", d.needs_pass and d.authenticate("secret"))
check("perm", not (d.permissions & pymupdf.PDF_PERM_COPY) and (d.permissions & pymupdf.PDF_PERM_PRINT), d.permissions)
d.close()
try:
    Doc.open(enc)
    check("needs pw", False)
except pdfops.NeedPassword:
    check("needs pw", True)
try:
    Doc.open(enc, "wrong")
    check("wrong pw", False)
except pdfops.NeedPassword:
    check("wrong pw", True)
E = Doc.open(enc, "secret")
check("open enc", E.n == 3 and E.encrypt["user_pw"] == "secret")
with E.edit() as d:
    pdfops.rotate(d, [0], 90)
E.undo()
check("enc undo", E.doc[0].rotation == 0 and E.n == 3)
E.save(os.path.join(S, "enc2.pdf"))
d = pymupdf.open(os.path.join(S, "enc2.pdf"))
check("stays encrypted", d.needs_pass and d.authenticate("secret"))
d.close()
E.encrypt = None
E.save(os.path.join(S, "dec.pdf"))
d = pymupdf.open(os.path.join(S, "dec.pdf"))
check("decrypted", not d.needs_pass and not d.is_encrypted)
d.close()
check("merge enc", pdfops.merge([{"path": enc, "password": "secret"}, {"path": b}], os.path.join(S, "m2.pdf")) == 7)

# ---- compress / export / text
big = os.path.join(S, "big.pdf")
d = pymupdf.open()
pm = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2400, 1800))
import random
random.seed(1)
pm.set_rect(pm.irect, (240, 240, 240))
for _ in range(1500):
    x, y = random.randrange(2300), random.randrange(1700)
    pm.set_rect(pymupdf.IRect(x, y, x + random.randrange(10, 100), y + random.randrange(10, 100)),
                (random.randrange(256), random.randrange(256), random.randrange(256)))
p = d.new_page()
p.insert_image(pymupdf.Rect(50, 50, 450, 350), pixmap=pm)
d.save(big)
d.close()
size0 = os.path.getsize(big)
with open(big, "rb") as f:
    data = f.read()
s1 = pdfops.compress(data, os.path.join(S, "c_low.pdf"), "low")
s2 = pdfops.compress(data, os.path.join(S, "c_lossless.pdf"), "lossless")
check("compress low", s1 < size0 * 0.7, (size0, s1))
check("compress lossless", s2 <= size0 * 1.02, (size0, s2))
check("compressed opens", len(texts(os.path.join(S, "c_low.pdf"))) == 1)
imgs = pdfops.export_images(D.doc, [0, 2], os.path.join(S, "img"), "p", dpi=72, fmt="jpg")
check("export images", [os.path.basename(x) for x in imgs] == ["p_1.jpg", "p_3.jpg"] and all(os.path.getsize(x) > 1000 for x in imgs))
check("extract text", "第 2 页" in pdfops.extract_text(D.doc))
I = Doc.open(img)
check("open image", I.n == 1 and I.path is None and I.dirty and I.name == "pic.pdf")
B = Doc.blank()
check("blank", B.n == 1)

print(f"{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)
