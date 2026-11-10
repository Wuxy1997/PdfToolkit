"""Thumbnail column: select pages, drag to reorder, right-click for page actions."""
import pymupdf
from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem, QStyle, QStyledItemDelegate

from .common import ACCENT, BLUE, PANEL

THUMB_W = 132
PAD = 10
LABEL_H = 22


class _Delegate(QStyledItemDelegate):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner

    def sizeHint(self, opt, index):
        return index.data(Qt.SizeHintRole) or QSize(THUMB_W + 2 * PAD, 200)

    def paint(self, p, opt, index):
        row = index.row()
        r = opt.rect
        sel = bool(opt.state & QStyle.State_Selected)
        cur = row == self.owner.current
        if sel:
            p.fillRect(r.adjusted(3, 2, -3, -2), QColor("#3d4b6b"))
        tw, th = self.owner.thumb_size(row)
        box = QRect(r.x() + (r.width() - tw) // 2, r.y() + PAD, tw, th)
        p.fillRect(box.translated(2, 2), QColor(0, 0, 0, 90))
        pm = self.owner.pixmap(row)
        if pm is not None:
            p.drawPixmap(box, pm)
        else:
            p.fillRect(box, Qt.white)
        p.setPen(QPen(QColor(ACCENT if cur else (BLUE if sel else "#1a1e27")), 2 if (cur or sel) else 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(box)
        f = QFont(p.font())
        f.setBold(cur)
        p.setFont(f)
        label = QRect(r.x(), box.bottom() + 3, r.width(), LABEL_H - 4)
        if cur:
            fm = p.fontMetrics()
            w = fm.horizontalAdvance(str(row + 1)) + 16
            pill = QRect(label.center().x() - w // 2, label.y(), w, label.height())
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(ACCENT))
            p.drawRoundedRect(pill, 8, 8)
            p.setPen(Qt.white)
        else:
            p.setPen(QColor("#c9cfdd"))
        p.drawText(label, Qt.AlignCenter, str(row + 1))


class Thumbs(QListWidget):
    pageActivated = Signal(int)
    reordered = Signal(list)         # new order as list of old indexes
    menuRequested = Signal(object)   # global QPoint
    deletePressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dm = None
        self.current = 0
        self._sizes = []
        self._cache = {}
        self._want = set()
        self._guard = False
        self.setItemDelegate(_Delegate(self))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(30)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setUniformItemSizes(False)
        self.setFixedWidth(THUMB_W + 2 * PAD + 22)
        self.setFrameShape(QListWidget.NoFrame)
        self.setStyleSheet(f"QListWidget {{ background: {PANEL}; border: none; outline: none; }}")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: self.menuRequested.emit(self.viewport().mapToGlobal(pos)))
        self.itemClicked.connect(lambda it: self.pageActivated.emit(self.row(it)))
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._render_some)

    # -- content
    def set_doc(self, dm):
        self.dm = dm
        self.current = 0
        self.reload()

    def reload(self, pages=None, select=None):
        """Rebuild rows after a document change. select: rows to select afterwards."""
        self._guard = True
        try:
            keep = self.verticalScrollBar().value()
            if select is None:
                select = self.selected()
            sizes = []
            if self.dm is not None:
                doc = self.dm.doc
                sizes = [(r.width, r.height) for r in (doc[i].rect for i in range(doc.page_count))]
            if pages is None or sizes != self._sizes:
                self._cache.clear()
            else:
                for i in pages:
                    self._cache.pop(i, None)
            self._sizes = sizes
            self.clear()
            for i in range(len(sizes)):
                it = QListWidgetItem()
                it.setData(Qt.UserRole, i)
                _, th = self.thumb_size(i)
                it.setData(Qt.SizeHintRole, QSize(THUMB_W + 2 * PAD, th + 2 * PAD + LABEL_H))
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
                self.addItem(it)
            for r in select:
                if 0 <= r < self.count():
                    self.item(r).setSelected(True)
            self.current = min(self.current, max(self.count() - 1, 0))
            self.verticalScrollBar().setValue(keep)
        finally:
            self._guard = False
        self.viewport().update()

    def thumb_size(self, row):
        if row >= len(self._sizes):
            return THUMB_W, 180
        w, h = self._sizes[row]
        if w >= h:
            return THUMB_W, max(20, int(THUMB_W * h / w))
        th = min(int(THUMB_W * h / w), 230)
        return max(20, int(th * w / h)), th

    def selected(self):
        return sorted(self.row(it) for it in self.selectedItems())

    def set_current(self, row):
        if row != self.current and 0 <= row < self.count():
            self.current = row
            self.scrollToItem(self.item(row), QAbstractItemView.EnsureVisible)
            self.viewport().update()

    # -- lazy pictures
    def pixmap(self, row):
        pm = self._cache.get(row)
        if pm is None and row not in self._cache:
            self._want.add(row)
            if not self._timer.isActive():
                self._timer.start(10)
        return pm

    def _render_some(self):
        if self.dm is None or not self._want:
            return
        first = self.indexAt(self.viewport().rect().topLeft()).row()
        last = self.indexAt(self.viewport().rect().bottomLeft()).row()
        if last < 0:
            last = self.count() - 1
        todo = sorted(r for r in self._want if first - 1 <= r <= last + 1)
        self._want.clear()
        for row in todo[:3]:
            try:
                page = self.dm.doc[row]
                tw, th = self.thumb_size(row)
                s = tw * self.devicePixelRatioF() / max(page.rect.width, 1)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(s, s), alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
                self._cache[row] = QPixmap.fromImage(img)
            except Exception:
                self._cache[row] = None
        if len(self._cache) > 400:
            for r in sorted(self._cache, key=lambda r: abs(r - first), reverse=True)[:100]:
                self._cache.pop(r, None)
        self.viewport().update()
        if len(todo) > 3:
            self._want.update(todo[3:])
            self._timer.start(0)

    # -- reorder
    @staticmethod
    def order_for_drop(n, rows, target):
        """New page order when the pages `rows` are dropped in front of row `target` (n = at the end)."""
        rows = sorted(set(rows))
        moving = set(rows)
        before = [i for i in range(target) if i not in moving]
        after = [i for i in range(target, n) if i not in moving]
        return before + rows + after

    def drop_target(self, pos):
        idx = self.indexAt(pos)
        if not idx.isValid():
            return self.count() if pos.y() > 0 and self.count() else 0
        r = self.visualRect(idx)
        return idx.row() + (1 if pos.y() > r.center().y() else 0)

    def dropEvent(self, e):
        # the document is reordered by the main window, which then rebuilds the rows
        if e.source() is not self:
            return e.ignore()
        rows = self.selected()
        order = self.order_for_drop(self.count(), rows, self.drop_target(e.position().toPoint()))
        e.setDropAction(Qt.IgnoreAction)
        e.accept()
        if rows and order != list(range(self.count())):
            QTimer.singleShot(0, lambda: self.reordered.emit(order))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.deletePressed.emit()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.currentRow() >= 0:
            self.pageActivated.emit(self.currentRow())
        else:
            super().keyPressEvent(e)
