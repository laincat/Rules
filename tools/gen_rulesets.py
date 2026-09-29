#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ozon / AI 规则集生成器。

产物（全部由本脚本生成，勿手改）:
  Surge/Ruleset/Ozon.list   Surge classical 全量
  Surge/Ruleset/AI.list     Surge classical 全量
  Mihomo/Ruleset/Ozon.yaml  mihomo classical 全量（兼容单文件订阅）
  Mihomo/Ruleset/AI.yaml    mihomo classical 全量
  Mihomo/Ruleset/Ozon.mrs   mihomo domain 二进制（需 --mihomo 提供 convert-ruleset）
  Mihomo/Ruleset/AI.mrs     mihomo domain 二进制

数据源（活跃度复核 2026-09-29）:
  AI   = MetaCubeX category-ai-chat-!cn（= v2fly domain-list-community 展开产物，不重复抓 v2fly）
       + SukkaW/Surge Source/non_ip/ai.conf
       + Rabbit-Spec/Surge Rules/AIGC.list
       + ACL4SSR Clash/Ruleset/AI.list
       + iplist.opencck.org 主站 ai 组域名（仅域名；其 CIDR 是 Cloudflare 整段聚合，误伤面过大，不用）
  Ozon = 本文件维护的静态域名基线（含中国卖家新域名 ozonru.cn）
       + russia.iplist.opencck.org 的 ozon.ru 动态解析（域名取交叉根域，CIDR 全取）

已弃用的源:
  blackmatrix7 OpenAI.list —— 该文件停在 2025-06-06 不再更新，条目被上述四源完全覆盖

清洗规则:
  - 归一化为 DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD / IP-CIDR(R6) / IP-ASN 后去重
  - 后缀包含收敛: DOMAIN-SUFFIX,a.b.com 吞并 DOMAIN-SUFFIX,b.a.b.com
  - 精确域名被任意后缀覆盖时丢弃
  - 排除 deepseek.com（国内直连服务，iplist 把它放进了 ai 组）
  - 排除 pool.ntp.org（公共 NTP 池，不应整池进 AI 策略）
  - 丢弃 IP-ASN 13335/20473（Cloudflare/Vultr 整个云厂商，误伤面过大）
  - 丢弃 URL-REGEX 等跨端兼容性差的规则
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

NL = chr(10)
ROOT = Path(__file__).resolve().parent.parent
SURGE_OUT = ROOT / "Surge" / "Ruleset"
MIHOMO_OUT = ROOT / "Mihomo" / "Ruleset"
UA = {"User-Agent": "Mozilla/5.0 (compatible; laincat-rules-gen/1.0)"}

SRC_METACUBEX_AI = (
    "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-ai-chat-!cn.list"
)
SRC_SUKKA_AI = "https://raw.githubusercontent.com/SukkaW/Surge/master/Source/non_ip/ai.conf"
SRC_SUKKA_VOICE_IP = "https://ruleset.skk.moe/List/ip/ai.conf"  # ChatGPT Voice 官方出口 IP
SRC_RABBIT_AIGC = "https://raw.githubusercontent.com/Rabbit-Spec/Surge/master/Rules/AIGC.list"
SRC_ACL_AI = "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/AI.list"
SRC_PLIST_AI = "https://iplist.opencck.org/?format=json&data=domains&group=ai"
SRC_RUSSIA = "https://russia.iplist.opencck.org"
OZON_PLIST_DOMAINS = SRC_RUSSIA + "/?format=json&data=domains&site=ozon.ru"
# Ozon CIDR 不再用 iplist: 实测其 25 条里混有 5 条非 Ozon 网段 (斯洛文尼亚
# ISP /19、Jusan Mobile /24、ExpertSender /25 等), 而其自有 ASN 实际宣告的
# 91.212.64.0/24 与 46.226.122.0/24 两条它反而没有。改用 RIPEstat 官方 BGP
# 数据, 按 Ozon 两个 ASN 取宣告前缀, 权威且随扩容自动更新。
OZON_ASN_LIST = ["44386", "207986"]  # OZON-AS / OZON-BANK-AS
SRC_RIPESTAT = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS"

AI_SOURCES = [
    SRC_METACUBEX_AI, SRC_SUKKA_AI, SRC_RABBIT_AIGC, SRC_ACL_AI, SRC_PLIST_AI,
    SRC_SUKKA_VOICE_IP + " (ChatGPT Voice 官方出口 IP, 来自 openai.com/chatgpt-voice.json)",
]
OZON_SOURCES = [
    "静态域名基线（本脚本维护，含 ozonru.cn 中国卖家域名）",
    OZON_PLIST_DOMAINS,
    "RIPEstat announced-prefixes (AS44386 + AS207986, 官方 BGP 权威数据)",
]

