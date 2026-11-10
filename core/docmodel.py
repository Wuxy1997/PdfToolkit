"""The document being edited: lives in memory, with undo snapshots."""
import contextlib
import os

import pymupdf

from . import pdfops

MAX_STEPS = 40
MAX_BYTES = 600 * 1024 * 1024


class Doc:
    def __init__(self, doc, path=None, encrypt=None):
        self.doc = doc
        self.path = path
        self.encrypt = encrypt      # kept so that saving a protected file keeps its password
        self.dirty = False
        self._undo = []
        self._redo = []

    # -- open
    @classmethod
    def open(cls, path, password=None):
        doc, used = pdfops.load(path, password)
        if pdfops.is_image(path):
            d = cls(doc, None)
            d.dirty = True
            d.suggest = os.path.splitext(path)[0] + ".pdf"
            return d
        enc = {"user_pw": used, "owner_pw": used} if used else None
        return cls(doc, os.path.abspath(path), enc)

    @classmethod
    def blank(cls):
        doc = pymupdf.open()
        doc.new_page(width=pdfops.A4[0], height=pdfops.A4[1])
        d = cls(doc, None)
        d.dirty = True
        return d

    @property
    def name(self):
        if self.path:
            return os.path.basename(self.path)
        s = getattr(self, "suggest", None)
        return os.path.basename(s) if s else "未命名.pdf"

    @property
    def n(self):
        return self.doc.page_count

    def bytes(self):
        return self.doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_NONE)

    # -- undo
    def _trim(self):
        while len(self._undo) > MAX_STEPS or (len(self._undo) > 1 and sum(map(len, self._undo)) > MAX_BYTES):
            self._undo.pop(0)

    def _restore(self, data):
        self.doc.close()
        self.doc = pymupdf.open(stream=data, filetype="pdf")

    @contextlib.contextmanager
    def edit(self):
        """with doc.edit(): change self.doc. Rolled back when the change raises."""
        snap = self.bytes()
        try:
            yield self.doc
        except BaseException:
            self._restore(snap)
            raise
        self._undo.append(snap)
        self._redo.clear()
        self._trim()
        self.dirty = True

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def undo(self):
        if self._undo:
            self._redo.append(self.bytes())
            self._restore(self._undo.pop())
            self.dirty = True

    def redo(self):
        if self._redo:
            self._undo.append(self.bytes())
            self._restore(self._redo.pop())
            self.dirty = True

    # -- save
    def save(self, path=None):
        path = os.path.abspath(path or self.path)
        pdfops.save(self.doc, path, self.encrypt)
        self.path = path
        self.dirty = False

    def close(self):
        try:
            self.doc.close()
        except Exception:
            pass
