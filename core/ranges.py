"""Page range text such as "1-3, 5, 8-" (1-based for the user, 0-based inside)."""
import re


class RangeError(ValueError):
    pass


_PART = re.compile(r"^(\d*)\s*(?:[-~—–]\s*(\d*))?$")


def _norm(text):
    return (text or "").replace("，", ",").replace("；", ";").replace("、", ",").strip()


def parse_part(part, n):
    """One piece like "3", "2-5", "8-", "-4", "5-2" (reversed) -> list of 0-based indexes."""
    part = part.strip()
    m = _PART.match(part)
    if not m or part in ("", "-"):
        raise RangeError(f"看不懂的页码：“{part}”")
    a, b = m.group(1), m.group(2)
    if b is None:
        first = last = int(a)
    else:
        first = int(a) if a else 1
        last = int(b) if b else n
    for v in (first, last):
        if v < 1 or v > n:
            raise RangeError(f"页码 {v} 超出范围（本文件共 {n} 页）")
    step = 1 if last >= first else -1
    return [i - 1 for i in range(first, last + step, step)]


def parse_groups(text, n):
    """Each comma/semicolon separated piece becomes one group."""
    text = _norm(text)
    if not text:
        raise RangeError("请填写页码范围")
    groups = []
    for part in re.split(r"[,;\n]+", text):
        if part.strip():
            groups.append(parse_part(part, n))
    if not groups:
        raise RangeError("请填写页码范围")
    return groups


def parse_ranges(text, n):
    """Flat list of pages; empty text means every page."""
    if not _norm(text):
        return list(range(n))
    out = []
    for g in parse_groups(text, n):
        out.extend(g)
    return out


def describe(indexes):
    """[0,1,2,4] -> "1-3,5"."""
    if not indexes:
        return ""
    parts, start, prev = [], indexes[0], indexes[0]
    for i in list(indexes[1:]) + [None]:
        if i is not None and i == prev + 1:
            prev = i
            continue
        parts.append(f"{start + 1}" if start == prev else f"{start + 1}-{prev + 1}")
        if i is not None:
            start = prev = i
    return ",".join(parts)
