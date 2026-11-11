"""The page view: continuous scrolling, zoom, and the editing tools.

Scene units are PDF points, so everything placed on a page is zoom independent.
Text, pictures and signatures first appear as a floating item that can be moved or
resized; it is written into the PDF when the user clicks elsewhere or presses Enter.
"""
import bisect
import math

import pymupdf
from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QCursor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath,
                           QPen, QTransform)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QGraphicsRectItem,
                               QGraphicsScene, QGraphicsTextItem, QGraphicsView)

from core import fonts, pdfops
from core.i18n import tr

from .common import BLUE, CANVAS

GAP = 14.0
PX_PER_PT = 96.0 / 72.0
MAX_PIXELS = 36_000_000
SHAPES = ("rect", "ellipse", "line", "arrow", "pen")
MARKS = ("highlight", "underline", "strike")
AREAS = ("erase", "redact")
DRAG_TOOLS = SHAPES + MARKS + AREAS


class PageItem(QGraphicsItem):
    def __init__(self, view, index, w, h):
        super().__init__()
        self.view, self.index, self.w, self.h = view, index, w, h

    def boundingRect(self):
        return QRectF(-1, -1, self.w + 6, self.h + 6)

    def rect(self):
        return QRectF(0, 0, self.w, self.h)

    def paint(self, p, opt, widget=None):
        p.fillRect(QRectF(3, 3, self.w, self.h), QColor(0, 0, 0, 80))
        p.fillRect(self.rect(), Qt.white)
        img = self.view.image_for(self.index)
        if img is not None:
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.drawImage(self.rect(), img)


