"""PDF operations. No UI code here.

Page coordinates are always those of the page as displayed (points, origin top-left).
Functions that write content call _flat() first, which bakes a /Rotate entry into the
page so that displayed coordinates and content coordinates are the same thing.
"""
import math
import os
import re

import pymupdf
from pymupdf import Matrix, Point, Rect

from . import fonts

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")
A4 = (595.0, 842.0)


class NeedPassword(Exception):
    pass


# ---------------------------------------------------------------- open / save

def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXT


def image_to_pdf(path, page="image", margin=28.0):
    """page: "image" keeps the picture's own size, "a4" puts it on an A4 sheet."""
    img = pymupdf.open(path)
    try:
        one = pymupdf.open("pdf", img.convert_to_pdf())
    finally:
        img.close()
    if page != "a4":
        return one
    out = pymupdf.open()
    for p in one:
        w, h = (A4[1], A4[0]) if p.rect.width > p.rect.height else A4
        box = Rect(margin, margin, w - margin, h - margin)
        # small pictures are not blown up
        scale = min(box.width / p.rect.width, box.height / p.rect.height, 1.0)
        iw, ih = p.rect.width * scale, p.rect.height * scale
        x0, y0 = (w - iw) / 2, (h - ih) / 2
        out.new_page(width=w, height=h).show_pdf_page(Rect(x0, y0, x0 + iw, y0 + ih), one, p.number)
    one.close()
    return out


