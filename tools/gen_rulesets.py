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
import hashlib
import ipaddress
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rule_validation import PublicSuffixList, normalize_domain, validate_source_text

# Windows 下 Python 默认 stdout 是 cp1252，print 中文会 UnicodeEncodeError。
# 统一强制 UTF-8，保证两个 runner 输出一致。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

NL = chr(10)
ROOT = Path(__file__).resolve().parent.parent
SURGE_OUT = ROOT / "Surge" / "Ruleset"
SURGE_ADS_OUT = ROOT / "Surge" / "Advertising"
MIHOMO_OUT = ROOT / "Mihomo" / "Ruleset"
MIHOMO_ADS_OUT = ROOT / "Mihomo" / "Advertising"
UA = {"User-Agent": "Mozilla/5.0 (compatible; laincat-rules-gen/1.0)"}

# 文件头的时间戳：由 --stamp 覆盖（CI 传当前时间）；本地执行沿用固定值。
# 具体写入口在 main：内容有变化时才用新时间戳，否则沿用文件里已有的，
# 保证「内容没变 → 文件没变」（幂等），不会天天产生纯时间戳 diff。
BUILD_TIME = "1970-01-01 00:00:00"

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

# 文件头里的「上游来源」用短名（对齐 laincat/Rules 既有产物的写法），
# 完整 URL 见本文件顶部的常量区。
AI_TAGS = ["metacubex-ai", "skk-ai", "rabbitspec-aigc", "acl4ssr-ai", "iplist-ai", "skk-voice-ip"]
OZON_TAGS = ["local-baseline", "iplist-ozon-domains", "ripestat-asn"]

EXCLUDE_SUFFIX = {"deepseek.com", "pool.ntp.org"}
EXCLUDE_EXACT = {
    # iplist russia portal 的 ozon.ru 数据里混进了一条 m.wildberries.ru
    # (Ozon 页面引用了 Wildberries 的资源), 不应整域跟随
    "m.wildberries.ru",
}
DROP_ASN = {"13335", "20473"}

# --------------------------------------------------------------- 去广告 (Advertising)
SRC_CATS_SURGE_CONF = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/adrules-surge.conf"
SRC_CATS_MIHOMO_MRS = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/adrules-mihomo.mrs"
SRC_CATS_MIHOMO_DOMAINSET = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/adrules_domainset.txt"
SRC_CATS_ALLOW = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/mod/rules/dns-allowlist.txt"
SRC_AWA_SURGE = "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Surge-RULE-SET.list"
SRC_PUBLIC_SUFFIX = "https://publicsuffix.org/list/public_suffix_list.dat"

# ── SKK 分片骨架 ────────────────────────────────────────────────────────────
# 去广告的组织方式直接采用 SukkaW/Surge 的方案：一个来源分片对应一种**处置
# 策略**与一种**匹配代价**，用户按需组合，而不是面对一个 20 万条的巨型文件。
#
#   domainset/reject           纯域名，DOMAIN-SET，不触发 DNS 解析
#   domainset/reject_extra     同上但「补充包」，单独启用覆盖率会明显下降
#   non_ip/reject              关键词/通配/少量 IP，RULE-SET，不触发 DNS 解析
#   non_ip/reject-drop         高频遥测洪流，配 REJECT-DROP 静默丢包（不刷日志）
#   non_ip/reject-no-drop      需要拒绝但**保留** RST/drop 语义的条目
#   ip/reject                  CIDR / ASN，会触发 DNS 解析，必须放最后
#
# 分片取 SKK 的**已编译成品**（ruleset.skk.moe）而非 Source 源文件：成品已经
# 过了它的 trie 去重、子域包含收敛与白名单回剔，直接接入可省掉一整层重复
# 实现，且与 SKK 用户拿到的效果完全一致。
SRC_SUKKA_SURGE = "https://ruleset.skk.moe/List"


class SkkShard:
    """一个 SKK 分片的定义：来源、处置策略、平台无关的规则归属。

    Surge 的 REJECT-DROP / REJECT-NO-DROP 在 Mihomo 里没有对应策略，
    统一降级为 REJECT —— 这与 SKK 自己的 Mihomo 引用方式一致。

    minimum 是该分片**去重后**的条目数下限。用唯一值而不是行数，是为了让
    「上游重复刷同一行」骗不过健康检查。
    """

    def __init__(self, key: str, path: str, drop: str, mihomo: str,
                 note: str, minimum: int) -> None:
        self.key = key
        self.path = path
        self.drop = drop
        self.mihomo = mihomo
        self.note = note
        self.minimum = minimum

    @property
    def url(self) -> str:
        return f"{SRC_SUKKA_SURGE}/{self.path}"


# 处置策略沿用 SKK 的分派：drop 类用 REJECT-DROP / REJECT-NO-DROP，其余 REJECT。
SKK_ADS_SHARDS = [
    SkkShard("domainset_reject", "domainset/reject.conf", "REJECT", "REJECT",
              "纯域名主库，DOMAIN-SET，不触发 DNS 解析", 100000),
    SkkShard("domainset_extra", "domainset/reject_extra.conf", "REJECT", "REJECT",
              "纯域名补充库，需与主库同时启用", 50000),
    SkkShard("non_ip_drop", "non_ip/reject-drop.conf", "REJECT-DROP", "REJECT-DROP",
              "高频遥测端点，配 REJECT-DROP 静默丢包", 20),
    SkkShard("non_ip_nodrop", "non_ip/reject-no-drop.conf", "REJECT-NO-DROP", "REJECT",
              "需拒绝但保留 RST/drop 语义的条目", 20),
    SkkShard("non_ip", "non_ip/reject.conf", "REJECT", "REJECT",
              "关键词/通配等非 IP 规则，不触发 DNS 解析", 300),
    SkkShard("ip", "ip/reject.conf", "REJECT-DROP", "REJECT",
              "CIDR / ASN，会触发 DNS 解析，须放在 IP 类规则之后", 500),
]

