"""PDF工具箱 / PDF Toolkit — split, merge, edit and sign PDF files. Everything runs locally."""
import os
import sys
import traceback


def _take(args, flag):
    """Remove `flag value` from args. -> value or None."""
    if flag not in args:
        return None
    i = args.index(flag)
    value = args[i + 1] if i + 1 < len(args) else None
    del args[i:i + 2]
    return value


def main():
    args = sys.argv[1:]
    data = _take(args, "--data")
    force_lang = _take(args, "--lang")          # --lang zh|en : for this run only
    selftest = _take(args, "--selftest")        # used to check a packaged build: <in.pdf> --selftest <out.pdf>

    from core import config
    if data:
        config.set_data_dir(data)

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from core.i18n import tr
    from core.version import APP_ID
    from ui import common
    from ui.mainwindow import MainWindow

    try:        # own taskbar group and icon instead of python's
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    app = QApplication(sys.argv[:1])
    cfg = config.load()
    common.pick_language(cfg, force_lang)
    common.apply_language(app)
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for name in ("app.ico", "app.png"):
        ico = os.path.join(base, "assets", name)
        if os.path.exists(ico):
            app.setWindowIcon(QIcon(ico))
            break

    win = MainWindow(cfg)

    def on_error(etype, value, tb):
        traceback.print_exception(etype, value, tb)
        try:
            with open(os.path.join(config.data_dir(), "error.log"), "a", encoding="utf-8") as f:
                traceback.print_exception(etype, value, tb, file=f)
        except OSError:
            pass
        common.warn(MainWindow.current, tr("程序遇到了一个意外问题，当前操作没有完成。") + f"\n\n{etype.__name__}: {value}")

    sys.excepthook = on_error
    win.show()
    files = [a for a in args if os.path.exists(a)]
    if files:
        win.handle_files(files)
    if selftest:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: _selftest(app, selftest))
    sys.exit(app.exec())


def _selftest(app, out):
    """Edit and save through the real window, switch the language and back, write what happened
    next to the output, quit."""
    from core import i18n, pdfops
    from core.i18n import tr
    from ui.mainwindow import MainWindow
    log = []
    try:
        win = MainWindow.current
        log.append(f"opened pages={win.dm.n} lang={i18n.lang()} title={win.windowTitle()}")
        win.edit("selftest", lambda d: pdfops.add_text(d[0], 72, 300, "自检 selftest 文字", 18, "#d32f2f"), {0})
        win.rotate(90)
        win.edit("selftest", lambda d: pdfops.watermark(d, [0], "自检水印"), {0})
        first = i18n.lang()
        steps = win.dm.can_undo()
        for lang in ("en" if first == "zh" else "zh", first):
            win = win.switch_language(lang)
            log.append(f"lang={i18n.lang()} title={win.windowTitle()} open={win.acts['open'].text()} "
                       f"tool={win.tool_acts['text'].text()} pages={win.dm.n} undo={win.dm.can_undo() == steps} "
                       f"is_current={win is MainWindow.current} font={win.font_box.currentText()} "
                       f"name={tr('未命名.pdf')}")
        ok = win._save_to(out)
        log.append(f"saved={ok} size={os.path.getsize(out) if os.path.exists(out) else 0}")
        log.append(f"view_pages={len(win.view._items)} thumbs={win.thumbs.count()} rendered={len(win.view._cache)}")
        win.dm.dirty = False
    except Exception as exc:
        log.append(f"ERROR {type(exc).__name__}: {exc}")
    with open(out + ".log", "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    app.quit()


if __name__ == "__main__":
    main()