EXCLUDE_SUFFIX = {"deepseek.com", "pool.ntp.org"}
EXCLUDE_EXACT = {
    # iplist russia portal 的 ozon.ru 数据里混进了一条 m.wildberries.ru
    # (Ozon 页面引用了 Wildberries 的资源), 不应整域跟随
    "m.wildberries.ru",
}
DROP_ASN = {"13335", "20473"}
DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
)

# ---------------------------------------------------------------- Ozon 静态基线
OZON_KEYWORD = ["ozon", "ozone"]
OZON_SUFFIX = [
    "ozon.ru", "ozone.ru", "ozon.com", "ozon.by", "ozon.kz", "ozon.li",
    "ozon.app", "ozon.dev", "ozon.tech", "ozon.express", "ozon.travel",
    "ozon.global", "ozon.market", "ozon.team", "ozon.com.by", "ozon.com.kz",
    "ozon.ru.com", "ozon.ru.eu", "ozon.ru.me", "ozon.co.il",
    "ozoncard.ru", "ozoncorp.ru", "ozoncorporate.ru", "ozoncredit.ru",
    "ozon-dostavka.ru", "ozonpartners.ru", "ozonpartners.by",
    "ozonrocet.by", "ozonroket.by", "ozonsport.ru", "ozonstatus.ru",
    "ozon-tech.ru", "ozontravel.ru", "ozonusercontent.com",
    "ozonglobalevents.com", "ozoncamp.pro",
    "ozonru.cn",
    "o3.ru", "o3t.ru", "o3team.ru", "ocourier.ru", "o-courier.ru",
    "ewisdom.us.kg",
    "xn--e1adjldbbpv.xn--90ais",
    "xn--80aafgovrgbc7am.xn--p1ai",
    "xn----8sbahiqzthbd0bn.xn--p1ai",
]


def fetch(url: str, tries: int = 3, timeout: int = 30) -> str:
    last: Exception | None = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed: {url} ({last})")


def is_domain(value: str) -> bool:
    return bool(DOMAIN_RE.fullmatch(value))


class RuleSet:
    """suffix / exact / keyword / ip 四类条目的可去重集合。"""

    def __init__(self) -> None:
        self.suffix: set[str] = set()
        self.exact: set[str] = set()
        self.keyword: set[str] = set()
        self.ips: set[tuple[str, str]] = set()

    def add_classical(self, text: str, metacubex_style: bool = False) -> None:
        """解析 classical 规则行；metacubex_style 时裸域名=精确、+.=后缀。"""
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "//", ";")):
                continue
            line = line.lstrip("- ").strip()
            if not line or line.startswith(("#", "//", ";")):
                continue
            if line.startswith("+."):
                value = line[2:].rstrip(".").lower()
                if is_domain(value):
                    self.suffix.add(value)
                continue
            parts = [p.strip() for p in line.split(",")]
            rtype = parts[0].upper()
            if rtype in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD") and len(parts) >= 2:
                value = parts[1].rstrip(".").lower()
                if not is_domain(value) and rtype != "DOMAIN-KEYWORD":
                    continue
                if rtype == "DOMAIN" and is_domain(value):
                    self.exact.add(value)
                elif rtype == "DOMAIN-SUFFIX" and is_domain(value):
                    self.suffix.add(value)
                elif rtype == "DOMAIN-KEYWORD" and value:
                    self.keyword.add(value)
            elif rtype in ("IP-CIDR", "IP-CIDR6") and len(parts) >= 2:
                try:
                    net = ipaddress.ip_network(parts[1], strict=False)
                except ValueError:
                    continue
                name = "IP-CIDR6" if net.version == 6 else "IP-CIDR"
                self.ips.add((name, str(net)))
            elif rtype == "IP-ASN" and len(parts) >= 2 and parts[1].isdigit():
                self.ips.add(("IP-ASN", parts[1]))
            elif metacubex_style and is_domain(line.rstrip(".").lower()):
                self.exact.add(line.rstrip(".").lower())
            # URL-REGEX / PROCESS-* / 逻辑规则等: 兼容性差或价值低，丢弃

    def add_plist_domains(self, data: dict) -> None:
        """iplist 站点域名: 站点根 → 后缀；交叉根域条目 → 精确候选。"""
        for site, domains in data.items():
            site = str(site).rstrip(".").lower()
            if is_domain(site):
                self.suffix.add(site)
            for dom in domains or []:
                dom = str(dom).rstrip(".").lower()
                if is_domain(dom):
                    self.exact.add(dom)

    def finalize(self) -> None:
        # 后缀包含收敛: 更长的后缀若其父后缀也在集合中, 则冗余
        for suf in list(self.suffix):
            labels = suf.split(".")
            for i in range(1, len(labels)):
                if ".".join(labels[i:]) in self.suffix:
                    self.suffix.discard(suf)
                    break
        self.suffix -= EXCLUDE_SUFFIX

        # IP-CIDR 包含收敛: 子网被超网覆盖时冗余 (如 AS44386 宣告了 /22 又宣告 /24)
        v4 = sorted(
            (ipaddress.ip_network(v) for t, v in self.ips if t == "IP-CIDR"),
            key=lambda n: (n.prefixlen, str(n.network_address)),
        )
        kept: list = []
        for net in v4:
            if any(net.subnet_of(sup) for sup in kept):
                continue
            kept.append(net)
        covered_by_supernet = {str(n) for n in v4} - {str(n) for n in kept}
        self.ips = {
            (t, v) for t, v in self.ips
            if not (t == "IP-CIDR" and v in covered_by_supernet)
        }

        # 排除表以其任意子域的形式混在 exact 里 (如 api.deepseek.com), 一并清掉
        def excluded(dom: str) -> bool:
            return any(dom == e or dom.endswith("." + e) for e in EXCLUDE_SUFFIX)

        def covered(dom: str) -> bool:
            labels = dom.split(".")
            return any(".".join(labels[i:]) in self.suffix for i in range(len(labels)))

        self.exact = {
            d for d in self.exact
            if not covered(d) and not excluded(d) and d not in EXCLUDE_EXACT
        }
        # 整域名充当 keyword 的条目 (如 Sukka 的 DOMAIN-KEYWORD,xxx.clients6.google.com)
        # 若该域名已被精确/后缀规则覆盖, 则是纯冗余
        self.keyword = {
            k for k in self.keyword
            if not (is_domain(k) and (covered(k) or k in self.exact))
        }
        self.ips = {
            ip for ip in self.ips
            if not (ip[0] == "IP-ASN" and ip[1] in DROP_ASN)
        }

    def body_lines(self) -> list[str]:
        lines = [f"DOMAIN-KEYWORD,{k}" for k in sorted(self.keyword)]
        lines += [f"DOMAIN-SUFFIX,{s}" for s in sorted(self.suffix)]
        lines += [f"DOMAIN,{d}" for d in sorted(self.exact)]
        lines += [f"{t},{v},no-resolve" for t, v in sorted(self.ips)]
        return lines

    def mrs_domain_lines(self) -> list[str]:
        return ["+." + s for s in sorted(self.suffix)] + sorted(self.exact)

    def counts(self) -> str:
        return (
            f"keyword={len(self.keyword)} suffix={len(self.suffix)} "
            f"exact={len(self.exact)} ip={len(self.ips)}"
        )


