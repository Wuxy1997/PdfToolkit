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
          upx=False, runtime_tmpdir=None)
"""

README = f"""{APP_NAME} {VERSION}（绿色版）
====================================

使用方法
  双击 “{APP_NAME}.exe” 即可，无需安装。
  也可以把 PDF 文件拖到 exe 图标上直接打开。

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
    with open(spec, "w", encoding="utf-8") as f:
        f.write(SPEC.format(main=os.path.join(ROOT, "main.py"), root=ROOT, ico=ico, name=APP_NAME,
                            excludes=EXCLUDE, drop=DROP))
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                           "--distpath", DIST, "--workpath", WORK, spec], cwd=ROOT)

    exe = os.path.join(DIST, APP_NAME + ".exe")
    zpath = os.path.join(DIST, f"{APP_ID}-v{VERSION}-portable.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(exe, f"{APP_NAME}/{APP_NAME}.exe")
        z.writestr(f"{APP_NAME}/使用说明.txt", README.replace("\n", "\r\n").encode("utf-8-sig"))
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"exe: {exe}  ({os.path.getsize(exe) / 1048576:.1f} MB)")
    print(f"zip: {zpath}  ({os.path.getsize(zpath) / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
