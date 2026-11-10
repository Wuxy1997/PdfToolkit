"""PDF工具箱 — split, merge, edit and sign PDF files. Everything runs locally."""
import os
import sys
import traceback


def main():
    args = sys.argv[1:]
    data = None
    if "--data" in args:
        i = args.index("--data")
        data = args[i + 1]
        del args[i:i + 2]

    from core import config
    if data:
        config.set_data_dir(data)

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from core.version import APP_ID, APP_NAME
    from ui import common
    from ui.mainwindow import MainWindow

    try:        # own taskbar group and icon instead of python's
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    tr = QTranslator(app)
    if tr.load(QLocale(QLocale.Chinese, QLocale.China), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(tr)
    common.apply_theme(app)
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for name in ("app.ico", "app.png"):
        ico = os.path.join(base, "assets", name)
        if os.path.exists(ico):
            app.setWindowIcon(QIcon(ico))
            break

    win = MainWindow(config.load())

    def on_error(etype, value, tb):
        traceback.print_exception(etype, value, tb)
        try:
            with open(os.path.join(config.data_dir(), "error.log"), "a", encoding="utf-8") as f:
                traceback.print_exception(etype, value, tb, file=f)
        except OSError:
            pass
        common.warn(win, f"程序遇到了一个意外问题，当前操作没有完成。\n\n{etype.__name__}: {value}")

    selftest = None
    if "--selftest" in args:        # used to check a packaged build: <in.pdf> --selftest <out.pdf>
        i = args.index("--selftest")
        selftest = args[i + 1]
        del args[i:i + 2]

    sys.excepthook = on_error
    win.show()
    files = [a for a in args if os.path.exists(a)]
    if files:
        win.handle_files(files)
    if selftest:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: _selftest(app, win, selftest))
    sys.exit(app.exec())


def _selftest(app, win, out):
    """Edit and save through the real window, write what happened next to the output, quit."""
    from core import pdfops
    log = []
    try:
        log.append(f"opened pages={win.dm.n} title={win.windowTitle()}")
        win.edit("selftest", lambda d: pdfops.add_text(d[0], 72, 300, "自检 selftest 文字", 18, "#d32f2f"), {0})
        win.rotate(90)
        win.edit("selftest", lambda d: pdfops.watermark(d, [0], "自检水印"), {0})
        ok = win._save_to(out)
        log.append(f"saved={ok} size={os.path.getsize(out) if os.path.exists(out) else 0}")
        log.append(f"view_pages={len(win.view._items)} thumbs={win.thumbs.count()} rendered={len(win.view._cache)}")
    except Exception as exc:
        log.append(f"ERROR {type(exc).__name__}: {exc}")
    with open(out + ".log", "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    win.dm.dirty = False
    app.quit()


if __name__ == "__main__":
    main()
