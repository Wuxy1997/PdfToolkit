"""Fonts used for text written into a PDF. Windows fonts are embedded (and subset on save)."""
import os

import pymupdf

WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

# display name -> (regular file, bold file, Qt family)
FONTS = {
    "微软雅黑": ("msyh.ttc", "msyhbd.ttc", "Microsoft YaHei"),
    "宋体": ("simsun.ttc", None, "SimSun"),
    "黑体": ("simhei.ttf", None, "SimHei"),
    "楷体": ("simkai.ttf", None, "KaiTi"),
    "仿宋": ("simfang.ttf", None, "FangSong"),
    "Arial": ("arial.ttf", "arialbd.ttf", "Arial"),
    "Times New Roman": ("times.ttf", "timesbd.ttf", "Times New Roman"),
}

_cache = {}


def names():
    return [n for n, (f, _, _) in FONTS.items() if os.path.exists(os.path.join(WIN, f))] or ["内置字体"]


def qt_family(name):
    return FONTS.get(name, (None, None, "Microsoft YaHei"))[2]


def get(name, bold=False):
    """A pymupdf.Font. Falls back to the built-in CJK font when the file is missing."""
    key = (name, bool(bold))
    if key in _cache:
        return _cache[key]
    font = None
    reg, bd, _ = FONTS.get(name, (None, None, None))
    for fn in ((bd if bold else None), reg):
        if fn and os.path.exists(os.path.join(WIN, fn)):
            try:
                font = pymupdf.Font(fontfile=os.path.join(WIN, fn))
                break
            except Exception:
                font = None
    if font is None:
        font = pymupdf.Font("cjk")
    _cache[key] = font
    return font


def has_cjk(text):
    return any(ord(c) > 0x2E7F for c in text)


def for_text(text, name, bold=False):
    """Latin-only fonts cannot draw Chinese: switch to YaHei when the text needs it."""
    font = get(name, bold)
    if all(font.has_glyph(ord(c)) for c in text if not c.isspace()):
        return font
    return get("微软雅黑", bold)
