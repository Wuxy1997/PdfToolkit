"""Settings and data folder (kept next to the exe, so the app stays portable)."""
import json
import os
import sys

_DATA = None


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def set_data_dir(path):
    global _DATA
    _DATA = os.path.abspath(path)


def data_dir():
    d = _DATA or os.path.join(app_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def sig_dir():
    d = os.path.join(data_dir(), "signatures")
    os.makedirs(d, exist_ok=True)
    return d


def _path():
    return os.path.join(data_dir(), "config.json")


DEFAULTS = {
    "recent": [],
    "last_dir": "",
    "font": "微软雅黑",
    "font_size": 12,
    "color": "#d32f2f",
    "text_color": "#000000",
    "line_width": 1.5,
    "sig_width": 140,
}


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(_path(), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    tmp = _path() + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path())
    except OSError:
        pass


def add_recent(cfg, path):
    path = os.path.abspath(path)
    rec = [p for p in cfg.get("recent", []) if os.path.normcase(p) != os.path.normcase(path)]
    rec.insert(0, path)
    cfg["recent"] = rec[:12]
    cfg["last_dir"] = os.path.dirname(path)
    save(cfg)
