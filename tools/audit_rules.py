#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""误杀风险审计：扫规则集，找出「可能把正常服务一起 REJECT」的条目。

    python tools/audit_rules.py
    python tools/audit_rules.py --md      # 导出完整风险清单到 AUDIT.md

按危险程度分级输出：
  P0  条目等于 TLD 或单标签域（.data 这种）—— 匹配面不可控
  P1  整站条目命中关键服务观察名单（CDN / 推送 / 支付 / 登录 / 更新）
  P2  整站条目中主域极短（<=4 字符）—— 容易和未来注册的域名撞车
  P3  DOMAIN-KEYWORD 子串规则 —— 匹配面最大，逐条人工看
  P4  含通配符 *（DOMAIN-SET 不支持，会被当无效行跳过）
  P5  精确匹配里看不出广告特征词的 —— 纯人工判断

「整站条目」= 条目本身就是 eTLD+1（如 .getui.com），
它把该域名及其所有子域都拉黑，风险远高于拉黑单个子域。
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from watchlist import SERVICE, WATCH, etld1          # noqa: E402

# 精确匹配里「看不出广告特征」的：不含这些词的都列出来人工过目
AD_HINT = re.compile(
    r"(ad|track|stat|log|analytic|pixel|beacon|telemetry|click|promo|aff|"
    r"market|spy|serv|banner|pop|count|metric|report|monitor|sdk|push|"
    r"img|cdn|api|config|event|collect|upload|sync|res|static|ssp|dsp)")

# 主域本身就是功能词的整站条目（如 api.bz）
FUNC_WORDS = ("api", "login", "pay", "payment", "update", "upgrade", "push",
              "im", "chat", "msg", "sync", "auth", "account", "accounts",
              "oss", "cdn", "static", "img", "video", "live", "search",
              "map", "cloud", "open", "gateway", "ws", "wss", "socket",
              "notify", "order", "trade", "wallet", "user", "member",
              "passport", "sso", "oauth", "download", "install", "activate",
              "license", "verify", "captcha")


