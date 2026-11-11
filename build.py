"""Build the portable exe and zip.

    .venv\\Scripts\\python.exe build.py            ->  dist\\PDF工具箱.exe
                                                     dist\\PdfToolkit-v<ver>-portable.zip
"""
import os
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from core.version import APP_ID, APP_NAME, VERSION

DIST = os.path.join(ROOT, "dist")
WORK = os.path.join(ROOT, "build")

EXCLUDE = ["tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
           "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSvg",
           "PySide6.QtDBus", "PySide6.QtConcurrent", "PySide6.QtXml", "numpy", "PIL"]

# Bundled by the hooks but never used here (about 55 MB): PyMuPDF's layout-analysis models and
# C headers, Qt's software OpenGL, network / SVG / PDF plugins, translations other than Chinese.
DROP = ["pymupdf/layout/resources", "pymupdf/mupdf-devel", "opengl32sw.dll", "qt6network", "qt6svg", "qt6pdf",
        "qt6quick", "qt6qml", "qt6opengl", "qdirect2d", "qminimal", "qoffscreen", "plugins/tls",
        "plugins/networkinformation", "plugins/generic", "plugins/iconengines", "qsvg", "qpdf.dll"]

SPEC = """# -*- mode: python ; coding: utf-8 -*-
DROP = {drop!r}


def keep(entry):
    name = entry[0].replace("\\\\", "/").lower()
    if "/translations/" in name:
        return "qtbase_zh_cn" in name
    return not any(bad in name for bad in DROP)


a = Analysis([{main!r}], pathex=[{root!r}], datas=[({ico!r}, "assets")], excludes={excludes!r})
a.binaries = [e for e in a.binaries if keep(e)]
a.datas = [e for e in a.datas if keep(e)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name={name!r}, console=False, icon={ico!r},
          upx=False, runtime_tmpdir=None, version={ver_file!r})
"""

# What Explorer shows under Properties > Details; App Hub reads the installed version from here.
VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({v}, 0), prodvers=({v}, 0), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904b0', [
      StringStruct('FileDescription', 'PDF Toolkit - split, merge, edit and sign PDF files'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', '{app_id}'),
      StringStruct('OriginalFilename', '{name}.exe'),
      StringStruct('ProductName', 'PDF Toolkit'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

GUIDE_ZH = f"""{APP_NAME} {VERSION}（绿色版）
====================================

使用方法
  双击 “{APP_NAME}.exe” 即可，无需安装。
  也可以把 PDF 文件拖到 exe 图标上直接打开。

界面语言
  第一次打开时跟随 Windows 的语言。
  点右上角的“设置”可以在中文和 English 之间切换，整个界面立即切换。

功能
  · 合并：多个 PDF / 图片合成一个 PDF，可只取每个文件的部分页
  · 拆分：按页码范围、每 N 页、每页、按书签拆分，或提取部分页
  · 页面：旋转、删除、拖动排序、插入其他文件的页面或空白页
  · 编辑：加文字、修改已有文字、插入图片、高亮/下划线/删除线、
          画笔/直线/箭头/方框/圆圈、擦除、涂黑（真正删除内容）
  · 签名：手写、从照片导入（自动去背景）、输入姓名生成；可保存多个签名
  · 其他：水印、页码、密码保护、压缩、导出图片、导出文字、打印

说明
  · 所有处理都在本机完成，文件不会上传到任何地方。
  · 设置和保存的签名放在 exe 旁边的 data 文件夹里；
    换电脑时把整个文件夹一起拷走即可。删除本文件夹即卸载。
  · 需要 Windows 10 / 11（64 位）。

源代码与许可（AGPL-3.0）：https://github.com/Wuxy1997/{APP_ID}
"""

GUIDE_EN = f"""PDF Toolkit {VERSION} (portable)
====================================

How to use
  Double-click "{APP_NAME}.exe". Nothing needs to be installed.
  You can also drop a PDF file onto the exe to open it.

Language
  The first time, the program follows the language of Windows.
  Click Settings (top right) to switch between 中文 and English;
  the whole interface changes at once.

What it does
  - Merge: several PDFs / images into one PDF, optionally only some
    pages of each file
  - Split: by page ranges, every N pages, one file per page, by
    bookmarks, or extract some pages
  - Pages: rotate, delete, drag to reorder, insert pages from another
    file or blank pages
  - Edit: add text, change existing text, insert images, highlight /
    underline / strikeout, pen / line / arrow / box / ellipse, erase,
    redact (the content is really removed)
  - Signature: draw it, import a photo (the paper background is removed)
    or type a name; several signatures can be saved
  - Also: watermark, page numbers, password protection, compress,
    export images, export text, print

Notes
  - Everything is processed on this PC; no file is uploaded anywhere.
  - Settings and saved signatures are kept in the "data" folder next to
    the exe. Copy the whole folder along when you move to another PC.
    To uninstall, delete this folder.
  - Needs Windows 10 / 11 (64-bit).

Source code and licence (AGPL-3.0): https://github.com/Wuxy1997/{APP_ID}
"""


def make_ico(png, ico):
    """Multi-size .ico (PNG-compressed entries) from one big PNG, using Qt only."""
    from PySide6.QtCore import QBuffer, Qt
    from PySide6.QtGui import QImage
    src = QImage(png)
    blobs = []
    for s in (16, 24, 32, 48, 64, 128, 256):
        buf = QBuffer()
        buf.open(QBuffer.WriteOnly)
        src.scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(buf, "PNG")
        blobs.append((s, bytes(buf.data())))
    with open(ico, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(blobs)))
        offset = 6 + 16 * len(blobs)
        for s, data in blobs:
            f.write(struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset))
            offset += len(data)
        for _, data in blobs:
            f.write(data)


def main():
    png = os.path.join(ROOT, "assets", "app.png")
    ico = os.path.join(ROOT, "assets", "app.ico")
    if not os.path.exists(png):
        subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "make_icon.py")])
    from PySide6.QtGui import QGuiApplication
    _app = QGuiApplication.instance() or QGuiApplication([])
    make_ico(png, ico)

    os.makedirs(WORK, exist_ok=True)
    spec = os.path.join(WORK, APP_ID + ".spec")
    ver_file = os.path.join(WORK, "version_info.txt")
    with open(ver_file, "w", encoding="utf-8") as f:
        f.write(VERSION_INFO.format(v=VERSION.replace(".", ", "), ver=VERSION, app_id=APP_ID, name=APP_NAME))
    with open(spec, "w", encoding="utf-8") as f:
        f.write(SPEC.format(main=os.path.join(ROOT, "main.py"), root=ROOT, ico=ico, name=APP_NAME,
                            excludes=EXCLUDE, drop=DROP, ver_file=ver_file))
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                           "--distpath", DIST, "--workpath", WORK, spec], cwd=ROOT)

    exe = os.path.join(DIST, APP_NAME + ".exe")
    zpath = os.path.join(DIST, f"{APP_ID}-v{VERSION}-portable.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(exe, f"{APP_NAME}/{APP_NAME}.exe")
        for name, text in (("使用说明.txt", GUIDE_ZH), ("User Guide.txt", GUIDE_EN)):    # one guide per language
            z.writestr(f"{APP_NAME}/{name}", text.replace("\n", "\r\n").encode("utf-8-sig"))
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"exe: {exe}  ({os.path.getsize(exe) / 1048576:.1f} MB)")
    print(f"zip: {zpath}  ({os.path.getsize(zpath) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