ADS_SURGE_TAGS = ["skk-shards"] + ["cats-surge-conf", "awa-surge"]
ADS_MIHOMO_TAGS = ["skk-shards"] + ["cats-mihomo", "awa-surge"]
# Cats 官方白名单用于回剔误杀，单独记录（它不贡献规则，只做过滤）
ADS_ALLOWLIST = SRC_CATS_ALLOW

# 白名单完全采用 SukkaW/Surge 的 PREDEFINED_WHITELIST。
# 本仓库不再维护自己的 ALWAYS_ALLOW 表，避免双源腐化。
SRC_SUKKA_REJECT_DATA_SOURCE = (
    "https://raw.githubusercontent.com/SukkaW/Surge/master/"
    "Build/constants/reject-data-source.ts"
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
                text = resp.read().decode("utf-8-sig")
                validate_source_text(url, text, resp.headers.get("Content-Type", ""))
                return text
        except (UnicodeError, ValueError) as exc:
            raise RuntimeError(f"invalid source: {url} ({exc})") from exc
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed: {url} ({last})")


def fetch_bytes(url: str, tries: int = 3, timeout: int = 90) -> bytes:
    last: Exception | None = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            if not data:
                raise ValueError("empty binary source")
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch bytes failed: {url} ({last})")


def is_domain(value: str) -> bool:
    return normalize_domain(value) is not None


# DOMAIN-WILDCARD 模式允许的字符：域名可用字符 + 两种通配符
_WILDCARD_RE = re.compile(r"^[a-z0-9.*?_-]+$")


def normalize_wildcard(value: str) -> str | None:
    """校验并归一化一条 `DOMAIN-WILDCARD` 模式，非法返回 None。

    Surge 与 mihomo 都支持 `*`（任意长）与 `?`（单字符），**位置不限**，
    所以 `info.*.aleragroup.com`、`p2p*.qq.com` 都是合法模式 —— 早期实现
    只认 `*.foo.com` 前缀形式，把上游绝大多数通配整条丢掉了。

    只做形状校验，不做语义改写：必须含通配符、必须带点、最后一段必须是
    纯 TLD。宁可少拦，也不能生成引擎解析不了的规则（会被静默跳过）。
    """
    value = value.strip().lower().rstrip(".")
    if not value or ("*" not in value and "?" not in value):
        return None
    if not _WILDCARD_RE.fullmatch(value) or "." not in value:
        return None
    tld = value.rsplit(".", 1)[1]
    if "*" in tld or "?" in tld:
        return None
    if not re.fullmatch(r"[a-z]{2,}|xn--[a-z0-9-]+", tld):
        return None
    return value


class RuleSet:
    """suffix / exact / keyword / ip 四类条目的可去重集合。"""

    def __init__(self) -> None:
        self.suffix: set[str] = set()
        self.exact: set[str] = set()
        self.keyword: set[str] = set()
        self.wildcards: set[str] = set()
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
                value = normalize_domain(line[2:])
                if value:
                    self.suffix.add(value)
                continue
            parts = [p.strip() for p in line.split(",")]
            rtype = parts[0].upper()
            if rtype in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD") and len(parts) >= 2:
                value = parts[1].rstrip(".").lower() if rtype == "DOMAIN-KEYWORD" else normalize_domain(parts[1])
                if rtype == "DOMAIN" and value:
                    self.exact.add(value)
                elif rtype == "DOMAIN-SUFFIX" and value:
                    self.suffix.add(value)
                elif rtype == "DOMAIN-KEYWORD" and value:
                    self.keyword.add(value)
            elif rtype == "DOMAIN-WILDCARD" and len(parts) >= 2:
                value = normalize_wildcard(parts[1])
                if value:
                    self.wildcards.add(value)
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
                self.exact.add(normalize_domain(line))
            # URL-REGEX / PROCESS-* / 逻辑规则等: 兼容性差或价值低，丢弃

    def add_plist_domains(self, data: dict) -> None:
        """iplist 站点域名: 站点根 → 后缀；交叉根域条目 → 精确候选。"""
        for site, domains in data.items():
            site = normalize_domain(str(site))
            if site:
                self.suffix.add(site)
            for dom in domains or []:
                dom = normalize_domain(str(dom))
                if dom:
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

        # IP-CIDR 包含收敛: 子网被超网覆盖时冗余 (如 AS44386 宣告了 /22 又宣告 /24)。
        # 按 (起始地址, 前缀长) 排序后单趟扫描: 容器必然排在其子网之前,
        # 起点一旦离开容器范围就不会再回来, 记录当前容器即可 —— O(n log n)。
        v4 = sorted(
            (ipaddress.ip_network(v) for t, v in self.ips if t == "IP-CIDR"),
            key=lambda n: (int(n.network_address), n.prefixlen),
        )
        cur = None
        covered: set[str] = set()
        for net in v4:
            if cur and net.subnet_of(cur):
                covered.add(str(net))
            else:
                cur = net
        if covered:
            self.ips = {
                (t, v) for t, v in self.ips
                if not (t == "IP-CIDR" and v in covered)
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
        lines += [f"DOMAIN-WILDCARD,{w}" for w in sorted(self.wildcards)]
        lines += [f"DOMAIN-SUFFIX,{s}" for s in sorted(self.suffix)]
        lines += [f"DOMAIN,{d}" for d in sorted(self.exact)]
        lines += [f"{t},{v},no-resolve" for t, v in sorted(self.ips)]
        return lines

    def mrs_domain_lines(self) -> list[str]:
        return ["+." + s for s in sorted(self.suffix)] + sorted(self.exact)

    def unique_count(self) -> int:
        """去重后的真实条目数 —— 健康检查必须用这个，而不是行数。"""
        return (len(self.exact) + len(self.suffix) + len(self.keyword)
                + len(self.wildcards) + len(self.ips))

    def counts(self) -> str:
        return (
            f"keyword={len(self.keyword)} suffix={len(self.suffix)} "
            f"exact={len(self.exact)} wildcard={len(self.wildcards)} ip={len(self.ips)}"
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


def parse_cats_domainset(text: str, rs: RuleSet) -> int:
    n = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("+.") or line.startswith("."):
            value = normalize_domain(line[2:] if line.startswith("+.") else line[1:])
        else:
            value = normalize_domain(line)
        if value:
            rs.suffix.add(value)
            n += 1
    return n


def parse_cats_surge(text: str, domains: RuleSet, keywords: RuleSet,
                     report: dict | None = None) -> dict[str, int]:
    """解析 Cats 的 Surge 专用文件：主域名集 + Surge 独有的通配与关键词。

    `adrules-surge.conf` 里的 DOMAIN-SUFFIX 与官方 domainset 同源；
    Surge 的 DOMAIN-WILDCARD 支持任意位置通配，原样保留在 Surge 补充文件，
    不降级成会扩大匹配面的关键词。

    `unsupported` 只统计**我们看不懂的规则类型**（URL-REGEX / PROCESS-* /
    逻辑规则），它是硬错误；被主动丢弃的超宽通配（如 `adservice.google.*`
    这种跨所有 TLD 的模式）单独记进 `overbroad`，不算错误。
    """
    counts = {"suffix": 0, "keyword": 0, "wildcard": 0,
              "overbroad": 0, "unsupported": 0}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        rtype = parts[0].upper() if parts else ""
        if rtype == "DOMAIN-SUFFIX" and len(parts) >= 2:
            value = normalize_domain(parts[1])
            if value:
                domains.suffix.add(value)
                counts["suffix"] += 1
                continue
        elif rtype == "DOMAIN-WILDCARD" and len(parts) >= 2:
            value = normalize_wildcard(parts[1])
            if value:
                domains.wildcards.add(value)
                counts["wildcard"] += 1
            else:
                # 含通配符但形状不可用：多半是跨 TLD 的超宽模式
                counts["overbroad"] += 1
            continue
        elif rtype == "DOMAIN-KEYWORD" and len(parts) >= 2 and parts[1]:
            value = parts[1].lower()
            if len(value) >= 4:
                keywords.keyword.add(value)
                counts["keyword"] += 1
                continue
        counts["unsupported"] += 1
    if report is not None:
        report["cats_surge"] = counts
    return counts


def decode_mrs_domains(mihomo: str, url: str, payload: bytes | None = None) -> str:
    """把 mihomo domain .mrs 解码回文本，供合并、过滤与重新编译。

    直接复用官方二进制会绕过本仓库的公共后缀、核心服务与 `t.co` 保护；
    所以这里只把它当**域名来源**，仍走同一套清洗流水线。
    """
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "cats.mrs"
        out = Path(tmp) / "cats.txt"
        data.write_bytes(payload if payload is not None else fetch_bytes(url))
        proc = subprocess.run(
            [mihomo, "convert-ruleset", "domain", "mrs", str(data), str(out)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not out.exists() or not out.stat().st_size:
            raise RuntimeError("Cats mrs 解码失败: %s" % (proc.stderr.strip() or proc.stdout.strip()))
        return out.read_text(encoding="utf-8-sig")


def parse_sukka_domainset(text: str, rs: RuleSet) -> int:
    n = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("."):
            value = normalize_domain(line[1:])
            if value:
                rs.suffix.add(value)
                n += 1
        elif normalize_domain(line):
            rs.exact.add(normalize_domain(line))
            n += 1
    return n


def parse_skk_shard(text: str, rs: RuleSet) -> int:
    """解析一个 SKK 分片成品。

    成品是 **RULE-SET 语法**（非 domainset/reject.conf 那种裸域名）——不对：
    domainset/* 分片才是裸域名（前导 `.` 表后缀），non_ip/* 与 ip/* 是完整
    规则行。两种语法都要能吃，所以这里统一走 add_classical：它对裸域名行
    会按 metacubex 语义落进 exact，而前导 `.` 已在下面单独处理。
    """
    # 返回**唯一条目数**而不是行数：RuleSet 是去重集合，若按行计数，
    # 上游重复刷同一行就能骗过 guard() 的健康下限（真实条目远少于行数）。
    before = rs.unique_count()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//", ";")):
            continue
        if line.startswith("."):
            value = normalize_domain(line[1:])
            if value:
                rs.suffix.add(value)
            continue
        if line.startswith(("#", ";", "!")) or "=" in line.split(",")[0]:
            # 元数据行（`# $ meta_title`）与 [Section] 风格的行不属于规则
            continue
        rs.add_classical(line, metacubex_style=True)
    return rs.unique_count() - before


def parse_cats_allowlist(text: str) -> tuple[set, set]:
    """解析 Cats 官方白名单，返回 (精确域名集合, 正则/通配行集合)。

    特殊行（is[0-9]-ssl.mzstatic.com / *.jbzj.com 等）不能当普通域名，
    单独记下供审计；它们的父域大多已在白名单里，回剔时不影响结果。
    """
    allow = set()
    special = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        value = normalize_domain(line)
        if value:
            allow.add(value)
        elif "\\" in line or "*" in line or "^" in line or "[" in line:
            special.add(line)
    return allow, special


def parse_skk_whitelist(text: str) -> set[str]:
    """Parse PREDEFINED_WHITELIST from SKK reject-data-source.ts."""
    marker = re.search(r"PREDEFINED_WHITELIST\s*=\s*\[", text)
    if not marker:
        raise ValueError("PREDEFINED_WHITELIST not found")
    start = marker.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
        i += 1
    body = text[start:i - 1]
    body = re.sub(r"//[^\n]*", "", body)
    entries = re.findall(r"'([^']*)'|\"([^\"]*)\"", body)
    return {a or b for a, b in entries if a or b}


def build_ads(platform: str = "surge", mihomo: str | None = None,
              report: dict | None = None) -> dict[str, RuleSet]:
    """按 SKK 的分片方案构建去广告规则。

    返回 {shard_key: RuleSet}。分层规则：
      1. 六个 SKK 分片是**骨架**，决定每个分片装什么、怎么处置；
      2. Cats-Team / AWAvenue 只把 SKK 未覆盖的条目**补进对应分片**，
         严格沿用 SKK 的分类（域名进 domainset、关键词/通配进 non_ip 等）；
      3. 所有分片都过一遍同一套保护表与公共后缀清洗。
    """
    if platform not in ("surge", "mihomo"):
        raise ValueError("platform 必须是 surge 或 mihomo")
    report = report if report is not None else {}
    report["sources"] = []

    def source_info(name: str, url: str, payload, accepted: int) -> None:
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        report["sources"].append({
            "name": name, "url": url,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "accepted": accepted,
        })

    shards = {shard.key: RuleSet() for shard in SKK_ADS_SHARDS}
    n_sukka = 0
    for shard in SKK_ADS_SHARDS:
        text = fetch(shard.url)
        n = parse_skk_shard(text, shards[shard.key])
        source_info("skk-" + shard.key, shard.url, text, n)
        n_sukka += n
        guard("skk " + shard.key, n, shard.minimum)
    guard("sukka reject shards", n_sukka, 100000)

    # 骨架建立后记下 SKK 已覆盖的域名集：Cats / AWA 只补 SKK **没有**的条目。
    skk_domains: set[str] = set()
    for shard in SKK_ADS_SHARDS:
        if shard.key == "ip":
            continue
        skk_domains |= shards[shard.key].exact | shards[shard.key].suffix

    # ── Cats-Team：只补增量，按 SKK 的分类归位 ──────────────────────────────
    cats_shard = shards["domainset_extra"]
    cats_nonip = shards["non_ip"]

    # Cats 的「关键词 / 通配」这类非域名规则只出现在 adrules-surge.conf 里；
    # mihomo 侧的 domainset / .mrs 是纯域名产物。这两类规则两个平台都支持，
    # 所以都从 Surge conf 收这一份 —— 否则会出现 Surge 有 414 条通配、
    # mihomo 只有 15 条的取源不对称缺口，与「同一套分片」的意图相悖。
    cats_surge = fetch(SRC_CATS_SURGE_CONF)
    cats_surge_dom, cats_surge_kw = RuleSet(), RuleSet()
    cats_surge_counts = parse_cats_surge(
        cats_surge, cats_surge_dom, cats_surge_kw, report)
    if cats_surge_counts["unsupported"]:
        raise RuntimeError("Cats Surge 文件含 %d 条未支持规则"
                           % cats_surge_counts["unsupported"])
    guard("cats rule types",
          len(cats_surge_kw.keyword) + len(cats_surge_kw.wildcards)
          + len(cats_surge_dom.wildcards), 100)
    cats_nonip.keyword.update(cats_surge_kw.keyword)
    cats_nonip.wildcards.update(cats_surge_kw.wildcards)
    cats_nonip.wildcards.update(cats_surge_dom.wildcards)

    if platform == "surge":
        cats_tmp_dom = cats_surge_dom
        cats_n = (cats_surge_counts["suffix"] + cats_surge_counts["keyword"]
                  + cats_surge_counts["wildcard"])
        guard("cats surge conf", cats_n, 10000)
        source_info("cats-surge-conf", SRC_CATS_SURGE_CONF, cats_surge, cats_n)
    else:
        if mihomo:
            cats_source = SRC_CATS_MIHOMO_MRS
            cats_mrs = fetch_bytes(cats_source)
            cats_mihomo = decode_mrs_domains(mihomo, cats_source, cats_mrs)
            cats_digest = hashlib.sha256(cats_mrs).hexdigest()
        else:
            # 未提供 mihomo 时仍支持 dry-run：官方 domainset 与 .mrs 主域名同源。
            cats_source = SRC_CATS_MIHOMO_DOMAINSET
            cats_mihomo = fetch(cats_source)
            cats_digest = hashlib.sha256(cats_mihomo.encode("utf-8")).hexdigest()
        cats_rules = RuleSet()
        parse_cats_domainset(cats_mihomo, cats_rules)
        cats_n = len(cats_rules.suffix) + len(cats_rules.exact)
        guard("cats mihomo", cats_n, 10000)
        report["sources"].append({
            "name": "cats-mihomo-mrs" if mihomo else "cats-mihomo-domainset",
            "url": cats_source, "sha256": cats_digest, "accepted": cats_n,
        })
        cats_tmp_dom = cats_rules
        report["cats_mihomo"] = {"suffix": len(cats_rules.suffix),
                                 "exact": len(cats_rules.exact)}

    # 域名增量：SKK 未覆盖的才进补充分片
    inc_suffix = {s for s in cats_tmp_dom.suffix if s not in skk_domains}
    inc_exact = {d for d in cats_tmp_dom.exact if d not in skk_domains}
    cats_shard.suffix.update(inc_suffix)
    cats_shard.exact.update(inc_exact)
    report["cats_increment"] = {"suffix": len(inc_suffix), "exact": len(inc_exact),
                                "skk_covered_skipped": cats_n - len(inc_suffix) - len(inc_exact)}

    # ── AWAvenue：同样只补 SKK 缺失 ───────────────────────────────────────
    awa = fetch(SRC_AWA_SURGE)
    awa_rules = RuleSet()
    awa_rules.add_classical(awa)
    awa_n = len(awa_rules.exact) + len(awa_rules.suffix) + len(awa_rules.keyword)
    guard("awavenue parsed rules", awa_n, 500)
    source_info("awa-surge", SRC_AWA_SURGE, awa, awa_n)
    awa_inc_suffix = {s for s in awa_rules.suffix if s not in skk_domains}
    awa_inc_exact = {d for d in awa_rules.exact if d not in skk_domains}
    cats_shard.suffix.update(awa_inc_suffix)
    cats_shard.exact.update(awa_inc_exact)
    cats_nonip.keyword.update(
        {k for k in awa_rules.keyword if k not in cats_nonip.keyword})
    report["awa_increment"] = {
        "suffix": len(awa_inc_suffix), "exact": len(awa_inc_exact),
        "skk_covered_skipped": awa_n - len(awa_inc_suffix) - len(awa_inc_exact),
    }

    allow_text = fetch(SRC_CATS_ALLOW)
    allow, allow_special = parse_cats_allowlist(allow_text)
    guard("cats allowlist", len(allow), 100)
    if allow_special:
        print(f"Cats 白名单含 {len(allow_special)} 条未转换的正则/通配行，详见校验报告", file=sys.stderr)

    source_info("cats-allowlist", SRC_CATS_ALLOW, allow_text, len(allow))
    report["unhandled_allowlist_patterns"] = sorted(allow_special)
    psl_text = fetch(SRC_PUBLIC_SUFFIX)
    public_suffixes = PublicSuffixList.from_text(psl_text)
    guard("public suffix list", len(public_suffixes.exact), 5000)
    source_info("public-suffix-list", SRC_PUBLIC_SUFFIX, psl_text, len(public_suffixes.exact))
    # SKK only applies PREDEFINED_WHITELIST to domainset shards.
    rds_text = fetch(SRC_SUKKA_REJECT_DATA_SOURCE)
    skk_whitelist = parse_skk_whitelist(rds_text)
    guard("skk whitelist", len(skk_whitelist), 50)
    source_info("skk-reject-data-source", SRC_SUKKA_REJECT_DATA_SOURCE, rds_text, len(skk_whitelist))

    removed_acc: dict[str, int] = {}
    for key, rs in shards.items():
        shard_report: dict = {}
        # drop 层的语义与其他层相反：其它层是「拦下来保护用户」，drop 层是
        # 「高频遥测洪流，静默丢包」。这里整域被拦也不会让 App 立刻报错
        # （丢包 ≠ RST，客户端会重试），且 SKK 逐条挑选过。
        # 推送 SDK（jpush/getui/umeng）与遥测（data.microsoft 等）正是这一层的
        # 主体，若套用保护表会把这一层清空 —— 与 SKK 的意图相反。
        if shard.key == "non_ip_drop":
            rs.finalize()
        else:
            whitelist = skk_whitelist if shard.key.startswith("domainset") else set()
            filter_ads_domains(rs, allow, public_suffixes, shard_report, whitelist)
            filter_ads_keywords(rs, allow, shard_report, whitelist)
            filter_ads_wildcards(rs, allow, shard_report, whitelist)
            rs.finalize()
        for bucket, value in shard_report.get("removed", {}).items():
            removed_acc[bucket] = removed_acc.get(bucket, 0) + value
        samples = shard_report.get("samples")
        if samples:
            report.setdefault("samples", {}).setdefault(key, samples)
        guard(f"ads shard {key}", 
              len(rs.exact) + len(rs.suffix) + len(rs.keyword) + len(rs.wildcards) + len(rs.ips), 2)
        report.setdefault("shard_counts", {})[key] = {
            "suffix": len(rs.suffix), "exact": len(rs.exact),
            "keyword": len(rs.keyword), "wildcard": len(rs.wildcards),
            "ip": len(rs.ips),
        }
    if removed_acc:
        report["removed"] = removed_acc
    print("Ads validation: " + json.dumps(report["removed"], ensure_ascii=False), file=sys.stderr)
    return shards


def filter_ads_domains(domains: RuleSet, allow: set[str],
                       public_suffixes: PublicSuffixList | None = None,
                       report: dict | None = None,
                       whitelist: set[str] | None = None) -> None:
    """剔除受保护域名；独立于抓取，支持现有产物的定向修复与离线验证。"""
    whitelist = whitelist or set()
    wl_suffix = {v.lstrip(".") for v in whitelist if v.startswith(".")}
    wl_exact = {v for v in whitelist if not v.startswith(".")}

    # 双向保护：排除受保护域的后代，也排除会覆盖保护域的祖先后缀。
    def is_allowed(dom: str) -> bool:
        labels = dom.split(".")
        return any(
            ".".join(labels[i:]) in allow or ".".join(labels[i:]) in wl_suffix
            for i in range(len(labels))
        )

    protected = allow | wl_suffix | wl_exact
    unsafe_ancestors = {
        ".".join(labels[i:])
        for dom in protected for labels in [dom.split(".")]
        for i in range(len(labels))
    }
    old_suffix, old_exact = set(domains.suffix), set(domains.exact)
    public = {
        d for d in old_suffix | old_exact
        if public_suffixes and public_suffixes.is_public_suffix(d)
    }
    domains.suffix = {
        s for s in domains.suffix
        if normalize_domain(s) and s not in public
        and s not in unsafe_ancestors and not is_allowed(s)
    }
    domains.exact = {
        d for d in domains.exact
        if normalize_domain(d) and d not in public
        and d not in wl_exact and not is_allowed(d)
    }
    removed = (old_suffix - domains.suffix) | (old_exact - domains.exact)
    invalid = {d for d in old_suffix | old_exact if normalize_domain(d) is None}
    if report is not None:
        report["removed"] = {
            "invalid_domain": len(invalid),
            "public_suffix": len(public),
            "protected_domain": len(removed - public - invalid),
        }
        report["samples"] = {
            "public_suffix": sorted(public)[:50],
            "protected_domain": sorted(removed - public - invalid)[:20],
        }
    # Protection precedes compression so a rejected parent cannot erase safe children.
    domains.finalize()


def filter_ads_keywords(keywords: RuleSet, allow: set[str], report: dict | None = None,
                        whitelist: set[str] | None = None) -> None:
    whitelist = whitelist or set()
    protected = allow | {v.lstrip(".") for v in whitelist} | {
        v for v in whitelist if not v.startswith(".")
    }
    before = set(keywords.keyword)
    keywords.keyword = {
        k for k in before if len(k) >= 4 and re.fullmatch(r"[a-z0-9._-]+", k)
        and not any(k in d for d in protected)
    }
    keywords.finalize()
    if report is not None:
        report.setdefault("removed", {})["unsafe_keyword"] = len(before - keywords.keyword)


def wildcard_matches(pattern: str, domain: str) -> bool:
    """判断一条 `DOMAIN-WILDCARD` 模式是否命中某个具体域名。"""
    rx = "^" + "".join(
        ".*" if c == "*" else "." if c == "?" else re.escape(c) for c in pattern
    ) + "$"
    return re.fullmatch(rx, domain) is not None


def filter_ads_wildcards(wildcards: RuleSet, allow: set[str],
                         report: dict | None = None,
                         whitelist: set[str] | None = None) -> None:
    """丢掉会命中受保护域名的通配模式。

    通配的匹配面比精确/后缀都大，一条 `*-ad-sign.byteimg.com` 会连带命中
    白名单里的 `p3-ad-sign.byteimg.com`。与关键词同样处理：只要模式能匹配
    任一受保护域名，就整条丢弃 —— 宁可少拦，也不制造新的误杀。

    两种命中都要查：
      1. 模式直接匹配某个受保护的具体域名（含白名单里的精确主机）；
      2. 模式的**字面尾部**本身就是受保护域 —— 此时它的每一次匹配都落在
         该受保护域之下（`*-ad-sign.byteimg.com` 的尾部就是 `byteimg.com`）。
    """
    whitelist = whitelist or set()
    protected = allow | {v.lstrip(".") for v in whitelist} | {
        v for v in whitelist if not v.startswith(".")
    }

    def under_protected(dom: str) -> bool:
        return any(dom == p or dom.endswith("." + p) for p in protected)

    def literal_tail_is_protected(pattern: str) -> bool:
        labels = pattern.split(".")
        for i in range(len(labels)):
            tail = ".".join(labels[i:])
            if "*" in tail or "?" in tail:
                continue
            if "." in tail and under_protected(tail):
                return True
        return False

    before = set(wildcards.wildcards)
    wildcards.wildcards = {
        w for w in before
        if not any(wildcard_matches(w, d) for d in protected)
        and not literal_tail_is_protected(w)
    }
    if report is not None:
        report.setdefault("removed", {})["unsafe_wildcard"] = (
            len(before - wildcards.wildcards)
        )


def _header(title: str, sources: list[str], count: int, extra_lines: list[str] | None = None) -> str:
    """统一文件头: 标题 / 来源 / 构建时间 / 上游 / 条数 + 场景说明行。

    构建时间只在内容变化时刷新 (见 main 里的 stamp 参数): 否则每天重跑都会
    产生一条纯时间戳 diff, 与「有变化才提交」的 CI 策略冲突。
    """
    lines = [
        f"# {title}",
        "# 由 laincat/Rules 自动构建，请勿手工编辑（改动请改 tools/gen_rulesets.py）",
        f"# 构建时间: {BUILD_TIME} (UTC+8)",
        "# 上游来源: " + " + ".join(sources),
        f"# 规则条数: {count}",
    ]
    lines += extra_lines or []
    return NL.join(lines)


DOMAINSET_NOTE = [
    "# 格式：普通行 = 精确域名；前导 . = 该域名及全部子域",
    "# 只能被 Surge 的 DOMAIN-SET 规则引用，不能当 RULE-SET 用",
]
RULESET_NOTE = [
    "# 完整规则行，供 RULE-SET 引用",
]


def mihomo_note(behavior: str) -> list[str]:
    return [f"# 引用方式: behavior: {behavior}  （payload 语法随 behavior 变，写错会静默失效）"]


def render_surge_ruleset(title: str, rs: RuleSet, sources: list[str]) -> str:
    body = rs.body_lines()
    return _header(title + "（非域名类型）", sources, len(body), RULESET_NOTE) + NL + NL.join(body) + NL


def render_mihomo_classical(title: str, rs: RuleSet, sources: list[str]) -> str:
    """mihomo classical provider: payload 是完整规则行 (DOMAIN-KEYWORD /
    IP-CIDR / IP-ASN 等 mrs 表达不了的类型)。"""
    body = rs.body_lines()
    payload = NL.join(f"  - {line}" for line in body)
    head = _header(
        title + "（补充：非域名类型）", sources, len(body),
        mihomo_note("classical"),
    )
    return head + NL + "payload:" + NL + payload + NL


def render_mihomo_domain(title: str, rs: RuleSet, sources: list[str]) -> str:
    """mihomo domain provider 的文本版 (与 .mrs 同源，供不便用二进制时替换)."""
    body = rs.mrs_domain_lines()
    payload = NL.join(f"  - {line}" for line in body)
    head = _header(title + "（域名）", sources, len(body), mihomo_note("domain"))
    return head + NL + "payload:" + NL + payload + NL


def render_domainset(title: str, rs: RuleSet, sources: list[str]) -> str:
    """Surge DOMAIN-SET: 裸域名=精确, 前导 .=后缀(含自身)。
    注意不是 +. —— 那是 mihomo/Clash 的语法, Surge 不认。""";
    lines = ["." + s for s in sorted(rs.suffix)] + sorted(rs.exact)
    extra = [line for line in DOMAINSET_NOTE]
    return _header(title, sources, len(lines), extra) + NL + NL.join(lines) + NL


def render_surge_domainset_shard(shard: SkkShard, rs: RuleSet,
                                 sources: list[str]) -> str:
    """Surge DOMAIN-SET 分片：纯域名，不触发 DNS 解析。"""
    lines = ["." + s for s in sorted(rs.suffix)] + sorted(rs.exact)
    note = [f"# 处置策略: {shard.drop}", f"# {shard.note}"]
    return _header(f"去广告 · {shard.key}", sources, len(lines), note) + NL + NL.join(lines) + NL


def render_surge_ruleset_shard(shard: SkkShard, rs: RuleSet,
                               sources: list[str]) -> str:
    """Surge RULE-SET 分片：非域名类型，不触发 DNS 解析。"""
    body = rs.body_lines()
    note = [f"# 处置策略: {shard.drop}", f"# {shard.note}"]
    return _header(f"去广告 · {shard.key}", sources, len(body), note) + NL + NL.join(body) + NL


def render_mihomo_shard(shard: SkkShard, rs: RuleSet, sources: list[str]) -> str:
    """Mihomo classical provider：完整规则行，行为随分片语义固定。"""
    body = rs.body_lines()
    payload = NL.join(f"  - {line}" for line in body)
    head = _header(
        f"去广告 · {shard.key}", sources, len(body),
        [f"# 处置策略: {shard.mihomo}", f"# {shard.note}", *mihomo_note("classical")],
    )
    return head + NL + "payload:" + NL + payload + NL


def render_mrs_src(rs: RuleSet) -> str:
    return NL.join(rs.mrs_domain_lines()) + NL


def write_if_changed(path: Path, data: str | bytes) -> bool:
    data_bytes = data.encode("utf-8") if isinstance(data, str) else data
    if path.exists() and path.read_bytes() == data_bytes:
        return False
    path.write_bytes(data_bytes)
    return True


def _existing_time(path: Path) -> str | None:
    """从现有产物头部取出「构建时间」，用于时间戳幂等。"""
    if not path.exists():
        return None
    try:
        head = path.read_bytes()[:512].decode("utf-8", "replace")
    except OSError:
        return None
    for line in head.splitlines():
        if line.startswith("# 构建时间:"):
            value = line.split(":", 1)[1].strip()
            # 去掉 " (UTC+8)" 后缀，只留时间本体，否则比对永远不相等
            suffix = " (UTC+8)"
            if value.endswith(suffix):
                value = value[: -len(suffix)].strip()
            return value
    return None


def write_with_stamp(path: Path, data: str, stamp: str) -> bool:
    """写入产物；正文未变则沿用旧时间戳（幂等）。data 里含占位时间戳。"""
    now = data.replace(BUILD_TIME, stamp, 1)
    prev = _existing_time(path)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if prev and path.exists():
        same = data.replace(BUILD_TIME, prev, 1)
        if existing == same:
            return False
    if existing == now:
        return False
    path.write_bytes(now.encode("utf-8"))
    return True


def convert_mrs(mihomo: str, name: str, src_text: str, dst: Path) -> None:
    with tempfile.TemporaryDirectory(dir=dst.parent) as tmp:
        src = Path(tmp) / (name + ".txt")
        compiled = Path(tmp) / (name + ".mrs")
        src.write_text(src_text, encoding="utf-8")
        proc = subprocess.run(
            [mihomo, "convert-ruleset", "domain", "text", str(src), str(compiled)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not compiled.exists() or not compiled.stat().st_size:
            raise RuntimeError(f"mrs 编译失败 {name}: {proc.stderr.strip() or proc.stdout.strip()}")
        compiled.replace(dst)


def main() -> int:
    global BUILD_TIME
    ap = argparse.ArgumentParser(description="生成 Ozon / AI / 去广告 规则集")
    ap.add_argument("--write", action="store_true", help="写回仓库文件（缺省只打印摘要）")
    ap.add_argument("--mihomo", default=None, help="mihomo 可执行文件路径，用于编译 .mrs")
    ap.add_argument("--stamp", default=None, help="文件头的构建时间 (UTC+8)，缺省取当前时间")
    ap.add_argument("--report", default=None, help="写入去广告来源哈希与校验统计（JSON）")
    args = ap.parse_args()
    if args.mihomo and not Path(args.mihomo).exists():
        ap.error(f"--mihomo 文件不存在: {args.mihomo}")

    # 构建时间: CI 传 --stamp（北京时间），本地跑取当前 UTC+8。
    BUILD_TIME = args.stamp or (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"))

    ai = build_ai()
    print(f"AI: {ai.counts()}", file=sys.stderr)
    ozon = build_ozon()
    print(f"Ozon: {ozon.counts()}", file=sys.stderr)
    ads_surge_report: dict = {}
    ads_surge = build_ads("surge", report=ads_surge_report)
    for key, rs in ads_surge.items():
        print(f"Ads Surge[{key}]: {rs.counts()}", file=sys.stderr)
    ads_mihomo_report: dict = {}
    ads_mihomo = build_ads("mihomo", mihomo=args.mihomo, report=ads_mihomo_report)
    for key, rs in ads_mihomo.items():
        print(f"Ads Mihomo[{key}]: {rs.counts()}", file=sys.stderr)

    # ── 三类目统一结构：「纯域名主文件 + 非域名补充 (Extra)」 ────────────────
    #   Surge  : <Name>.list (DOMAIN-SET)          + <Name>.Extra.list (RULE-SET)
    #   Mihomo : <Name>.mrs  (behavior: domain)   + <Name>.Extra.yaml (classical)
    # Extra 为空则不生成（当前三类目都有非域名条目，故都会生成）。
    def extra_of(rs: RuleSet) -> RuleSet:
        e = RuleSet()
        e.keyword = set(rs.keyword)
        e.wildcards = set(rs.wildcards)
        e.ips = set(rs.ips)
        return e

    ai_extra = extra_of(ai)
    ozon_extra = extra_of(ozon)

    # 去广告分片文件名：沿用 SKK 的语义键，平台前缀区分。
    #   Surge : Advertising.<key>.list   domainset 分片用 DOMAIN-SET
    #           Advertising.<key>.list   non_ip / ip 分片用 RULE-SET
    #   Mihomo: Advertising.<key>.yaml   classical provider
    #           Advertising.<key>.mrs    domain provider（二进制）
    shard_file = {
        "domainset_reject": "Reject",
        "domainset_extra": "RejectExtra",
        "non_ip": "NonIP",
        "non_ip_drop": "Drop",
        "non_ip_nodrop": "NoDrop",
        "ip": "IP",
    }
    ads_outputs: list[tuple[Path, str]] = []
    ads_mrs: list[tuple[str, RuleSet, Path]] = []
    for shard in SKK_ADS_SHARDS:
        name = shard_file[shard.key]
        s_rs = ads_surge[shard.key]
        m_rs = ads_mihomo[shard.key]
        if shard.key.startswith("domainset"):
            ads_outputs.append((
                SURGE_ADS_OUT / f"Advertising.{name}.list",
                render_surge_domainset_shard(shard, s_rs, ADS_SURGE_TAGS)))
            ads_mrs.append((f"Advertising.{name}", m_rs,
                            MIHOMO_ADS_OUT / f"Advertising.{name}.mrs"))
        else:
            ads_outputs.append((
                SURGE_ADS_OUT / f"Advertising.{name}.list",
                render_surge_ruleset_shard(shard, s_rs, ADS_SURGE_TAGS)))
            ads_outputs.append((
                MIHOMO_ADS_OUT / f"Advertising.{name}.yaml",
                render_mihomo_shard(shard, m_rs, ADS_MIHOMO_TAGS)))

    outputs = [
        # Surge
        (SURGE_OUT / "AI.list", render_domainset("AI 服务（国外）", ai, AI_TAGS)),
        (SURGE_OUT / "AI.Extra.list", render_surge_ruleset("AI 服务（国外）", ai_extra, AI_TAGS)),
        (SURGE_OUT / "Ozon.list", render_domainset("Ozon 电商", ozon, OZON_TAGS)),
        (SURGE_OUT / "Ozon.Extra.list", render_surge_ruleset("Ozon 电商", ozon_extra, OZON_TAGS)),
        # Mihomo（域名走 .mrs；这里的文本版本供不便用二进制时引用）
        (MIHOMO_OUT / "AI.Extra.yaml", render_mihomo_classical("AI 服务（国外）", ai_extra, AI_TAGS)),
        (MIHOMO_OUT / "Ozon.Extra.yaml", render_mihomo_classical("Ozon 电商", ozon_extra, OZON_TAGS)),
    ] + ads_outputs
    mrs_jobs = [
        ("AI", ai, MIHOMO_OUT / "AI.mrs"),
        ("Ozon", ozon, MIHOMO_OUT / "Ozon.mrs"),
    ] + ads_mrs
    # 上一版产物（旧命名），改造后由 <Name>.mrs + <Name>.Extra.yaml 取代
    stale = [
        MIHOMO_OUT / "AI.yaml",
        MIHOMO_OUT / "Ozon.yaml",
        MIHOMO_ADS_OUT / "Advertising.yaml",
        MIHOMO_ADS_OUT / "Advertising.Extra.yaml",
        MIHOMO_ADS_OUT / "Advertising.mrs",
        MIHOMO_ADS_OUT / "Advertising.Reject.yaml",
        MIHOMO_ADS_OUT / "Advertising.RejectExtra.yaml",
        SURGE_ADS_OUT / "Advertising.list",
        SURGE_ADS_OUT / "Advertising.Extra.list",
        SURGE_ADS_OUT / "Advertising.Drop.rules",
        SURGE_ADS_OUT / "Advertising.NoDrop.rules",
        SURGE_ADS_OUT / "Advertising.NonIP.rules",
        SURGE_ADS_OUT / "Advertising.IP.rules",
    ]

    if not args.write:
        if args.report:
            report = {"surge": ads_surge_report, "mihomo": ads_mihomo_report}
            write_if_changed(Path(args.report),
                             json.dumps(report, ensure_ascii=False, indent=2) + NL)
        for name, rs, extra in (("AI", ai, ai_extra), ("Ozon", ozon, ozon_extra)):
            print(f"[dry-run] {name}: 域名 {len(rs.mrs_domain_lines())} 条 + Extra {len(extra.body_lines())} 条")
        for key, rs in ads_mihomo.items():
            print(f"[dry-run] Ads[{key}]: {rs.counts()}")
        return 0

    # 时间戳幂等: 先把「正文不含时间戳」的版本与现有文件比对，
    # 内容未变则沿用它已有的时间戳，避免每天产生纯时间戳 diff。
    changed = []
    for path, data in outputs:
        if write_with_stamp(path, data, BUILD_TIME):
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

    for path in stale:
        if path.exists():
            path.unlink()
            print(f"已删除废弃文件 {path}", file=sys.stderr)

    print("变更文件: " + (", ".join(changed) if changed else "无"))
    if args.report:
        report = {"surge": ads_surge_report, "mihomo": ads_mihomo_report}
        write_if_changed(Path(args.report),
                         json.dumps(report, ensure_ascii=False, indent=2) + NL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