def load(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith(("#", "//")):
            out.append(line)
    return out


def audit(domainset: str, extra: str | None = None) -> int:
    raw = load(domainset)
    if not raw:
        print("找不到 %s" % domainset)
        return 2
    print("审计 %s：%d 条" % (os.path.basename(domainset), len(raw)))

    whole = sorted({d.lstrip(".") for d in raw
                    if etld1(d.lstrip(".")) == d.lstrip(".")})
    print("整站条目 %d 个（占 %.1f%%），其余是子域/精确条目"
          % (len(whole), len(whole) * 100.0 / len(raw)))

    bad = 0

    # P0
    print("")
    print("-- P0 单标签 / TLD 级条目 --")
    p0 = sorted({d.lstrip(".") for d in raw if "." not in d.lstrip(".")})
    for d2 in p0:
        print("   !!", d2)
        bad += 1
    if not p0:
        print("   无")

    # P1
    print("")
    print("-- P1 整站条目命中关键服务观察名单 --")
    p1 = [w for w in whole if w in WATCH]
    for w in p1:
        sub = sum(1 for d in raw if d.lstrip(".").endswith("." + w)
                  and d.lstrip(".") != w)
        note = ("移除整站后完全放行" if sub == 0
                else "另有 %d 条子域条目，移除整站后这些仍会拦截" % sub)
        print("   !! %-30s %s" % (w, note))
        bad += 1
    if not p1:
        print("   无")

    # P2
    print("")
    print("-- P2 整站条目中主域极短（<=4 字符）--")
    p2 = sorted({w for w in whole if len(w.split(".")[0]) <= 4})
    for w in p2[:40]:
        print("   %-34s%s" % (w, "  !! 同时在 P1" if w in WATCH else ""))
    print("   ...共 %d 个（多数是广告网络短域，仅供参考）" % len(p2))

    # P3
    if extra and os.path.exists(extra):
        print("")
        print("-- P3 DOMAIN-KEYWORD 子串规则 --")
        for line in load(extra):
            print("   ", line)
        print("   （子串匹配，逐条确认是否过宽）")

    # P4
    print("")
    print("-- P4 含通配符 *（DOMAIN-SET 不支持，会被跳过）--")
    p4 = [d for d in raw if "*" in d]
    print("   ", p4[:20] if p4 else "无")
    bad += len(p4)

    # 参考
    print("")
    print("-- 参考：被拉黑条目最多的 eTLD+1 TOP 15 --")
    c = Counter(etld1(d.lstrip(".")) for d in raw)
    for dom, n in c.most_common(15):
        tag = ""
        if dom in whole:
            tag = "  <- 整站"
        elif dom in WATCH:
            tag = "  （仅子域）"
        print("   %-34s %5d 条%s" % (dom, n, tag))

    print("")
    print("=" * 60)
    if bad == 0:
        print("未发现高风险条目")
        return 0
    print("发现 %d 项需要人工确认（P0 / P1 / P4）" % bad)
    return 1


def write_md(ds: str, ex: str, out: str) -> None:
    """导出完整风险清单（给人工审核用，条目全部列出，不截断）。"""
    raw = load(ds)
    extra = load(ex) if ex and os.path.exists(ex) else []
    whole = sorted({d.lstrip(".") for d in raw
                    if etld1(d.lstrip(".")) == d.lstrip(".")})
    L = []
    A = L.append

    A("# 去广告规则误杀风险清单")
    A("")
    A("> 由 tools/audit_rules.py 生成。条目全部列出，供人工逐条审核。")
    A("> 结论以人工判断为准 —— 这里的分级只是值得看一眼的排序。")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 规则总数 | %d |" % len(raw))
    A("| 整站条目（条目 = eTLD+1） | %d（%.1f%%） |"
      % (len(whole), len(whole) * 100.0 / len(raw)))
    A("| 子域/精确条目 | %d |" % (len(raw) - len(whole)))
    A("")
    A("**整站条目**指 .getui.com 这种——把该域名及其所有子域都 REJECT，")
    A("风险远高于拉黑单个子域。以下按危险程度排序。")
    A("")

    # P0
    p0 = sorted({d.lstrip(".") for d in raw if "." not in d.lstrip(".")})
    A("## P0　单标签 / TLD 级条目（%d 条）" % len(p0))
    A("")
    A("没有点的条目。DOMAIN-SET 里 .data 表示匹配名为 data 的域及其所有子域，")
    A("如果 .data 是真实 TLD，等于把该 TLD 下所有域名全拦。")
    A("")
    for d2 in p0:
        A("- %s" % d2)
    if not p0:
        A("- 无")
    A("")

    # P1
    p1 = [w for w in whole if w in WATCH]
    A("## P1　整站条目命中关键服务名单（%d 条）" % len(p1))
    A("")
    A("| 条目 | 服务 | 移除整站后 |")
    A("|---|---|---|")
    for w in p1:
        sub = sum(1 for d in raw if d.lstrip(".").endswith("." + w)
                  and d.lstrip(".") != w)
        A("| %s | %s | %s |" % (
            w, SERVICE.get(w, "-"),
            "完全放行" if sub == 0
            else "仍有 %d 条子域条目会被拦截" % sub))
    A("")

    # 功能词整站
    fn = sorted(w for w in whole if w.split(".")[0] in FUNC_WORDS)
    A("## P2　主域本身是功能词的整站条目（%d 条）" % len(fn))
    A("")
    A("api.xxx / push.xxx 这种整站拉黑，理论上会影响同名业务。")
    A("实际看多是冷门新 gTLD（垃圾/广告域），但值得过一眼。")
    A("")
    for w in fn:
        A("- %s%s" % (w, "　!! 同时在 P1" if w in WATCH else ""))
    if not fn:
        A("- 无")
    A("")

    # 极短主域
    p3 = sorted(w for w in whole if len(w.split(".")[0]) <= 4)
    A("## P3　整站条目中主域极短（<=4 字符，共 %d 条）" % len(p3))
    A("")
    A("短域撞车概率高。全部列出：")
    A("")
    A("<details><summary>展开全部 %d 条</summary>" % len(p3))
    A("")
    for w in p3:
        A("- %s" % w)
    A("")
    A("</details>")
    A("")

    # KEYWORD
    A("## P4　DOMAIN-KEYWORD 子串规则（%d 条）" % len(extra))
    A("")
    A("子串匹配，命中面最大。逐条确认：")
    A("")
    for line in extra:
        A("- %s" % line)
    if not extra:
        A("- 无")
    A("")

    # 精确匹配里看不出广告特征的
    exact = [d for d in raw if not d.startswith(".")]
    suspect = sorted(d for d in exact if not AD_HINT.search(d))
    A("## P5　精确匹配中不含广告特征词的（%d / %d 条）" % (len(suspect), len(exact)))
    A("")
    A("按关键词筛不出广告痕迹，纯人工判断。全部列出：")
    A("")
    A("<details><summary>展开全部 %d 条</summary>" % len(suspect))
    A("")
    for d2 in suspect:
        A("- %s" % d2)
    A("")
    A("</details>")
    A("")

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print("已写入 %s" % out)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ds = args[0] if args else os.path.join(ROOT, "Surge", "Ruleset", "Advertising.list")
    ex = args[1] if len(args) > 1 else os.path.join(ROOT, "Surge", "Ruleset", "Advertising.Extra.list")
    if "--md" in sys.argv:
        out = args[2] if len(args) > 2 else os.path.join(ROOT, "AUDIT.md")
        write_md(ds, ex, out)
        return 0
    return audit(ds, ex)


if __name__ == "__main__":
    sys.exit(main())