def load_bytes(data, password=None):
    """-> (document, password that opened it or None). The document is decrypted in memory."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    used = None
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            doc.close()
            raise NeedPassword()
        used = password
    if doc.is_encrypted or used or (doc.metadata or {}).get("encryption"):
        plain = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE)
        doc.close()
        doc = pymupdf.open(stream=plain, filetype="pdf")
    return doc, used


def load(path, password=None, image_page="image"):
    if is_image(path):
        return image_to_pdf(path, image_page), None
    with open(path, "rb") as f:
        data = f.read()
    return load_bytes(data, password)


def page_count(path, password=None):
    doc, _ = load(path, password)
    try:
        return doc.page_count
    finally:
        doc.close()


PERMS = {
    "print": pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ,
    "copy": pymupdf.PDF_PERM_COPY | pymupdf.PDF_PERM_ACCESSIBILITY,
    "modify": pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_ASSEMBLE,
    "annotate": pymupdf.PDF_PERM_ANNOTATE | pymupdf.PDF_PERM_FORM,
}


def save(doc, path, encrypt=None, garbage=3):
    """encrypt: None or dict(user_pw, owner_pw, allow=set of PERMS keys)."""
    kw = dict(garbage=garbage, deflate=True)
    if encrypt and (encrypt.get("user_pw") or encrypt.get("owner_pw")):
        perm = 0
        for k in encrypt.get("allow", PERMS.keys()):
            perm |= PERMS[k]
        owner = encrypt.get("owner_pw") or encrypt.get("user_pw")
        kw.update(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=owner,
                  user_pw=encrypt.get("user_pw") or "", permissions=perm)
    else:
        kw["encryption"] = pymupdf.PDF_ENCRYPT_NONE
    tmp = path + ".saving~"
    try:
        doc.save(tmp, **kw)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ---------------------------------------------------------------- pages

def copy_pages(dst, src, indexes, at=-1):
    """Append/insert pages of src (any order, repeats allowed) into dst."""
    runs = []
    for i in indexes:
        if runs and runs[-1][2] == 1 and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i, 1])
    pos = at
    for k, (a, b, _) in enumerate(runs):
        dst.insert_pdf(src, from_page=a, to_page=b, start_at=pos, final=(k == len(runs) - 1))
        if pos >= 0:
            pos += b - a + 1
    return len(indexes)


def rotate(doc, indexes, delta):
    for i in indexes:
        p = doc[i]
        p.set_rotation((p.rotation + delta) % 360)


def delete(doc, indexes):
    if len(set(indexes)) >= doc.page_count:
        raise ValueError("不能删除全部页面")
    doc.delete_pages(sorted(set(indexes)))


def reorder(doc, order):
    doc.select(list(order))


def insert_blank(doc, at, width=A4[0], height=A4[1]):
    doc.new_page(pno=at, width=width, height=height)


def insert_file(doc, path, at, password=None, ranges_idx=None, image_page="image"):
    src, _ = load(path, password, image_page)
    try:
        idx = list(range(src.page_count)) if ranges_idx is None else ranges_idx
        return copy_pages(doc, src, idx, at=at)
    finally:
        src.close()


def extract(doc, indexes, out_path):
    new = pymupdf.open()
    try:
        copy_pages(new, doc, indexes)
        save(new, out_path)
    finally:
        new.close()


# ---------------------------------------------------------------- merge / split

def merge(items, out_path, bookmarks=True, image_page="image", progress=None):
    """items: list of dict(path, password=None, pages=None or list of 0-based indexes)."""
    out = pymupdf.open()
    toc = []
    try:
        for n, it in enumerate(items):
            if progress and progress(n, len(items), it["path"]) is False:
                raise InterruptedError()
            src, _ = load(it["path"], it.get("password"), image_page)
            try:
                start = out.page_count
                pages = it.get("pages")
                whole = pages is None
                copy_pages(out, src, list(range(src.page_count)) if whole else pages)
                if out.page_count == start:
                    continue
                if bookmarks:
                    title = os.path.splitext(os.path.basename(it["path"]))[0]
                    toc.append([1, title, start + 1])
                if whole:
                    for lvl, title, pno, *_ in src.get_toc():
                        if 1 <= pno <= src.page_count:
                            toc.append([lvl + (1 if bookmarks else 0), title, start + pno])
            finally:
                src.close()
        if out.page_count == 0:
            raise ValueError("没有可合并的页面")
        if toc:
            try:
                out.set_toc(_fix_toc(toc))
            except Exception:
                pass
        save(out, out_path)
        return out.page_count
    finally:
        out.close()


def _fix_toc(toc):
    """set_toc wants the first level to be 1 and no jumps of more than one level."""
    fixed, prev = [], 0
    for lvl, title, pno in toc:
        lvl = max(1, min(lvl, prev + 1))
        fixed.append([lvl, title or " ", pno])
        prev = lvl
    return fixed


def safe_name(text, limit=60):
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", text).strip(" .")
    return text[:limit] or "未命名"


def groups_every(n_pages, size):
    size = max(1, int(size))
    return [list(range(a, min(a + size, n_pages))) for a in range(0, n_pages, size)]


def groups_bookmarks(doc):
    """-> list of (title, indexes) from the top-level bookmarks."""
    tops = [(t, p - 1) for lvl, t, p, *_ in doc.get_toc() if lvl == 1 and 1 <= p <= doc.page_count]
    starts = []
    for t, p in tops:
        if starts and starts[-1][1] == p:
            continue
        if starts and p < starts[-1][1]:
            continue
        starts.append((t, p))
    if not starts:
        return []
    out = []
    if starts[0][1] > 0:
        out.append(("前置页", list(range(0, starts[0][1]))))
    for k, (t, p) in enumerate(starts):
        end = starts[k + 1][1] if k + 1 < len(starts) else doc.page_count
        out.append((t, list(range(p, end))))
    return out


def split(doc, groups, folder, stem, names=None, progress=None):
    """Write one file per group. -> list of written paths."""
    os.makedirs(folder, exist_ok=True)
    written, used = [], set()
    width = len(str(len(groups)))
    for k, idx in enumerate(groups):
        if not idx:
            continue
        if progress and progress(k, len(groups), "") is False:
            raise InterruptedError()
        if names:
            label = f"{str(k + 1).zfill(width)}_{safe_name(names[k])}"
        elif len(idx) == 1:
            label = f"第{idx[0] + 1}页"
        elif idx == list(range(idx[0], idx[-1] + 1)):
            label = f"第{idx[0] + 1}-{idx[-1] + 1}页"
        else:
            label = f"部分{str(k + 1).zfill(width)}"
        name, n = f"{stem}_{label}", 2
        while name.lower() in used:
            name = f"{stem}_{label}_{n}"
            n += 1
        used.add(name.lower())
        path = os.path.join(folder, name + ".pdf")
        extract(doc, idx, path)
        written.append(path)
    return written


# ---------------------------------------------------------------- content

def _flat(page):
    if page.rotation:
        page.remove_rotation()
    if not page.is_wrapped:
        # without this, text written later inherits the page's leftover graphics state
        page.wrap_contents()
    return page


def rgb(color):
    """"#rrggbb" or tuple -> (r, g, b) floats."""
    if isinstance(color, str):
        c = color.lstrip("#")
        return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(color)


def line_height(font, size):
    return (font.ascender - font.descender) * size


class _TextLayer:
    """Text is first written on scratch pages, reduced to the glyphs actually used, and then
    stamped onto the real pages. Writing straight into the document would embed the whole
    font file (19 MB for Microsoft YaHei) on the first character."""

    def __init__(self):
        self.tmp = pymupdf.open()
        self.jobs = []

    def page(self, target):
        """A scratch page of the same size as target; what is written on it lands on target."""
        pg = self.tmp.new_page(width=target.rect.width, height=target.rect.height)
        self.jobs.append((target, pg.number))
        return pg

    def also(self, target, scratch_number):
        """Stamp an already written scratch page onto one more page."""
        self.jobs.append((target, scratch_number))

    def stamp(self):
        try:
            if not self.jobs:
                return
            self.tmp.subset_fonts()
            small = pymupdf.open(stream=self.tmp.tobytes(garbage=3, deflate=True), filetype="pdf")
            try:
                for target, n in self.jobs:
                    target.show_pdf_page(target.rect, small, n)
            finally:
                small.close()
        finally:
            self.tmp.close()


def add_text(page, x, y, text, size, color, font_name="微软雅黑", bold=False, opacity=1.0,
             ascent=None, line_h=None):
    """(x, y) is the top-left corner of the first line. ascent / line_h (points) let the
    caller impose the metrics of an on-screen preview."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    if not text.strip():
        return False
    _flat(page)
    font = fonts.for_text(text, font_name, bold)
    layer = _TextLayer()
    pg = layer.page(page)
    tw = pymupdf.TextWriter(pg.rect)
    lh = line_h or line_height(font, size)
    base = y + (ascent if ascent is not None else font.ascender * size)
    for i, line in enumerate(text.split("\n")):
        if line.strip():
            tw.append(Point(x, base + i * lh), line, font=font, fontsize=size)
    tw.write_text(pg, color=rgb(color), opacity=opacity)
    layer.stamp()
    return True


