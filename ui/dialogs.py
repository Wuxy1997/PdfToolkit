"""Dialogs for merge, split and the document tools."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QPushButton, QRadioButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core import fonts, pdfops, ranges
from core.i18n import tr

from . import common
from .common import ColorButton, Progress, primary


def _ok_cancel(dlg, ok_text=None):
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    primary(bb.button(QDialogButtonBox.Ok)).setText(ok_text or tr("确定"))
    bb.button(QDialogButtonBox.Cancel).setText(tr("取消"))
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    return bb


def open_folder(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


class PagesField(QWidget):
    """Which pages: all / current / selected / typed range."""

    def __init__(self, n, current=0, selected=(), parent=None):
        super().__init__(parent)
        self.n, self.current, self.sel = n, current, list(selected)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.addItem(tr("全部页面（共 {n} 页）", n=n), "all")
        self.combo.addItem(tr("当前页（第 {n} 页）", n=current + 1), "cur")
        if len(self.sel) > 0:
            self.combo.addItem(tr("左侧选中的 {n} 页", n=len(self.sel)), "sel")
        self.combo.addItem(tr("自定义范围"), "custom")
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(tr("例如 1-3,5,8-"))
        self.edit.setEnabled(False)
        h.addWidget(self.combo)
        h.addWidget(self.edit, 1)
        self.combo.currentIndexChanged.connect(lambda: self.edit.setEnabled(self.combo.currentData() == "custom"))
        if len(self.sel) > 1:
            self.combo.setCurrentIndex(self.combo.findData("sel"))

    def indexes(self):
        mode = self.combo.currentData()
        if mode == "all":
            return list(range(self.n))
        if mode == "cur":
            return [self.current]
        if mode == "sel":
            return list(self.sel)
        if not self.edit.text().strip():
            raise ranges.RangeError(tr("请填写页码范围"))
        return sorted(set(ranges.parse_ranges(self.edit.text(), self.n)))


# ------------------------------------------------------------ merge

class MergeDialog(QDialog):
    def __init__(self, parent, cfg, files=()):
        super().__init__(parent)
        self.cfg = cfg
        self.result_path = None
        self.open_result = False
        self.setWindowTitle(tr("合并 PDF / 图片转 PDF"))
        self.resize(860, 560)
        self.setAcceptDrops(True)
        v = QVBoxLayout(self)
        tip = QLabel(tr("把要合并的 PDF 或图片加进来（也可以直接拖进窗口），按从上到下的顺序合成一个 PDF。"
                     "“页码范围”留空表示整个文件，可填 <b>1-3,5,8-</b> 这样的写法。"))
        tip.setWordWrap(True)
        v.addWidget(tip)

        mid = QHBoxLayout()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr("文件名"), tr("页数"), tr("页码范围（留空=全部）"), tr("所在文件夹")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setTextElideMode(Qt.ElideMiddle)
        self.table.verticalHeader().setDefaultSectionSize(30)
        hd = self.table.horizontalHeader()
        hd.setSectionResizeMode(QHeaderView.Interactive)
        hd.setStretchLastSection(True)
        for i, w in enumerate((270, 56, 190)):
            self.table.setColumnWidth(i, w)
        mid.addWidget(self.table, 1)
        col = QVBoxLayout()
        for text, fn in ((tr("添加文件…"), self._add), (tr("上移"), lambda: self._move(-1)), (tr("下移"), lambda: self._move(1)),
                         (tr("按文件名排序"), self._sort), (tr("移除"), self._remove), (tr("清空"), lambda: self.table.setRowCount(0))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            col.addWidget(b)
        col.addStretch(1)
        mid.addLayout(col)
        v.addLayout(mid, 1)

        opt = QHBoxLayout()
        self.bookmarks = QCheckBox(tr("用文件名生成书签（目录）"))
        self.bookmarks.setChecked(True)
        opt.addWidget(self.bookmarks)
        opt.addSpacing(20)
        opt.addWidget(QLabel(tr("图片页面大小")))
        self.image_page = QComboBox()
        self.image_page.addItem(tr("与图片相同"), "image")
        self.image_page.addItem(tr("A4 纸（居中）"), "a4")
        opt.addWidget(self.image_page)
        opt.addStretch(1)
        v.addLayout(opt)

        out = QHBoxLayout()
        out.addWidget(QLabel(tr("保存为")))
        self.out = QLineEdit()
        out.addWidget(self.out, 1)
        b = QPushButton(tr("浏览…"))
        b.clicked.connect(self._browse)
        out.addWidget(b)
        v.addLayout(out)

        bottom = QHBoxLayout()
        self.summary = QLabel()
        bottom.addWidget(self.summary, 1)
        self.go = primary(QPushButton(tr("开始合并")))
        self.go.clicked.connect(self._run)
        close = QPushButton(tr("关闭"))
        close.clicked.connect(self.reject)
        bottom.addWidget(self.go)
        bottom.addWidget(close)
        v.addLayout(bottom)
        self.add_files(files)
        self._summary()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.add_files([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    def _add(self):
        files = common.pick_open(self, tr("选择要合并的文件"), self.cfg.get("last_dir", ""), common.ANY_FILTER, many=True)
        if files:
            self.cfg["last_dir"] = os.path.dirname(files[0])
            self.add_files(files)

    def add_files(self, files):
        for path in files:
            path = os.path.normpath(path)
            ext = os.path.splitext(path)[1].lower()
            if ext != ".pdf" and not pdfops.is_image(path):
                continue
            pw_box = {}

            def opener(p, pw):
                n = pdfops.page_count(p, pw)
                pw_box["pw"] = pw
                return n
            try:
                n = common.open_with_password(self, path, opener)
            except Exception as exc:
                common.error(self, tr("读取 {name}", name=os.path.basename(path)), exc)
                continue
            if n is None:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            name = QTableWidgetItem(os.path.basename(path))
            name.setData(Qt.UserRole, (path, pw_box.get("pw"), n))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            cnt = QTableWidgetItem(str(n))
            cnt.setFlags(cnt.flags() & ~Qt.ItemIsEditable)
            cnt.setTextAlignment(Qt.AlignCenter)
            folder = QTableWidgetItem(os.path.dirname(path))
            folder.setFlags(folder.flags() & ~Qt.ItemIsEditable)
            for c, it in enumerate((name, cnt, QTableWidgetItem(""), folder)):
                self.table.setItem(r, c, it)
            if not self.out.text():
                self.out.setText(os.path.join(os.path.dirname(path), tr("合并结果.pdf")))
        self._summary()

    def _rows(self):
        return [[self.table.item(r, c).clone() for c in range(4)] for r in range(self.table.rowCount())]

    def _set_rows(self, rows, select=None):
        self.table.setRowCount(0)
        for cells in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, it in enumerate(cells):
                self.table.setItem(r, c, it)
        if select is not None:
            self.table.selectRow(select)
        self._summary()

    def _move(self, d):
        r = self.table.currentRow()
        rows = self._rows()
        if r < 0 or not (0 <= r + d < len(rows)):
            return
        rows[r], rows[r + d] = rows[r + d], rows[r]
        self._set_rows(rows, r + d)

    def _sort(self):
        rows = self._rows()
        rows.sort(key=lambda cells: _natural(cells[0].text()))
        self._set_rows(rows)

    def _remove(self):
        for r in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(r)
        self._summary()

    def _summary(self):
        n = self.table.rowCount()
        pages = sum(self.table.item(r, 0).data(Qt.UserRole)[2] for r in range(n))
        self.summary.setText(tr("共 {n} 个文件，{pages} 页", n=n, pages=pages) if n else tr("还没有添加文件"))
        self.go.setEnabled(n > 0)

    def _browse(self):
        f = common.pick_save(self, tr("合并后保存为"), self.out.text() or self.cfg.get("last_dir", ""))
        if f:
            self.out.setText(f)

    def items(self):
        out = []
        for r in range(self.table.rowCount()):
            path, pw, n = self.table.item(r, 0).data(Qt.UserRole)
            txt = self.table.item(r, 2).text().strip()
            try:
                pages = ranges.parse_ranges(txt, n) if txt else None
            except ranges.RangeError as exc:
                self.table.selectRow(r)
                raise ranges.RangeError(tr("{name}：{why}", name=os.path.basename(path), why=exc))
            out.append({"path": path, "password": pw, "pages": pages})
        return out

    def _run(self):
        out = self.out.text().strip()
        if not out:
            return common.warn(self, tr("请先选择合并后文件的保存位置。"))
        if not out.lower().endswith(".pdf"):
            out += ".pdf"
        try:
            items = self.items()
        except ranges.RangeError as exc:
            return common.warn(self, str(exc))
        if any(os.path.normcase(os.path.abspath(i["path"])) == os.path.normcase(os.path.abspath(out)) for i in items):
            return common.warn(self, tr("保存位置不能是正在合并的源文件之一，请换一个文件名。"))
        if os.path.exists(out) and not common.ask(self, tr("{name} 已存在，要覆盖吗？", name=os.path.basename(out))):
            return
        try:
            with Progress(self, tr("正在合并…")) as p:
                n = pdfops.merge(items, out, self.bookmarks.isChecked(), self.image_page.currentData(), p.step)
        except InterruptedError:
            return
        except Exception as exc:
            return common.error(self, tr("合并"), exc)
        self.result_path = out
        self.open_result = common.ask(self, tr("合并完成，共 {n} 页。\n{out}\n\n现在打开合并后的文件吗？", n=n, out=out))
        self.accept()


def _natural(text):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


# ------------------------------------------------------------ split

class SplitDialog(QDialog):
    def __init__(self, parent, cfg, dm=None, selected=()):
        super().__init__(parent)
        self.cfg, self.dm = cfg, dm
        self._src = None            # (path, password) when a file other than the open one is used
        self._n = dm.n if dm else 0
        self.setWindowTitle(tr("拆分 PDF"))
        self.resize(640, 470)
        v = QVBoxLayout(self)

        g = QGroupBox(tr("要拆分的文件"))
        h = QHBoxLayout(g)
        self.src = QLineEdit()
        self.src.setReadOnly(True)
        h.addWidget(self.src, 1)
        b = QPushButton(tr("选择其他文件…"))
        b.clicked.connect(self._pick)
        h.addWidget(b)
        v.addWidget(g)

        g = QGroupBox(tr("拆分方式"))
        grid = QGridLayout(g)
        self.grp = QButtonGroup(self)
        self.r_range = QRadioButton(tr("按页码范围"))
        self.e_range = QLineEdit()
        self.e_range.setPlaceholderText(tr("例如 1-3,4-10,11-   （每个逗号隔开的部分生成一个文件）"))
        self.r_every = QRadioButton(tr("每隔固定页数"))
        self.s_every = QSpinBox()
        self.s_every.setRange(1, 9999)
        self.s_every.setValue(1)
        self.s_every.setSuffix(tr(" 页一个文件"))
        self.r_each = QRadioButton(tr("每页拆成一个文件"))
        self.r_book = QRadioButton(tr("按一级书签（章节）"))
        self.r_one = QRadioButton(tr("提取成一个文件"))
        self.e_one = QLineEdit()
        self.e_one.setPlaceholderText(tr("例如 2,5-8   （把这些页按顺序放进同一个新文件）"))
        for i, (r, w) in enumerate(((self.r_range, self.e_range), (self.r_every, self.s_every),
                                    (self.r_each, None), (self.r_book, None), (self.r_one, self.e_one))):
            self.grp.addButton(r, i)
            grid.addWidget(r, i, 0)
            if w is not None:
                grid.addWidget(w, i, 1)
                w.setEnabled(False)
                r.toggled.connect(w.setEnabled)
        grid.setColumnStretch(1, 1)
        self.r_range.setChecked(True)
        v.addWidget(g)

        g = QGroupBox(tr("保存到"))
        f = QFormLayout(g)
        row = QHBoxLayout()
        self.folder = QLineEdit()
        row.addWidget(self.folder, 1)
        b = QPushButton(tr("浏览…"))
        b.clicked.connect(self._browse)
        row.addWidget(b)
        f.addRow(tr("文件夹"), row)
        self.stem = QLineEdit()
        f.addRow(tr("文件名前缀"), self.stem)
        v.addWidget(g)
        v.addStretch(1)

        bottom = QHBoxLayout()
        self.info = QLabel()
        bottom.addWidget(self.info, 1)
        go = primary(QPushButton(tr("开始拆分")))
        go.clicked.connect(self._run)
        close = QPushButton(tr("关闭"))
        close.clicked.connect(self.reject)
        bottom.addWidget(go)
        bottom.addWidget(close)
        v.addLayout(bottom)

        if dm:
            self.src.setText(tr("当前打开的文档：{name}", name=dm.name))
            base = dm.path or getattr(dm, "suggest", None) or os.path.join(cfg.get("last_dir", ""), dm.name)
            self._defaults(base)
            if len(selected) > 1:
                self.r_one.setChecked(True)
                self.e_one.setText(ranges.describe(sorted(selected)))
        self._count()

    def _defaults(self, path):
        stem = os.path.splitext(os.path.basename(path))[0]
        self.folder.setText(os.path.join(os.path.dirname(path), stem + tr("_拆分")))
        self.stem.setText(stem)

    def _count(self):
        self.info.setText(tr("共 {n} 页", n=self._n) if self._n else tr("请先选择文件"))

    def _pick(self):
        f = common.pick_open(self, tr("选择要拆分的 PDF"), self.cfg.get("last_dir", ""))
        if not f:
            return
        box = {}

        def opener(p, pw):
            box["pw"] = pw
            return pdfops.page_count(p, pw)
        try:
            n = common.open_with_password(self, f, opener)
        except Exception as exc:
            return common.error(self, tr("读取文件"), exc)
        if n is None:
            return
        self._src, self._n = (f, box.get("pw")), n
        self.src.setText(f)
        self.cfg["last_dir"] = os.path.dirname(f)
        self._defaults(f)
        self._count()

    def _browse(self):
        d = common.pick_dir(self, tr("保存到哪个文件夹"), self.folder.text() or self.cfg.get("last_dir", ""))
        if d:
            self.folder.setText(d)

    def _run(self):
        if not self._n:
            return common.warn(self, tr("请先选择要拆分的文件。"))
        folder, stem = self.folder.text().strip(), pdfops.safe_name(self.stem.text().strip() or tr("拆分"))
        if not folder:
            return common.warn(self, tr("请选择保存的文件夹。"))
        doc = None
        try:
            doc = self.dm.doc if self._src is None else pdfops.load(*self._src)[0]
            names = None
            mode = self.grp.checkedId()
            if mode == 0:
                groups = ranges.parse_groups(self.e_range.text(), self._n)
            elif mode == 1:
                groups = pdfops.groups_every(self._n, self.s_every.value())
            elif mode == 2:
                groups = pdfops.groups_every(self._n, 1)
            elif mode == 3:
                bm = pdfops.groups_bookmarks(doc)
                if not bm:
                    return common.warn(self, tr("这个文件没有书签，无法按章节拆分。请换一种拆分方式。"))
                names, groups = [t for t, _ in bm], [g for _, g in bm]
            else:
                if not self.e_one.text().strip():
                    return common.warn(self, tr("请填写要提取的页码。"))
                groups = [ranges.parse_ranges(self.e_one.text(), self._n)]
            if len(groups) > 200 and not common.ask(self, tr("将生成 {n} 个文件，继续吗？", n=len(groups))):
                return
            with Progress(self, tr("正在拆分…")) as p:
                files = pdfops.split(doc, groups, folder, stem, names, p.step)
        except ranges.RangeError as exc:
            return common.warn(self, str(exc))
        except InterruptedError:
            return
        except Exception as exc:
            return common.error(self, tr("拆分"), exc)
        finally:
            if doc is not None and self._src is not None:
                doc.close()
        if common.ask(self, tr("拆分完成，生成了 {n} 个文件。\n{folder}\n\n打开这个文件夹吗？", n=len(files), folder=folder)):
            open_folder(folder)
        self.accept()


# ------------------------------------------------------------ small tools

class WatermarkDialog(QDialog):
    def __init__(self, parent, n, current, selected):
        super().__init__(parent)
        self.setWindowTitle(tr("添加水印"))
        self.setMinimumWidth(470)
        f = QFormLayout(self)
        self.text = QLineEdit(tr("机密文件"))
        f.addRow(tr("水印文字"), self.text)
        self.font = QComboBox()
        common.fill_fonts(self.font)
        f.addRow(tr("字体"), self.font)
        row = QHBoxLayout()
        self.size = QSpinBox()
        self.size.setRange(6, 300)
        self.size.setValue(54)
        self.color = ColorButton("#8a8a8a", border="#8f97aa")
        row.addWidget(self.size)
        row.addWidget(QLabel(tr("颜色")))
        row.addWidget(self.color)
        row.addStretch(1)
        f.addRow(tr("字号"), row)
        self.opacity = QSpinBox()
        self.opacity.setRange(3, 100)
        self.opacity.setValue(22)
        self.opacity.setSuffix(" %")
        f.addRow(tr("不透明度"), self.opacity)
        self.angle = QSpinBox()
        self.angle.setRange(-90, 90)
        self.angle.setValue(45)
        self.angle.setSuffix(" °")
        f.addRow(tr("倾斜角度"), self.angle)
        self.tile = QCheckBox(tr("铺满整页（重复平铺）"))
        f.addRow("", self.tile)
        self.pages = PagesField(n, current, selected)
        f.addRow(tr("应用到"), self.pages)
        f.addRow(_ok_cancel(self, tr("添加水印")))

    def accept(self):
        if not self.text.text().strip():
            return common.warn(self, tr("请输入水印文字。"))
        try:
            self.idx = self.pages.indexes()
        except ranges.RangeError as exc:
            return common.warn(self, str(exc))
        super().accept()

    def params(self):
        return dict(text=self.text.text(), size=self.size.value(), color=self.color.color(),
                    opacity=self.opacity.value() / 100, angle=self.angle.value(), tile=self.tile.isChecked(),
                    font_name=self.font.currentData())


class PageNumberDialog(QDialog):
    POS = [("页脚居中", "bc"), ("页脚靠右", "br"), ("页脚靠左", "bl"), ("页眉居中", "tc"), ("页眉靠右", "tr"), ("页眉靠左", "tl")]

    def __init__(self, parent, n, current, selected):
        super().__init__(parent)
        self.setWindowTitle(tr("添加页码"))
        self.setMinimumWidth(470)
        f = QFormLayout(self)
        self.fmt = QComboBox()
        self.fmt.setEditable(True)
        self.fmt.addItems(["{n}", "{n} / {total}", tr("第 {n} 页"), tr("第 {n} 页 共 {total} 页"), "- {n} -"])
        self.fmt.setCurrentIndex(1)
        f.addRow(tr("样式"), self.fmt)
        tip = QLabel(tr("{n} 代表页码，{total} 代表总页数，可以自己改写"))
        tip.setStyleSheet("color: #7a8194;")
        f.addRow("", tip)
        self.pos = QComboBox()
        for label, key in self.POS:
            self.pos.addItem(tr(label), key)
        f.addRow(tr("位置"), self.pos)
        row = QHBoxLayout()
        self.size = QSpinBox()
        self.size.setRange(5, 72)
        self.size.setValue(10)
        self.color = ColorButton("#000000", border="#8f97aa")
        row.addWidget(self.size)
        row.addWidget(QLabel(tr("颜色")))
        row.addWidget(self.color)
        row.addStretch(1)
        f.addRow(tr("字号"), row)
        self.start = QSpinBox()
        self.start.setRange(0, 99999)
        self.start.setValue(1)
        f.addRow(tr("起始页码"), self.start)
        self.margin = QSpinBox()
        self.margin.setRange(5, 200)
        self.margin.setValue(28)
        self.margin.setSuffix(" pt")
        f.addRow(tr("距页边"), self.margin)
        self.pages = PagesField(n, current, selected)
        f.addRow(tr("应用到"), self.pages)
        f.addRow(_ok_cancel(self, tr("添加页码")))

    def accept(self):
        if "{n}" not in self.fmt.currentText():
            return common.warn(self, tr("样式里需要包含 {n}（代表页码）。"))
        try:
            self.idx = self.pages.indexes()
        except ranges.RangeError as exc:
            return common.warn(self, str(exc))
        super().accept()

    def params(self):
        return dict(fmt=self.fmt.currentText(), pos=self.pos.currentData(), size=self.size.value(),
                    color=self.color.color(), start=self.start.value(), margin=self.margin.value(),
                    font_name="宋体" if fonts.has_cjk(self.fmt.currentText()) else "Arial")


class EncryptDialog(QDialog):
    def __init__(self, parent, current):
        super().__init__(parent)
        self.setWindowTitle(tr("密码保护"))
        self.setMinimumWidth(460)
        self.result = current
        v = QVBoxLayout(self)
        state = QLabel(tr("当前状态：<b>已设置密码</b>") if current else tr("当前状态：未加密"))
        v.addWidget(state)
        f = QFormLayout()
        self.pw1 = QLineEdit()
        self.pw1.setEchoMode(QLineEdit.Password)
        self.pw2 = QLineEdit()
        self.pw2.setEchoMode(QLineEdit.Password)
        f.addRow(tr("打开密码"), self.pw1)
        f.addRow(tr("再输一次"), self.pw2)
        self.show_pw = QCheckBox(tr("显示密码"))
        self.show_pw.toggled.connect(lambda on: [w.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                                 for w in (self.pw1, self.pw2, self.owner)])
        f.addRow("", self.show_pw)
        self.owner = QLineEdit()
        self.owner.setEchoMode(QLineEdit.Password)
        self.owner.setPlaceholderText(tr("可不填；填了则用它才能解除下面的限制"))
        f.addRow(tr("权限密码"), self.owner)
        v.addLayout(f)
        g = QGroupBox(tr("打开后允许"))
        h = QHBoxLayout(g)
        self.allow = {}
        allowed = (current or {}).get("allow", pdfops.PERMS.keys())
        for key, label in (("print", tr("打印")), ("copy", tr("复制内容")), ("modify", tr("修改页面")), ("annotate", tr("批注和填表"))):
            c = QCheckBox(label)
            c.setChecked(key in allowed)
            self.allow[key] = c
            h.addWidget(c)
        v.addWidget(g)
        tip = QLabel(tr("密码在“保存”时写入文件（AES-256 加密）。请牢记密码，忘记后无法找回。"))
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #7a8194;")
        v.addWidget(tip)
        row = QHBoxLayout()
        rm = QPushButton(tr("移除密码"))
        rm.setEnabled(bool(current))
        rm.clicked.connect(self._remove)
        row.addWidget(rm)
        row.addStretch(1)
        ok = primary(QPushButton(tr("设置密码")))
        ok.clicked.connect(self._set)
        cancel = QPushButton(tr("取消"))
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        v.addLayout(row)

    def _remove(self):
        self.result = None
        self.accept()

    def _set(self):
        pw, owner = self.pw1.text(), self.owner.text()
        if not pw and not owner:
            return common.warn(self, tr("请输入密码。"))
        if pw != self.pw2.text():
            return common.warn(self, tr("两次输入的打开密码不一样。"))
        self.result = {"user_pw": pw, "owner_pw": owner or pw, "allow": {k for k, c in self.allow.items() if c.isChecked()}}
        self.accept()


class CompressDialog(QDialog):
    LEVELS = [("lossless", "无损整理", "不改图片，只清理冗余数据，画质完全不变"),
              ("high", "高质量", "图片降到 200 DPI，适合打印"),
              ("medium", "均衡（推荐）", "图片降到 150 DPI，适合屏幕阅读和邮件发送"),
              ("low", "最小体积", "图片降到 96 DPI，文件最小，图片会变模糊")]

    def __init__(self, parent, default_out, size_now):
        super().__init__(parent)
        self.setWindowTitle(tr("压缩 PDF"))
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(tr("当前文档大小约 <b>{size}</b>。压缩结果另存为新文件，不改动当前文档。",
                              size=common.human_size(size_now))))
        g = QGroupBox(tr("压缩程度"))
        gv = QVBoxLayout(g)
        self.grp = QButtonGroup(self)
        for i, (key, name, tip) in enumerate(self.LEVELS):
            r = QRadioButton(tr("{name}　—　{tip}", name=tr(name), tip=tr(tip)))
            r.setChecked(key == "medium")
            self.grp.addButton(r, i)
            gv.addWidget(r)
        v.addWidget(g)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("保存为")))
        self.out = QLineEdit(default_out)
        row.addWidget(self.out, 1)
        b = QPushButton(tr("浏览…"))
        b.clicked.connect(lambda: self.out.setText(common.pick_save(self, tr("压缩后保存为"), self.out.text()) or self.out.text()))
        row.addWidget(b)
        v.addLayout(row)
        v.addWidget(_ok_cancel(self, tr("开始压缩")))

    def level(self):
        return self.LEVELS[self.grp.checkedId()][0]

    def accept(self):
        if not self.out.text().strip():
            return common.warn(self, tr("请选择保存位置。"))
        super().accept()


class ExportImagesDialog(QDialog):
    def __init__(self, parent, n, current, selected, default_dir):
        super().__init__(parent)
        self.setWindowTitle(tr("导出为图片"))
        self.setMinimumWidth(500)
        f = QFormLayout(self)
        self.pages = PagesField(n, current, selected)
        f.addRow(tr("页面"), self.pages)
        self.fmt = QComboBox()
        self.fmt.addItem(tr("PNG（清晰，文件较大）"), "png")
        self.fmt.addItem(tr("JPG（文件较小）"), "jpg")
        f.addRow(tr("格式"), self.fmt)
        self.dpi = QComboBox()
        for d, tip in ((72, tr("屏幕")), (100, ""), (150, tr("常用")), (200, ""), (300, tr("打印")), (600, tr("超清"))):
            self.dpi.addItem(f"{d} DPI" + (tr("（{tip}）", tip=tip) if tip else ""), d)
        self.dpi.setCurrentIndex(2)
        f.addRow(tr("清晰度"), self.dpi)
        row = QHBoxLayout()
        self.folder = QLineEdit(default_dir)
        row.addWidget(self.folder, 1)
        b = QPushButton(tr("浏览…"))
        b.clicked.connect(lambda: self.folder.setText(common.pick_dir(self, tr("保存到"), self.folder.text()) or self.folder.text()))
        row.addWidget(b)
        f.addRow(tr("保存到"), row)
        f.addRow(_ok_cancel(self, tr("导出")))

    def accept(self):
        try:
            self.idx = self.pages.indexes()
        except ranges.RangeError as exc:
            return common.warn(self, str(exc))
        if not self.folder.text().strip():
            return common.warn(self, tr("请选择保存的文件夹。"))
        super().accept()


class ReplaceTextDialog(QDialog):
    def __init__(self, parent, line):
        super().__init__(parent)
        self.setWindowTitle(tr("修改文字"))
        self.setMinimumWidth(560)
        self.line = line
        v = QVBoxLayout(self)
        v.addWidget(QLabel(tr("把这一行文字改成（清空则删除这一行）：")))
        self.text = QLineEdit(line["text"])
        self.text.selectAll()
        v.addWidget(self.text)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("字体")))
        self.font = QComboBox()
        guess = pdfops.guess_font(line)
        common.fill_fonts(self.font)
        common.pick_font(self.font, guess)
        row.addWidget(self.font)
        row.addWidget(QLabel(tr("字号")))
        self.size = QDoubleSpinBox()
        self.size.setRange(1, 500)
        self.size.setDecimals(1)
        self.size.setValue(line["size"])
        row.addWidget(self.size)
        self.bold = QCheckBox(tr("加粗"))
        self.bold.setChecked(bool(line.get("bold")))
        row.addWidget(self.bold)
        row.addWidget(QLabel(tr("颜色")))
        from PySide6.QtGui import QColor
        self.color = ColorButton(QColor.fromRgbF(*line["color"]).name(), border="#8f97aa")
        row.addWidget(self.color)
        row.addStretch(1)
        v.addLayout(row)
        tip = QLabel(tr("原字体：{font}。原文件的字体通常不完整，新文字会改用上面选的字体，"
                        "外观可能与周围略有差别；改后文字变长时不会自动换行。", font=line.get("font") or tr("未知")))
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #7a8194;")
        v.addWidget(tip)
        v.addWidget(_ok_cancel(self, tr("修改")))

    def params(self):
        return dict(new_text=self.text.text(), size=self.size.value(), color=self.color.color(),
                    font_name=self.font.currentData(), bold=self.bold.isChecked())