def guard(name: str, value: int, minimum: int) -> None:
    if value < minimum:
        raise RuntimeError(f"{name}: 条目数 {value} 低于下限 {minimum}，上游可能异常，拒绝生成")


def build_ai() -> RuleSet:
    rs = RuleSet()
    metacubex = fetch(SRC_METACUBEX_AI)
    guard("metacubex ai", len(metacubex.splitlines()), 100)
    rs.add_classical(metacubex, metacubex_style=True)

    sukka = fetch(SRC_SUKKA_AI)
    guard("sukka ai", len([l for l in sukka.splitlines() if l.strip()]), 20)
    rs.add_classical(sukka)

    voice = fetch(SRC_SUKKA_VOICE_IP)
    guard(
        "sukka voice ip",
        len([l for l in voice.splitlines() if l.strip() and not l.strip().startswith("#")]),
        15,
    )
    rs.add_classical(voice)

    rabbit = fetch(SRC_RABBIT_AIGC)
    guard("rabbit aigc", len([l for l in rabbit.splitlines() if l.strip()]), 80)
    rs.add_classical(rabbit)

    acl = fetch(SRC_ACL_AI)
    guard("acl4ssr ai", len([l for l in acl.splitlines() if l.strip()]), 30)
    rs.add_classical(acl)

    plist = json.loads(fetch(SRC_PLIST_AI))
    guard("iplist ai 站点数", len(plist), 10)
    rs.add_plist_domains(plist)

    rs.finalize()
    guard("AI 总条目", len(rs.body_lines()), 120)
    return rs


def build_ozon() -> RuleSet:
    rs = RuleSet()
    rs.keyword.update(OZON_KEYWORD)
    rs.suffix.update(OZON_SUFFIX)

    plist = json.loads(fetch(OZON_PLIST_DOMAINS))
    total = sum(len(v) for v in plist.values())
    guard("iplist ozon 域名", total, 50)
    rs.add_plist_domains(plist)

    nets: list[str] = []
    for asn in OZON_ASN_LIST:
        data = json.loads(fetch(SRC_RIPESTAT + asn))
        prefixes = [p["prefix"] for p in data.get("data", {}).get("prefixes", [])]
        guard(f"RIPEstat AS{asn} 宣告前缀", len(prefixes), 3)
        nets.extend(prefixes)
    nets = sorted(set(nets))
    guard("Ozon CIDR 汇总", len(nets), 10)
    for net in nets:
        try:
            rs.ips.add(("IP-CIDR", str(ipaddress.ip_network(net, strict=False))))
        except ValueError as exc:
            raise RuntimeError(f"iplist 返回异常 CIDR {net!r}: {exc}") from exc

    rs.finalize()
    guard("Ozon 总条目", len(rs.body_lines()), 50)
    return rs