class Grip(QGraphicsItem):
    """Small handle that drags its parent (a text box takes mouse drags for selecting text)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setCursor(Qt.SizeAllCursor)
        self.setZValue(5)
        self._last = None

    def boundingRect(self):
        return QRectF(-24, -24, 22, 22)

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BLUE))
        p.drawRoundedRect(QRectF(-23, -23, 20, 20), 4, 4)
        p.setPen(QPen(Qt.white, 1.6))
        c = QPointF(-13, -13)
        for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
            p.drawLine(c, c + QPointF(dx, dy))
            for s in (-1, 1):
                p.drawLine(c + QPointF(dx, dy), c + QPointF(dx * 0.55 + s * dy * 0.45, dy * 0.55 + s * dx * 0.45))

    def mousePressEvent(self, e):
        self._last = e.scenePos()
        e.accept()

    def mouseMoveEvent(self, e):
        if self._last is not None:
            d = e.scenePos() - self._last
            self._last = e.scenePos()
            self.parentItem().moveBy(d.x(), d.y())

    def mouseReleaseEvent(self, e):
        self._last = None


class FloatText(QGraphicsTextItem):
    def __init__(self, view, text=""):
        super().__init__()
        self.view = view
        self.setZValue(10)
        self.document().setDocumentMargin(1.5)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setPlainText(text)
        self.grip = Grip(self)
        self.font_name, self.size, self.color = "微软雅黑", 12, "#000000"

    def apply(self, font_name, size, color):
        self.font_name, self.size, self.color = font_name, size, color
        f = QFont(fonts.qt_family(font_name))
        f.setPixelSize(max(1, int(round(size))))
        f.setHintingPreference(QFont.PreferNoHinting)
        self.setFont(f)
        self.setDefaultTextColor(QColor(color))

    def paint(self, p, opt, widget=None):
        r = self.boundingRect()
        if not self.toPlainText():
            r = QRectF(0, 0, max(r.width(), self.size * 5.2), r.height())
            p.setPen(QColor("#9aa2b3"))
            p.setFont(self.font())
            p.drawText(r.adjusted(1.5, 1.5, 0, 0), Qt.AlignLeft | Qt.AlignTop, tr("在此输入文字"))
        opt.state &= ~(opt.state.State_HasFocus | opt.state.State_Selected)
        super().paint(p, opt, widget)
        pen = QPen(QColor(BLUE), 0, Qt.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(r)

    def boundingRect(self):
        r = super().boundingRect()
        if not self.toPlainText():
            return QRectF(0, 0, max(r.width(), self.size * 5.2), r.height())
        return r

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.view.cancel_float()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter) and e.modifiers() & Qt.ControlModifier:
            self.view.commit_float()
        else:
            super().keyPressEvent(e)


class FloatImage(QGraphicsObject):
    def __init__(self, view, image, data, w, h):
        super().__init__()
        self.view, self.image, self.data = view, image, data
        self.w, self.h = w, h
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self._mode = None

    def _m(self):
        return 9.0 / self.view.k      # handle size in scene units

    def boundingRect(self):
        m = self._m()
        return QRectF(-m, -m, self.w + 2 * m, self.h + 2 * m)

    def zoom_changed(self):
        self.prepareGeometryChange()

    def paint(self, p, opt, widget=None):
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        r = QRectF(0, 0, self.w, self.h)
        p.drawImage(r, self.image)
        p.setPen(QPen(QColor(BLUE), 0, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(r)
        m = self._m()
        p.setPen(QPen(Qt.white, 0))
        p.setBrush(QColor(BLUE))
        for c in self._corners():
            p.drawRect(QRectF(c.x() - m / 2, c.y() - m / 2, m, m))

    def _corners(self):
        return [QPointF(0, 0), QPointF(self.w, 0), QPointF(self.w, self.h), QPointF(0, self.h)]

    def _corner_at(self, pos):
        m = self._m()
        for i, c in enumerate(self._corners()):
            if abs(pos.x() - c.x()) <= m and abs(pos.y() - c.y()) <= m:
                return i
        return None

    def hoverMoveEvent(self, e):
        i = self._corner_at(e.pos())
        self.setCursor(Qt.SizeAllCursor if i is None else (Qt.SizeFDiagCursor if i in (0, 2) else Qt.SizeBDiagCursor))

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return e.ignore()
        i = self._corner_at(e.pos())
        self._mode = ("move", e.scenePos(), self.pos()) if i is None else \
            ("size", i, self.mapToScene(self._corners()[(i + 2) % 4]), self.w / self.h)
        self.setFocus()
        e.accept()

    def mouseMoveEvent(self, e):
        if not self._mode:
            return
        if self._mode[0] == "move":
            _, start, pos0 = self._mode
            self.setPos(pos0 + e.scenePos() - start)
            return
        _, i, anchor, ratio = self._mode
        d = e.scenePos() - anchor
        w = max(abs(d.x()), abs(d.y()) * ratio, 6.0)
        h = w / ratio
        self.prepareGeometryChange()
        self.w, self.h = w, h
        # the anchor is the corner opposite to the dragged one
        x = anchor.x() if i in (1, 2) else anchor.x() - w
        y = anchor.y() if i in (2, 3) else anchor.y() - h
        self.setPos(x, y)
        self.update()

    def mouseReleaseEvent(self, e):
        self._mode = None


class PdfView(QGraphicsView):
    pageChanged = Signal(int)
    zoomChanged = Signal(float)
    edited = Signal(object)          # set of page indexes or None
    failed = Signal(str, object)
    toolChanged = Signal(str)
    lineClicked = Signal(int, object)
    hint = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QBrush(QColor(CANVAS)))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(False)
        self.dm = None
        self.zoom = 1.0
        self.k = PX_PER_PT
        self.tool = "select"
        self.opts = {"color": "#d32f2f", "hl_color": "#ffeb3b", "text_color": "#000000",
                     "width": 1.5, "font": "微软雅黑", "size": 12}
        self._items, self._ys, self._sizes = [], [], []
        self._cache, self._want = {}, set()
        self._lines = {}
        self._float = None
        self._drag = None
        self._hover = None
        self._payload = None
        self._cur = -1
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._render_some)
        self.verticalScrollBar().valueChanged.connect(self._scrolled)
        self._apply_zoom()

    # ------------------------------------------------------------ document / layout
    def set_doc(self, dm):
        self.cancel_float()
        self.dm = dm
        self._cache.clear()
        self._lines.clear()
        self._cur = -1
        self._layout()
        if dm is not None:
            self.goto_page(0)

    def _measure(self):
        doc = self.dm.doc
        return [(r.width, r.height) for r in (doc[i].rect for i in range(doc.page_count))]

    def _layout(self, sizes=None):
        self._hover = None
        self._drag = None
        fl = self._float
        if fl is not None:
            self.scene().removeItem(fl)
        self.scene().clear()
        self._items, self._ys = [], []
        if self.dm is None:
            self._sizes = []
            self.scene().setSceneRect(QRectF(0, 0, 10, 10))
            return
        self._sizes = sizes or self._measure()
        maxw = max(w for w, _ in self._sizes)
        y = GAP
        for i, (w, h) in enumerate(self._sizes):
            it = PageItem(self, i, w, h)
            it.setPos((maxw - w) / 2, y)
            self.scene().addItem(it)
            self._items.append(it)
            self._ys.append(y)
            y += h + GAP
        self.scene().setSceneRect(QRectF(-GAP, 0, maxw + 2 * GAP, y))
        if fl is not None:
            self.scene().addItem(fl)

    def refresh(self, pages=None):
        """Call after the document changed. pages: indexes whose content changed, None = unknown."""
        if self.dm is None:
            return
        self._lines.clear()
        self._hover_clear()
        sizes = self._measure()
        if sizes != self._sizes:
            pos = self._position()
            wider = max(w for w, _ in sizes) != max((w for w, _ in self._sizes), default=0)
            self._cache.clear()
            self._layout(sizes)
            self._restore(pos)
            if wider:
                hb = self.horizontalScrollBar()
                hb.setValue((hb.minimum() + hb.maximum()) // 2)
        else:
            for i in (list(self._cache) if pages is None else pages):
                self._cache.pop(i, None)
        self.viewport().update()
        self._scrolled()

    def _position(self):
        if not self._items:
            return None
        top = self.mapToScene(0, 0).y()
        i = self.current_page()
        return i, top - self._ys[i]

    def _restore(self, pos):
        if not pos or not self._items:
            return
        i = min(pos[0], len(self._items) - 1)
        self._scroll_to_y(self._ys[i] + pos[1])

    def _scroll_to_y(self, y):
        top = self.sceneRect().top()
        self.verticalScrollBar().setValue(int(round((y - top) * self.k)))

    # ------------------------------------------------------------ rendering
    def _render_scale(self):
        return self.k * self.devicePixelRatioF()

    def image_for(self, i):
        ent = self._cache.get(i)
        if ent is None or abs(ent[1] - self._render_scale()) > 1e-3:
            self._want.add(i)
            if not self._timer.isActive():
                self._timer.start(12)
        return ent[0] if ent else None

    def _visible(self):
        if not self._items:
            return []
        r = self.mapToScene(self.viewport().rect()).boundingRect()
        a = max(bisect.bisect_right(self._ys, r.top()) - 1, 0)
        out = []
        for i in range(a, len(self._items)):
            if self._ys[i] > r.bottom():
                break
            if self._ys[i] + self._sizes[i][1] >= r.top():
                out.append(i)
        return out

    def render_page(self, i, scale):
        page = self.dm.doc[i]
        w, h = self._sizes[i]
        scale = min(scale, math.sqrt(MAX_PIXELS / max(w * h, 1)))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        return QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()

    def _render_some(self):
        if self.dm is None:
            return
        vis = self._visible()
        todo = [i for i in vis if i in self._want]
        self._want.intersection_update(vis)
        if not todo:
            return
        i = todo[0]
        self._want.discard(i)
        scale = self._render_scale()
        try:
            self._cache[i] = (self.render_page(i, scale), scale)
        except Exception:
            self._cache[i] = (None, scale)
        if len(self._cache) > 14:
            for j in sorted(self._cache, key=lambda j: abs(j - i), reverse=True)[:len(self._cache) - 14]:
                if j not in vis:
                    self._cache.pop(j, None)
        self._items[i].update()
        if len(todo) > 1:
            self._timer.start(0)

    # ------------------------------------------------------------ zoom / navigation
    def _apply_zoom(self):
        self.k = self.zoom * PX_PER_PT
        self.setTransform(QTransform.fromScale(self.k, self.k))
        if isinstance(self._float, FloatImage):
            self._float.zoom_changed()

    def set_zoom(self, z, under_mouse=False):
        z = max(0.1, min(6.0, z))
        if abs(z - self.zoom) < 1e-4:
            return
        self.zoom = z
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse if under_mouse else QGraphicsView.AnchorViewCenter)
        self._apply_zoom()
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.zoomChanged.emit(z)
        self._scrolled()

    def fit_width(self):
        if self._sizes:
            w = max(w for w, _ in self._sizes) + 2 * GAP
            self.set_zoom((self.viewport().width() - 4) / (w * PX_PER_PT))

    def fit_page(self):
        if self._sizes:
            i = self.current_page()
            w, h = self._sizes[i]
            z = min((self.viewport().width() - 4) / ((w + 2 * GAP) * PX_PER_PT),
                    (self.viewport().height() - 4) / ((h + 2 * GAP) * PX_PER_PT))
            self.set_zoom(z)
            self.goto_page(i)

    def current_page(self):
        if not self._items:
            return 0
        c = self.mapToScene(self.viewport().rect().center()).y()
        return max(0, min(bisect.bisect_right(self._ys, c) - 1, len(self._items) - 1))

    def goto_page(self, i):
        if self._items:
            i = max(0, min(i, len(self._items) - 1))
            self._scroll_to_y(self._ys[i] - GAP / 2)
            self._scrolled()

    def _scrolled(self, *_):
        i = self.current_page()
        if i != self._cur:
            self._cur = i
            self.pageChanged.emit(i)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.set_zoom(self.zoom * (1.15 if e.angleDelta().y() > 0 else 1 / 1.15), under_mouse=True)
            e.accept()
        else:
            super().wheelEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._scrolled()

    # ------------------------------------------------------------ tools
    def set_tool(self, name, keep_float=False):
        if not keep_float:
            self.commit_float()
        self._cancel_drag()
        self._hover_clear()
        self.tool = name
        if name != "place":
            self._payload = None
        self.setDragMode(QGraphicsView.ScrollHandDrag if name == "select" else QGraphicsView.NoDrag)
        cur = {"select": None, "text": Qt.IBeamCursor, "edittext": Qt.ArrowCursor}.get(name, Qt.CrossCursor)
        if cur is None:
            self.viewport().unsetCursor()
        else:
            self.viewport().setCursor(cur)
        self.toolChanged.emit(name)

    def place_image(self, image, data, width_pt):
        """Next click on a page drops this picture there."""
        self.set_tool("place")
        self._payload = (image, data, width_pt)
        self.hint.emit(tr("在页面上点击要放置的位置；放好后可拖动、拖四角缩放，点击空白处或按回车确认，Esc 取消"))

    def set_opts(self, **kw):
        self.opts.update(kw)
        if isinstance(self._float, FloatText):
            self._float.apply(self.opts["font"], self.opts["size"], self.opts["text_color"])

    def page_at(self, sp):
        if not self._items:
            return None
        i = max(0, min(bisect.bisect_right(self._ys, sp.y()) - 1, len(self._items) - 1))
        it = self._items[i]
        return it if it.rect().contains(sp - it.pos()) else None

    def _nearest_page(self, sp):
        best = min(self._items, key=lambda it: abs(it.pos().y() + it.h / 2 - sp.y()))
        return best

    def _on_float(self, view_pos):
        it = self.itemAt(view_pos)
        while it is not None:
            if it is self._float:
                return True
            it = it.parentItem()
        return False

    # -- floats
    def has_float(self):
        return self._float is not None

    def _set_float(self, item, sp):
        self._float = item
        self.scene().addItem(item)
        item.setPos(sp)
        item.setFocus()

    def new_text(self, sp, text=""):
        it = FloatText(self, text)
        it.apply(self.opts["font"], self.opts["size"], self.opts["text_color"])
        self._set_float(it, sp)
        if text:
            c = it.textCursor()
            c.select(c.SelectionType.Document)
            it.setTextCursor(c)
        self.hint.emit(tr("输入文字；拖左上角蓝色手柄移动，点击空白处或 Ctrl+回车 确认，Esc 取消"))

    def _drop_payload(self, sp, page):
        image, data, width = self._payload
        w = min(width, page.w * 0.9)
        h = w * image.height() / max(image.width(), 1)
        if h > page.h * 0.9:
            h = page.h * 0.9
            w = h * image.width() / max(image.height(), 1)
        it = FloatImage(self, image, data, w, h)
        self._set_float(it, QPointF(sp.x() - w / 2, sp.y() - h / 2))
        self.set_tool("select", keep_float=True)

    def cancel_float(self):
        f, self._float = self._float, None
        if f is not None:
            self.scene().removeItem(f)
            f.deleteLater()
            self.hint.emit("")

    def commit_float(self):
        f = self._float
        if f is None:
            return True
        self._float = None
        self.hint.emit("")
        try:
            rect = f.sceneBoundingRect() if isinstance(f, FloatText) else QRectF(f.scenePos().x(), f.scenePos().y(), f.w, f.h)
            page = self.page_at(rect.center()) or self._nearest_page(rect.center())
            local = f.scenePos() - page.pos()
            if isinstance(f, FloatText):
                text = f.toPlainText()
                if not text.strip():
                    return True
                fm = QFontMetricsF(f.font())
                m = f.document().documentMargin()
                with self.dm.edit() as d:
                    pdfops.add_text(d[page.index], local.x() + m, local.y() + m, text, f.size, f.color,
                                    f.font_name, ascent=fm.ascent(), line_h=fm.lineSpacing())
            else:
                with self.dm.edit() as d:
                    pdfops.add_image(d[page.index], (local.x(), local.y(), local.x() + f.w, local.y() + f.h),
                                     data=f.data)
            self._after({page.index})
            return True
        except Exception as exc:
            self.failed.emit(tr("写入页面"), exc)
            self.refresh()
            return False
        finally:
            self.scene().removeItem(f)
            f.deleteLater()

    def _after(self, pages):
        self.refresh(pages)
        self.edited.emit(pages)

    # -- drag tools
    def _cancel_drag(self):
        if self._drag:
            self.scene().removeItem(self._drag["item"])
            self._drag = None

    def _hover_clear(self):
        if self._hover is not None:
            try:
                self.scene().removeItem(self._hover)
            except RuntimeError:
                pass
            self._hover = None

    def _local(self, page, sp, clamp=True):
        p = sp - page.pos()
        if clamp:
            p = QPointF(max(0.0, min(page.w, p.x())), max(0.0, min(page.h, p.y())))
        return p

    def _preview_path(self):
        d = self._drag
        tool, pts = d["tool"], d["pts"]
        path = QPainterPath()
        a, b = pts[0], pts[-1]
        if tool in ("rect",) + MARKS + AREAS:
            path.addRect(QRectF(a, b).normalized())
        elif tool == "ellipse":
            path.addEllipse(QRectF(a, b).normalized())
        elif tool in ("line", "arrow"):
            path.moveTo(a)
            path.lineTo(b)
        else:
            path.moveTo(a)
            for q in pts[1:]:
                path.lineTo(q)
        return path

    def _start_drag(self, page, sp):
        tool = self.tool
        item = QGraphicsPathItem(page)
        item.setZValue(5)
        o = self.opts
        if tool in SHAPES:
            pen = QPen(QColor(o["color"]), o["width"], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            item.setPen(pen)
        elif tool == "highlight":
            c = QColor(o["hl_color"])
            c.setAlpha(110)
            item.setPen(QPen(Qt.NoPen))
            item.setBrush(c)
        elif tool in ("underline", "strike"):
            c = QColor(o["color"])
            c.setAlpha(60)
            item.setPen(QPen(QColor(o["color"]), 0, Qt.DashLine))
            item.setBrush(c)
        elif tool == "erase":
            item.setPen(QPen(QColor("#7a8194"), 0, Qt.DashLine))
            item.setBrush(QColor(255, 255, 255, 215))
        else:
            item.setPen(QPen(QColor("#ff5252"), 0, Qt.DashLine))
            item.setBrush(QColor(0, 0, 0, 170))
        self._drag = {"tool": tool, "page": page, "item": item, "pts": [self._local(page, sp)]}

    def _constrain(self, a, b, tool):
        dx, dy = b.x() - a.x(), b.y() - a.y()
        if tool in ("line", "arrow"):
            ang = round(math.atan2(dy, dx) / (math.pi / 4)) * (math.pi / 4)
            r = math.hypot(dx, dy)
            return QPointF(a.x() + r * math.cos(ang), a.y() + r * math.sin(ang))
        if tool in ("rect", "ellipse"):
            s = max(abs(dx), abs(dy))
            return QPointF(a.x() + math.copysign(s, dx or 1), a.y() + math.copysign(s, dy or 1))
        return b

    def _finish_drag(self):
        d, self._drag = self._drag, None
        self.scene().removeItem(d["item"])
        tool, page, pts = d["tool"], d["page"], d["pts"]
        a, b = pts[0], pts[-1]
        if tool == "pen":
            if len(pts) < 2:
                return
        elif math.hypot(b.x() - a.x(), b.y() - a.y()) < 2.0:
            return
        o = self.opts
        xy = [(p.x(), p.y()) for p in pts]
        box = (min(a.x(), b.x()), min(a.y(), b.y()), max(a.x(), b.x()), max(a.y(), b.y()))
        try:
            with self.dm.edit() as doc:
                pg = doc[page.index]
                if tool in SHAPES:
                    pdfops.draw(pg, tool, xy, o["color"], o["width"])
                elif tool in MARKS:
                    pdfops.markup(pg, box, tool, o["hl_color"] if tool == "highlight" else o["color"])
                else:
                    pdfops.erase(pg, box, "#ffffff" if tool == "erase" else "#000000")
            self._after({page.index})
        except Exception as exc:
            self.failed.emit(tr("编辑"), exc)
            self.refresh()

    def lines_of(self, index):
        if index not in self._lines:
            try:
                self._lines[index] = pdfops.text_lines(self.dm.doc[index])
            except Exception:
                self._lines[index] = []
        return self._lines[index]

    # ------------------------------------------------------------ mouse / keys
    def mousePressEvent(self, e):
        if self.dm is None or e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        vp = e.position().toPoint()
        if self._float is not None:
            if self._on_float(vp):
                return super().mousePressEvent(e)
            had_text = isinstance(self._float, FloatText)
            self.commit_float()
            if self.tool == "select" or (self.tool == "text" and had_text):
                if self.tool == "select":
                    super().mousePressEvent(e)
                return
        if self.tool == "select":
            return super().mousePressEvent(e)
        sp = self.mapToScene(vp)
        page = self.page_at(sp)
        if page is None:
            return
        if self.tool == "text":
            self.new_text(sp)
        elif self.tool == "place" and self._payload:
            self._drop_payload(sp, page)
        elif self.tool == "edittext":
            p = self._local(page, sp)
            line = pdfops.pick_line(self.lines_of(page.index), p.x(), p.y())
            if line:
                self.lineClicked.emit(page.index, line)
            else:
                self.hint.emit(tr("这里没有可修改的文字（扫描件或图片中的字无法直接修改，可用“擦除”后再加文字）"))
        elif self.tool in DRAG_TOOLS:
            self._start_drag(page, sp)

    def mouseMoveEvent(self, e):
        if self._drag:
            d = self._drag
            p = self._local(d["page"], self.mapToScene(e.position().toPoint()))
            if d["tool"] == "pen":
                last = d["pts"][-1]
                if math.hypot(p.x() - last.x(), p.y() - last.y()) * self.k >= 2.0:
                    d["pts"].append(p)
            else:
                if e.modifiers() & Qt.ShiftModifier:
                    p = self._constrain(d["pts"][0], p, d["tool"])
                    p = QPointF(max(0.0, min(d["page"].w, p.x())), max(0.0, min(d["page"].h, p.y())))
                d["pts"] = [d["pts"][0], p]
            d["item"].setPath(self._preview_path())
            return
        if self.tool == "edittext" and self.dm is not None and not e.buttons():
            sp = self.mapToScene(e.position().toPoint())
            page = self.page_at(sp)
            line = None
            if page is not None:
                p = self._local(page, sp)
                line = pdfops.pick_line(self.lines_of(page.index), p.x(), p.y())
            if line is None:
                self._hover_clear()
                self.viewport().setCursor(Qt.ArrowCursor)
            else:
                key = (page.index, line["bbox"])
                if self._hover is None or self._hover.data(0) != key:
                    self._hover_clear()
                    b = line["bbox"]
                    self._hover = QGraphicsRectItem(QRectF(b[0] - 1, b[1] - 1, b[2] - b[0] + 2, b[3] - b[1] + 2), page)
                    self._hover.setPen(QPen(QColor(BLUE), 0))
                    self._hover.setBrush(QColor(59, 130, 246, 45))
                    self._hover.setData(0, key)
                self.viewport().setCursor(Qt.PointingHandCursor)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._drag and e.button() == Qt.LeftButton:
            self._finish_drag()
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        f = self._float
        if self._drag and e.key() == Qt.Key_Escape:
            self._cancel_drag()
            return
        if isinstance(f, FloatImage):
            k = e.key()
            if k in (Qt.Key_Escape, Qt.Key_Delete):
                return self.cancel_float()
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self.commit_float()
                return
            step = {Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0), Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1)}.get(k)
            if step:
                n = 10 if e.modifiers() & Qt.ShiftModifier else 1
                f.moveBy(step[0] * n, step[1] * n)
                return
        elif f is None and e.key() == Qt.Key_Escape and self.tool != "select":
            self.set_tool("select")
            return
        super().keyPressEvent(e)

    def leaveEvent(self, e):
        self._hover_clear()
        super().leaveEvent(e)


def image_bytes(image, fmt="PNG"):
    buf = QBuffer()
    buf.open(QBuffer.WriteOnly)
    image.save(buf, fmt)
    return bytes(buf.data())