def text_size(text, size, font_name="微软雅黑", bold=False):
    font = fonts.for_text(text, font_name, bold)
    lines = text.split("\n")
    return max(font.text_length(l, size) for l in lines), line_height(font, size) * len(lines)


def add_image(page, rect, data=None, path=None):
    _flat(page)
    kw = {"stream": data} if data is not None else {"filename": path}
    page.insert_image(Rect(rect), keep_proportion=False, overlay=True, **kw)


def draw(page, kind, pts, color, width=1.5, fill=None, opacity=1.0):
    """kind: rect, ellipse, line, arrow, pen. pts: list of (x, y)."""
    _flat(page)
    pts = [Point(p) for p in pts]
    if len(pts) < 2:
        return False
    color = rgb(color)
    fill = rgb(fill) if fill else None
    sh = page.new_shape()
    style = dict(color=color, width=width, lineCap=1, lineJoin=1,
                 stroke_opacity=opacity, fill_opacity=opacity)
    if kind in ("rect", "ellipse"):
        r = Rect(pts[0], pts[-1]).normalize()
        if r.width < 0.5 or r.height < 0.5:
            return False
        (sh.draw_rect if kind == "rect" else sh.draw_oval)(r)
        sh.finish(fill=fill, **style)
    elif kind == "line":
        sh.draw_line(pts[0], pts[-1])
        sh.finish(closePath=False, **style)
    elif kind == "arrow":
        a, b = pts[0], pts[-1]
        length = math.hypot(b.x - a.x, b.y - a.y)
        if length < 1:
            return False
        ux, uy = (b.x - a.x) / length, (b.y - a.y) / length
        head = min(max(width * 4.5, 8.0), length * 0.6)
        base = Point(b.x - ux * head, b.y - uy * head)
        half = head * 0.38
        sh.draw_line(a, base)
        sh.finish(closePath=False, **style)
        sh.draw_polyline([b, Point(base.x - uy * half, base.y + ux * half),
                          Point(base.x + uy * half, base.y - ux * half), b])
        sh.finish(color=color, fill=color, width=0.1, stroke_opacity=opacity, fill_opacity=opacity)
    elif kind == "pen":
        sh.draw_polyline(pts)
        sh.finish(closePath=False, **style)
    else:
        raise ValueError(kind)
    sh.commit()
    return True


