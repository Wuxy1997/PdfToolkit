"""Draw the app icon. Usage: python tools/make_icon.py  (writes assets/app.png, 512 px)
The .ico is made from it by build.py."""
import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def draw(size=512):
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    p.scale(size / 512, size / 512)
    # tile
    g = QLinearGradient(0, 0, 512, 512)
    g.setColorAt(0, QColor("#2a3552"))
    g.setColorAt(1, QColor("#141a2b"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(QRectF(16, 16, 480, 480), 104, 104)
    # back sheet
    p.save()
    p.translate(256, 262)
    p.rotate(-9)
    p.setBrush(QColor("#5a6890"))
    p.drawRoundedRect(QRectF(-128, -168, 250, 330), 22, 22)
    p.restore()
    # front sheet with folded corner
    sheet = QPainterPath()
    x, y, w, h, c = 140, 86, 256, 338, 70
    sheet.moveTo(x + 22, y)
    sheet.lineTo(x + w - c, y)
    sheet.lineTo(x + w, y + c)
    sheet.lineTo(x + w, y + h - 22)
    sheet.quadTo(x + w, y + h, x + w - 22, y + h)
    sheet.lineTo(x + 22, y + h)
    sheet.quadTo(x, y + h, x, y + h - 22)
    sheet.lineTo(x, y + 22)
    sheet.quadTo(x, y, x + 22, y)
    p.setBrush(QColor("#ffffff"))
    p.drawPath(sheet)
    fold = QPainterPath()
    fold.moveTo(x + w - c, y)
    fold.lineTo(x + w - c, y + c - 16)
    fold.quadTo(x + w - c, y + c, x + w - c + 16, y + c)
    fold.lineTo(x + w, y + c)
    fold.closeSubpath()
    p.setBrush(QColor("#c9cfdd"))
    p.drawPath(fold)
    # red tag
    p.setBrush(QColor("#e5484d"))
    p.drawRoundedRect(QRectF(104, 150, 208, 92), 20, 20)
    f = QFont("Arial Black")
    f.setPixelSize(70)
    p.setFont(f)
    p.setPen(Qt.white)
    p.drawText(QRectF(104, 148, 208, 92), Qt.AlignCenter, "PDF")
    # text lines
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#c9cfdd"))
    for i, wd in enumerate((176, 140)):
        p.drawRoundedRect(QRectF(176, 268 + i * 30, wd, 13), 6, 6)
    # signature
    sig = QPainterPath()
    sig.moveTo(172, 384)
    sig.cubicTo(200, 318, 222, 408, 250, 352)
    sig.cubicTo(270, 314, 286, 396, 318, 360)
    sig.cubicTo(332, 344, 348, 356, 366, 346)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#1a3fb5"), 13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(sig)
    p.end()
    return img


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    out = os.path.join(ROOT, "assets", "app.png")
    draw().save(out)
    print(out)
