#!/usr/bin/env python3
"""uiautomator XML'inde dugum arar; tiklama merkezini (x y) yazdirir.

Kullanim: find_node.py <exact|contains|edit> <needle>
  exact    : text veya content-desc tam olarak esit
  contains : text veya content-desc needle iceriyor
  edit     : class = android.widget.EditText olan ilk duzenlenebilir alan
"""
import re
import sys


def main() -> None:
    mode = sys.argv[1]
    needle = sys.argv[2] if len(sys.argv) > 2 else ""
    xml = open("/tmp/opencode/w.xml", encoding="utf-8", errors="ignore").read()

    if mode == "list":
        seen = []
        for m in re.finditer(r"<node\b[^>]*?/?>", xml):
            s = m.group(0)
            txt = re.search(r'\btext="([^"]*)"', s)
            dsc = re.search(r'\bcontent-desc="([^"]*)"', s)
            for v in ((txt.group(1) if txt else ""), (dsc.group(1) if dsc else "")):
                if v.strip():
                    seen.append(v)
        for v in seen:
            print("    metin:", v[:90])
        return

    clickable_best = None
    any_best = None

    for m in re.finditer(r"<node\b[^>]*?/?>", xml):
        s = m.group(0)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', s)
        if not b:
            continue
        x1, y1, x2, y2 = map(int, b.groups())
        center = ((x1 + x2) // 2, (y1 + y2) // 2)

        if mode == "edit":
            cls = re.search(r'\bclass="([^"]*)"', s)
            hit = bool(cls) and cls.group(1) == "android.widget.EditText"
        else:
            txt = re.search(r'\btext="([^"]*)"', s)
            dsc = re.search(r'\bcontent-desc="([^"]*)"', s)
            vals = [v for v in ((txt.group(1) if txt else ""), (dsc.group(1) if dsc else "")) if v]
            if mode == "exact":
                hit = needle in vals
            else:
                hit = any(needle in v for v in vals)

        if not hit:
            continue
        if 'clickable="true"' in s:
            clickable_best = center
            break
        if any_best is None:
            any_best = center

    chosen = clickable_best or any_best
    if chosen:
        print(chosen[0], chosen[1])


if __name__ == "__main__":
    main()