def markup(page, rect, kind, color):
    """Highlight / underline / strikeout the words inside rect.
    -> "annot" when words were found, "box" when a translucent box was drawn instead."""
    _flat(page)
    rect = Rect(rect).normalize()
    words = page.get_text("words", clip=rect)
    lines = {}
    for w in words:
        r = Rect(w[:4])
        key = (w[5], w[6])
        lines[key] = (lines[key] | r) if key in lines else r
    if lines:
        quads = [r.quad for r in lines.values()]
        fn = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot,
              "strike": page.add_strikeout_annot}[kind]
        annot = fn(quads)
        annot.set_colors(stroke=rgb(color))
        annot.update()
        return "annot"
    if rect.width < 1 or rect.height < 1:
        return ""
    sh = page.new_shape()
    if kind == "highlight":
        sh.draw_rect(rect)
        sh.finish(color=None, fill=rgb(color), fill_opacity=0.35, width=0)
    else:
        y = rect.y1 if kind == "underline" else (rect.y0 + rect.y1) / 2
        sh.draw_line(Point(rect.x0, y), Point(rect.x1, y))
        sh.finish(color=rgb(color), width=1.2, closePath=False)
    sh.commit()
    return "box"


def erase(page, rect, fill="#ffffff"):
    """Really removes what is under rect (text, picture pixels), then paints it."""
    _flat(page)
    rect = Rect(rect).normalize()
    if rect.width < 0.5 or rect.height < 0.5:
        return False
    page.add_redact_annot(rect, fill=rgb(fill), cross_out=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
    return True


def _int_rgb(v):
    return ((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255


def text_lines(page):
    """Every horizontal text line of the page, in displayed coordinates."""
    # text extraction reports unrotated coordinates: bring them into displayed ones
    rot = page.rotation_matrix if page.rotation else None
    data = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)
    out = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            box = Rect(line["bbox"])
            dx, dy = line.get("dir", (1, 0))
            if rot:
                box = (box * rot).normalize()
                dx, dy = dx * rot.a + dy * rot.c, dx * rot.b + dy * rot.d
            if abs(dy) > 0.05 or dx <= 0:
                continue
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            s0 = spans[0]
            big = max(spans, key=lambda s: len(s["text"]))
            out.append(dict(
                bbox=tuple(box), text="".join(s["text"] for s in line["spans"]).rstrip(),
                size=round(big["size"], 2), color=_int_rgb(big["color"]),
                origin=tuple(Point(s0["origin"]) * rot) if rot else tuple(s0["origin"]),
                bold=bool(big["flags"] & 16), serif=bool(big["flags"] & 4), font=big["font"]))
    return out


def pick_line(lines, x, y):
    best = None
    for ln in lines:
        b = ln["bbox"]
        if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
            if best is None or (b[2] - b[0]) * (b[3] - b[1]) < (best["bbox"][2] - best["bbox"][0]) * (best["bbox"][3] - best["bbox"][1]):
                best = ln
    return best


def text_line_at(page, x, y):
    """The horizontal text line under a point, or None."""
    return pick_line(text_lines(page), x, y)


def guess_font(line):
    """A Windows font that looks roughly like the original one."""
    name = (line.get("font") or "").lower()
    for key, font in (("simsun", "宋体"), ("song", "宋体"), ("kai", "楷体"), ("fang", "仿宋"),
                      ("hei", "黑体"), ("yahei", "微软雅黑"), ("times", "Times New Roman"),
                      ("arial", "Arial"), ("helvetica", "Arial")):
        if key in name:
            return font
    if fonts.has_cjk(line.get("text", "")):
        return "宋体" if line.get("serif") else "微软雅黑"
    return "Times New Roman" if line.get("serif") else "Arial"


def replace_text(page, line, new_text, size=None, color=None, font_name=None, bold=None):
    """Remove one text line (pictures and drawings under it stay) and write new text there."""
    rotated = bool(page.rotation)
    _flat(page)
    if rotated:
        # coordinates of the line were taken before the rotation was baked in: look it up again
        box = Rect(line["bbox"])
        again = text_line_at(page, (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
        if again:
            line = dict(line, bbox=again["bbox"], origin=again["origin"])
    box = Rect(line["bbox"])
    inset = box.height * 0.2
    page.add_redact_annot(Rect(box.x0 - 0.5, box.y0 + inset, box.x1 + 0.5, box.y1 - inset),
                          fill=False, cross_out=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
    new_text = (new_text or "").replace("\n", " ")
    if not new_text.strip():
        return
    size = size or line["size"]
    font = fonts.for_text(new_text, font_name or guess_font(line),
                          line.get("bold") if bold is None else bold)
    layer = _TextLayer()
    pg = layer.page(page)
    tw = pymupdf.TextWriter(pg.rect)
    tw.append(Point(line["origin"]), new_text, font=font, fontsize=size)
    tw.write_text(pg, color=rgb(color if color is not None else line["color"]))
    layer.stamp()


# ---------------------------------------------------------------- whole-document tools

def watermark(doc, indexes, text, size=48, color="#888888", opacity=0.25, angle=45,
              tile=False, font_name="微软雅黑"):
    text = text.strip()
    if not text:
        return
    font = fonts.for_text(text, font_name)
    length = font.text_length(text, size)
    layer = _TextLayer()
    made = {}       # page size -> scratch page, so equal pages share one watermark object
    for i in indexes:
        page = _flat(doc[i])
        r = page.rect
        key = (round(r.width, 1), round(r.height, 1))
        if key in made:
            layer.also(page, made[key])
            continue
        pg = layer.page(page)
        made[key] = pg.number
        c = Point(r.width / 2, r.height / 2)
        tw = pymupdf.TextWriter(r)
        if tile:
            reach = math.hypot(r.width, r.height) / 2 + size
            sx, sy = length + size * 2.5, size * 4.5
            ny, nx = int(reach // sy) + 1, int(reach // sx) + 1
            for row in range(-ny, ny + 1):
                shift = sx / 2 if row % 2 else 0
                for col in range(-nx, nx + 1):
                    tw.append(Point(c.x + col * sx + shift - length / 2, c.y + row * sy + size * 0.35),
                              text, font=font, fontsize=size)
        else:
            tw.append(Point(c.x - length / 2, c.y + size * 0.35), text, font=font, fontsize=size)
        tw.write_text(pg, color=rgb(color), opacity=opacity, morph=(c, Matrix(angle)))
    layer.stamp()


POSITIONS = ("bc", "br", "bl", "tc", "tr", "tl")


def page_numbers(doc, indexes, fmt="{n} / {total}", pos="bc", size=10, color="#000000",
                 start=1, margin=28, font_name="Arial"):
    total = start + len(indexes) - 1
    layer = _TextLayer()
    for k, i in enumerate(indexes):
        page = _flat(doc[i])
        text = fmt.replace("{n}", str(start + k)).replace("{total}", str(total))
        font = fonts.for_text(text, font_name)
        length = font.text_length(text, size)
        r = page.rect
        x = {"l": margin, "c": (r.width - length) / 2, "r": r.width - margin - length}[pos[1]]
        y = margin + size * 0.8 if pos[0] == "t" else r.height - margin
        pg = layer.page(page)
        tw = pymupdf.TextWriter(r)
        tw.append(Point(x, y), text, font=font, fontsize=size)
        tw.write_text(pg, color=rgb(color))
    layer.stamp()


COMPRESS = {  # level: (dpi threshold, dpi target, jpeg quality)
    "lossless": None,
    "high": (250, 200, 85),
    "medium": (200, 150, 75),
    "low": (130, 96, 60),
}


def compress(data, out_path, level="medium"):
    """data: bytes of the PDF. -> size of the written file."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        preset = COMPRESS[level]
        if preset:
            thr, target, q = preset
            doc.rewrite_images(dpi_threshold=thr, dpi_target=target, quality=q)
            if not doc.is_form_pdf:     # fillable forms need their complete fonts
                try:
                    doc.subset_fonts()
                except Exception:
                    pass
        tmp = out_path + ".saving~"
        doc.save(tmp, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True,
                 use_objstms=1, encryption=pymupdf.PDF_ENCRYPT_NONE)
        os.replace(tmp, out_path)
        return os.path.getsize(out_path)
    finally:
        doc.close()


def export_images(doc, indexes, folder, stem, dpi=150, fmt="png", progress=None):
    os.makedirs(folder, exist_ok=True)
    width = len(str(doc.page_count))
    out = []
    for k, i in enumerate(indexes):
        if progress and progress(k, len(indexes), "") is False:
            raise InterruptedError()
        pix = doc[i].get_pixmap(dpi=dpi, alpha=False)
        path = os.path.join(folder, f"{stem}_{str(i + 1).zfill(width)}.{fmt}")
        if fmt == "jpg":
            pix.save(path, jpg_quality=90)
        else:
            pix.save(path)
        out.append(path)
    return out


def extract_text(doc, indexes=None):
    idx = range(doc.page_count) if indexes is None else indexes
    parts = []
    for i in idx:
        parts.append(f"===== 第 {i + 1} 页 =====\n{doc[i].get_text().strip()}\n")
    return "\n".join(parts)
