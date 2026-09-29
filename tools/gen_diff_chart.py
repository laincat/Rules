#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 gen_diff.py 的 JSON 输出画增减差异图（SVG，无第三方依赖）。

用法：
    python tools/gen_diff_chart.py diff.json diff.svg
"""
from __future__ import annotations

import json
import sys


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    if len(sys.argv) < 3:
        print("usage: gen_diff_chart.py <diff.json> <out.svg>")
        return 2
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    files = data.get("files", {})

    # 只画有变化的条目级文件（added/removed 数字存在且不同时为零）
    rows = []
    for name, f in files.items():
        added = f.get("added", 0)
        removed = f.get("removed", 0)
        if added or removed:
            rows.append((name, added, removed))
    rows.sort(key=lambda r: -(r[1] + r[2]))

    if not rows:
        rows = [("（本轮无条目级变化）", 0, 0)]

    maxval = max((max(r[1], r[2]) for r in rows), default=1) or 1
    row_h = 34
    label_w = 320
    bar_area = 460
    head_h = 70
    width = label_w + bar_area + 120
    height = head_h + len(rows) * row_h + 30

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="Segoe UI, Arial, sans-serif">')
    parts.append(f'<rect width="{width}" height="{height}" fill="#0d1117"/>')
    parts.append(f'<text x="20" y="40" fill="#e6edf3" font-size="20" font-weight="bold">规则集增减差异</text>')
    parts.append(f'<text x="20" y="62" fill="#8b949e" font-size="12">绿=新增 · 红=删除（对数刻度示意图，非等比例）</text>')

    import math
    y = head_h
    for name, added, removed in rows:
        parts.append(f'<text x="12" y="{y+20}" fill="#c9d1d9" font-size="13">{esc(name)}</text>')
        # 新增条（绿）
        if added > 0:
            w = max(4, int(bar_area * (math.log(added + 1) / math.log(maxval + 1))))
            parts.append(f'<rect x="{label_w}" y="{y+6}" width="{w}" height="12" fill="#3fb950" rx="2"/>')
            parts.append(f'<text x="{label_w + w + 8}" y="{y+17}" fill="#3fb950" font-size="12">+{added}</text>')
        # 删除条（红）
        if removed > 0:
            w = max(4, int(bar_area * (math.log(removed + 1) / math.log(maxval + 1))))
            parts.append(f'<rect x="{label_w}" y="{y+20}" width="{w}" height="12" fill="#f85149" rx="2"/>')
            parts.append(f'<text x="{label_w + w + 8}" y="{y+31}" fill="#f85149" font-size="12">-{removed}</text>')
        y += row_h

    parts.append("</svg>")
    open(sys.argv[2], "w", encoding="utf-8").write("\n".join(parts) + "\n")
    print("chart written: " + sys.argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
