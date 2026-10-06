#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比本次构建前后的规则集差异，输出 JSON 与 Markdown 差异报告。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEXT_FILES = [
    # 去广告按 SukkaW/Surge 分片：六个分片各自独立比对，
    # 任何一个分片的增减都要出现在差异报告里。
    "Surge/Advertising/Advertising.Reject.list",
    "Surge/Advertising/Advertising.RejectExtra.list",
    "Surge/Advertising/Advertising.Drop.list",
    "Surge/Advertising/Advertising.NonIP.list",
    "Surge/Advertising/Advertising.NoDrop.list",
    "Surge/Advertising/Advertising.IP.list",
    "Surge/Ruleset/AI.list",
    "Surge/Ruleset/AI.Extra.list",
    "Surge/Ruleset/Ozon.list",
    "Surge/Ruleset/Ozon.Extra.list",
    "Mihomo/Ruleset/AI.Extra.yaml",
    "Mihomo/Ruleset/Ozon.Extra.yaml",
    "Mihomo/Advertising/Advertising.Drop.yaml",
    "Mihomo/Advertising/Advertising.NonIP.yaml",
    "Mihomo/Advertising/Advertising.NoDrop.yaml",
    "Mihomo/Advertising/Advertising.IP.yaml",
]

BINARY_FILES = [
    "Mihomo/Advertising/Advertising.Reject.mrs",
    "Mihomo/Advertising/Advertising.RejectExtra.mrs",
    "Mihomo/Ruleset/AI.mrs",
    "Mihomo/Ruleset/Ozon.mrs",
]


def entries_from_text(text, is_yaml):
    out = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if is_yaml:
            if line.startswith("- "):
                line = line[2:].strip()
            else:
                continue
        out.add(line)
    return out


def git_show(path, ref):
    p = subprocess.run(["git", "show", ref + ":" + path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        return None
    return p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre", default="HEAD", help="对比基准 ref（默认 HEAD）")
    ap.add_argument("--out", default="diff.json", help="差异 JSON 输出路径")
    ap.add_argument("--md", default="DIFF.md", help="差异 Markdown 报告输出路径")
    args = ap.parse_args()

    result = {"files": {}, "totals": {"added": 0, "removed": 0}}
    md_lines = ["# 规则集差异报告", ""]

    for rel in TEXT_FILES:
        is_yaml = rel.endswith(".yaml")
        pre = git_show(rel, args.pre)
        cur_path = ROOT / rel
        cur = cur_path.read_text(encoding="utf-8", errors="replace") if cur_path.exists() else None
        if pre is None and cur is None:
            continue
        pre_set = entries_from_text(pre, is_yaml) if pre is not None else set()
        cur_set = entries_from_text(cur, is_yaml) if cur is not None else set()
        added = cur_set - pre_set
        removed = pre_set - cur_set
        result["files"][rel] = {
            "pre": len(pre_set),
            "cur": len(cur_set),
            "added": len(added),
            "removed": len(removed),
            "added_samples": sorted(added)[:20],
            "removed_samples": sorted(removed)[:20],
        }
        result["totals"]["added"] += len(added)
        result["totals"]["removed"] += len(removed)
        if added or removed:
            md_lines.append("## " + rel)
            md_lines.append("")
            md_lines.append("- 上版 " + str(len(pre_set)) + " 条 → 本版 " + str(len(cur_set)) + " 条：**+" + str(len(added)) + " / -" + str(len(removed)) + "**")
            md_lines.append("")

    for rel in BINARY_FILES:
        pre_bytes = subprocess.run(["git", "cat-file", "-s", args.pre + ":" + rel], capture_output=True, text=True).stdout.strip()
        cur_path = ROOT / rel
        cur_size = cur_path.stat().st_size if cur_path.exists() else 0
        try:
            pre_size = int(pre_bytes)
        except ValueError:
            pre_size = 0
        result["files"][rel] = {"pre": pre_size, "cur": cur_size, "added": 0, "removed": 0}
        if pre_size != cur_size:
            md_lines.append("## " + rel)
            md_lines.append("")
            md_lines.append("- 体积 " + str(pre_size) + " → " + str(cur_size) + " 字节")
            md_lines.append("")

    (ROOT / args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 无条目级变化时也写一行明确文字，方便 release notes 直接引用整份报告。
    if result["totals"]["added"] == 0 and result["totals"]["removed"] == 0:
        md_lines.append("（本次构建无条目级变化）")
        md_lines.append("")

    md_path = ROOT / args.md
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print("diff: +" + str(result["totals"]["added"]) + " / -" + str(result["totals"]["removed"]) + " 条，报告写至 " + args.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
