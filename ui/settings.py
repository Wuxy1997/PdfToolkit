"""Settings: the interface language, and where the app keeps its data."""
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QRadioButton, QVBoxLayout)

from core import config
from core.i18n import tr

from .common import primary

HEAD = "font-size: 14px; font-weight: bold; color: #1c2333;"
NOTE = "color: #7a8194;"


class SettingsDialog(QDialog):
    def __init__(self, parent, lang):
        super().__init__(parent)
        self.setWindowTitle(tr("设置"))
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(8)

        head = QLabel(tr("界面语言"))
        head.setStyleSheet(HEAD)
        lay.addWidget(head)
        row = QHBoxLayout()
        self.r_zh = QRadioButton("中文")
        self.r_en = QRadioButton("English")
        (self.r_en if lang == "en" else self.r_zh).setChecked(True)
        row.addWidget(self.r_zh)
        row.addSpacing(18)
        row.addWidget(self.r_en)
        row.addStretch(1)
        lay.addLayout(row)
        note = QLabel(tr("点“确定”后整个界面立即切换，正在编辑的文档和撤销记录都会保留。"))
        note.setWordWrap(True)
        note.setStyleSheet(NOTE)
        lay.addWidget(note)
        lay.addSpacing(12)

        head = QLabel(tr("数据文件夹"))
        head.setStyleSheet(HEAD)
        lay.addWidget(head)
        note = QLabel(tr("设置和保存的签名都放在这里，换电脑时把它一起拷走即可。"))
        note.setWordWrap(True)
        note.setStyleSheet(NOTE)
        lay.addWidget(note)
        row = QHBoxLayout()
        path = QLineEdit(config.data_dir())
        path.setReadOnly(True)
        path.setCursorPosition(0)
        row.addWidget(path, 1)
        b = QPushButton(tr("打开文件夹"))
        b.clicked.connect(self._open_data)
        row.addWidget(b)
        lay.addLayout(row)
        lay.addSpacing(10)

        box = QDialogButtonBox()
        ok = primary(box.addButton(tr("确定"), QDialogButtonBox.AcceptRole))
        box.addButton(tr("取消"), QDialogButtonBox.RejectRole)
        ok.setDefault(True)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def _open_data(self):
        from .dialogs import open_folder
        open_folder(config.data_dir())

    def lang(self):
        return "en" if self.r_en.isChecked() else "zh"