def header(title: str, sources: list[str]) -> str:
    lines = [f"# > {title} —— 自动生成，请勿手改（生成器: tools/gen_rulesets.py）"]
    lines.append("# 数据源:")
    lines += [f"#   - {s}" for s in sources]
    return NL.join(lines)


def render_surge(title: str, rs: RuleSet, sources: list[str]) -> str:
    return header(title, sources) + NL + NL.join(rs.body_lines()) + NL


def render_mihomo_yaml(title: str, rs: RuleSet, sources: list[str]) -> str:
    body = NL.join(f"  - {line}" for line in rs.body_lines())
    return header(title, sources) + NL + "payload:" + NL + body + NL


def render_mrs_src(rs: RuleSet) -> str:
    return NL.join(rs.mrs_domain_lines()) + NL


def write_if_changed(path: Path, data: str | bytes) -> bool:
    data_bytes = data.encode("utf-8") if isinstance(data, str) else data
    if path.exists() and path.read_bytes() == data_bytes:
        return False
    path.write_bytes(data_bytes)
    return True


def convert_mrs(mihomo: str, name: str, src_text: str, dst: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / (name + ".txt")
        src.write_text(src_text, encoding="utf-8")
        proc = subprocess.run(
            [mihomo, "convert-ruleset", "domain", "text", str(src), str(dst)],
            capture_output=True, text=True,
        )
    ok = proc.returncode == 0 and dst.exists() and dst.stat().st_size > 0
    if not ok:
        raise RuntimeError(f"mrs 编译失败 {name}: {proc.stderr.strip() or proc.stdout.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 Ozon / AI 规则集")
    ap.add_argument("--write", action="store_true", help="写回仓库文件（缺省只打印摘要）")
    ap.add_argument("--mihomo", default=None, help="mihomo 可执行文件路径，用于编译 .mrs")
    args = ap.parse_args()
    if args.mihomo and not Path(args.mihomo).exists():
        ap.error(f"--mihomo 文件不存在: {args.mihomo}")

    print("== 抓取并构建 AI ==", file=sys.stderr)
    ai = build_ai()
    print(f"AI: {ai.counts()}", file=sys.stderr)
    print("== 抓取并构建 Ozon ==", file=sys.stderr)
    ozon = build_ozon()
    print(f"Ozon: {ozon.counts()}", file=sys.stderr)

    outputs = [
        (SURGE_OUT / "Ozon.list", render_surge("Ozon", ozon, OZON_SOURCES)),
        (SURGE_OUT / "AI.list", render_surge("AI", ai, AI_SOURCES)),
        (MIHOMO_OUT / "Ozon.yaml", render_mihomo_yaml("Ozon", ozon, OZON_SOURCES)),
        (MIHOMO_OUT / "AI.yaml", render_mihomo_yaml("AI", ai, AI_SOURCES)),
    ]
    mrs_jobs = [
        ("Ozon", ozon, MIHOMO_OUT / "Ozon.mrs"),
        ("AI", ai, MIHOMO_OUT / "AI.mrs"),
    ]

    # AI 的域名 mrs 大小对条目变化不敏感 (数据本身冗余度高, trie 压缩
    # 把 103 与 91 个 exact 收敛到相近结果), 所以 mrs 变化检测不能只看 size,
    # 要看字节级 diff (write_if_changed 已按字节比较, 这里沿用)。
    if not args.write:
        for name, rs in (("Ozon", ozon), ("AI", ai)):
            print(f"[dry-run] {name}: {len(rs.body_lines())} 条 (mrs 域名 {len(rs.mrs_domain_lines())})")
        return 0

    changed = []
    for path, data in outputs:
        if write_if_changed(path, data):
            changed.append(str(path))
            print(f"已更新 {path}", file=sys.stderr)
    if args.mihomo:
        for name, rs, dst in mrs_jobs:
            before = dst.read_bytes() if dst.exists() else None
            convert_mrs(args.mihomo, name, render_mrs_src(rs), dst)
            if dst.read_bytes() != before:
                changed.append(str(dst))
                print(f"已更新 {dst}", file=sys.stderr)
    else:
        print("未提供 --mihomo，跳过 .mrs 编译", file=sys.stderr)

    print("变更文件: " + (", ".join(changed) if changed else "无"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
