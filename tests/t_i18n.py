"""Static check of the two languages: every text shown on screen goes through tr() and has English.
    python tests\\t_i18n.py            check
    python tests\\t_i18n.py --keys     also list the texts that still lack English"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import fonts, i18n
from core.version import APP_NAME

# Chinese characters and Chinese punctuation (full-width forms, corner quotes, ideographic space)
CJK = re.compile("[一-鿿　-〿＀-￯“”‘’]")
FILES = ["main.py", "core/config.py", "core/docmodel.py", "core/fonts.py", "core/pdfops.py", "core/ranges.py",
         "ui/common.py", "ui/dialogs.py", "ui/home.py", "ui/mainwindow.py", "ui/settings.py", "ui/signature.py",
         "ui/thumbs.py", "ui/view.py"]
# module-level tables whose texts are shown through tr(label) where they are used
TABLES = {"ui/common.py", "ui/dialogs.py", "ui/home.py", "ui/mainwindow.py", "ui/signature.py"}
# Chinese that is deliberately not translated in place
ALLOWED = {
    "中文",                                  # the language's own name in Settings
    "华文行楷",                              # a Windows font family name
    "微软雅黑", "宋体", "黑体", "楷体", "仿宋",       # font keys (saved in the settings, shown through tr)
    "自检 selftest 文字", "自检水印",            # written into the PDF by the packaged self test
    "，", "；", "、",                          # punctuation a person may type in a page range
    "内置字体",                              # fallback font key when no Windows font is found
}


def strings(node):
    """Literal strings an expression can evaluate to: "a", "a" if x else "b", nested."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value
    elif isinstance(node, ast.IfExp):
        yield from strings(node.body)
        yield from strings(node.orelse)


def main():
    fails = []
    keys = {APP_NAME, *[n for n in fonts.FONTS if CJK.search(n)], "内置字体"}
    for rel in FILES:
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        tree = ast.parse(src)
        inside, docs = set(), set()
        if rel in TABLES:
            for node in tree.body:
                targets = [node] if isinstance(node, ast.Assign) else \
                    [n for n in node.body if isinstance(n, ast.Assign)] if isinstance(node, ast.ClassDef) else []
                for t in targets:
                    for sub in ast.walk(t.value):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and CJK.search(sub.value):
                            keys.add(sub.value)
                            inside.add(id(sub))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node, clean=False):
                docs.add(id(node.body[0].value))
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "tr" and node.args:
                keys.update(strings(node.args[0]))
                for sub in ast.walk(node.args[0]):
                    inside.add(id(sub))
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                seg = ast.get_source_segment(src, node)
                lit = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
                if CJK.search(lit):
                    fails.append(f"{rel}:{node.lineno} f-string with Chinese, use tr(): {seg[:50]}")
                for sub in ast.walk(node):
                    inside.add(id(sub))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and CJK.search(node.value) \
                    and id(node) not in inside and id(node) not in docs and node.value not in ALLOWED:
                fails.append(f"{rel}:{node.lineno} not through tr(): {node.value[:40]!r}")
    missing = []
    for k in sorted(keys):
        if k not in i18n.EN:
            missing.append(k)
            fails.append(f"no English for {k!r}")
        elif sorted(re.findall(r"\{(\w+)\}", k)) != sorted(re.findall(r"\{(\w+)\}", i18n.EN[k])):
            fails.append(f"placeholders differ: {k!r}")
        elif CJK.search(i18n.EN[k]):
            fails.append(f"Chinese left in English: {k!r}")
    unused = [k for k in i18n.EN if k not in keys]
    if unused:
        fails.append(f"translations nobody uses: {unused}")
    if "--keys" in sys.argv:
        for k in missing:
            print(f"    {k!r}: ,")
    print(f"{len(keys)} texts, {len(i18n.EN)} translations")
    for f in fails:
        print("FAIL", f)
    print("\nFAILED" if fails else "\nALL OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
