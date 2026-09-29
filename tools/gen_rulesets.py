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
from datetime import datetime, timedelta, timezone
from pathlib import Path

NL = chr(10)
ROOT = Path(__file__).resolve().parent.parent
SURGE_OUT = ROOT / "Surge" / "Ruleset"
MIHOMO_OUT = ROOT / "Mihomo" / "Ruleset"
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
SRC_CATS_DOMAINSET = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/adrules_domainset.txt"
SRC_CATS_ALLOW = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/mod/rules/dns-allowlist.txt"
SRC_AWA_SURGE = "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Surge-RULE-SET.list"
SRC_SUKKA_REJECT = "https://raw.githubusercontent.com/SukkaW/Surge/master/Source/domainset/reject.conf"
SRC_SUKKA_REJECT_EXTRA = "https://raw.githubusercontent.com/SukkaW/Surge/master/Source/domainset/reject_extra.conf"
SRC_BLUESKY_ALL = "https://raw.githubusercontent.com/BlueSkyXN/AdGuardHomeRules/master/all.txt"
SRC_BLUESKY_LITE = "https://raw.githubusercontent.com/BlueSkyXN/AdGuardHomeRules/master/all-lite.txt"

ADS_TAGS = ["cats-domainset", "skk-reject", "awa-surge", "bluesky-abp"]
# Cats 官方白名单用于回剔误杀，单独记录（它不贡献规则，只做过滤）
ADS_ALLOWLIST = SRC_CATS_ALLOW

# 去广告的 NEVER_BLOCK: 这些域即使出现在广告源里也不拦 (核心基础设施 / 本仓库其他规则集的主体)
ADS_NEVER_BLOCK_SUFFIX = {
    # Apple 全家 (推送/支付/登录被误拦 = 全设备级故障)
    "apple.com", "icloud.com", "mzstatic.com", "cdn-apple.com",
    # 本仓库其他规则集的主体域, 拦截会自相矛盾
    "ozon.ru", "ozone.ru", "ozonru.cn",
    "openai.com", "chatgpt.com", "anthropic.com", "claude.ai", "gemini.google.com",

    # ── 上游 Cats domainset 整站收录的公共服务/国内核心域，误杀面大 ──
    # 静态资源 / CDN（整站拦截 → 页面大面积损坏）
    "jsdelivr.net", "akamai.net", "akamaiedge.net", "amazonaws.com", "cloudfront.net",
    "qpic.cn", "gtimg.cn", "alicdn.com", "bdstatic.com", "360buyimg.com",
    "googleapis.com", "gstatic.com",
    "aliyun.com", "aliyuncs.com", "qiniucdn.com", "bootcdn.net", "staticfile.org",
    # 国内核心电商 / 支付（整站拦截 → 交易阻断）
    "taobao.com", "tmall.com", "jd.com", "paypal.com", "alipay.com", "alipayobjects.com",
    "ebay.com",
    # 推送 / 统计 SDK（整站拦截 → 大量 App 收不到推送、统计丢失）
    "jpush.cn", "getui.com", "umeng.com", "umengcloud.com",
    # 跟踪 SDK 的公共域名：整站拦会把正常页面 JS 一并干掉
    "google-analytics.com", "googletagmanager.com",
    # 错误监控 / 统计 SDK（每个现代 App/网站都埋，整站拦 = 上报全丢）
    "sentry.io", "pstatp.com",
    # 搜索引擎 / 门户（上游误伤）
    "baidu.com", "xinhuanet.com",
    # 国外社交 / 门户（访问量大，整站拦截 = 全站不可用）
    "facebook.com", "fbcdn.net", "instagram.com", "twitter.com", "x.com", "twimg.com",
    # 国内门户 / 视频 / 社区
    "163.com", "126.com", "sina.com.cn", "sohu.com", "sogou.com",
    "toutiao.com", "douban.com", "youku.com", "iqiyi.com",
    "acg.tv", "bilibili.com", "zhimg.com", "zhihu.com",
    # 全量筛查器（audit_rules.py）P1 命中的其余关键服务
    "126.net", "sina.cn", "sinaimg.cn", "bdimg.com", "gtimg.com",
    "akamaihd.net", "azureedge.net", "cdn77.org", "huya.com",
    # 搜索引擎主域（微软必应整站被上游收录，整站拦 = 搜索引擎不可用）
    "bing.com", "bing.net",
}

ADS_NEVER_BLOCK_EXACT = {
    "apple.com", "www.apple.com", "icloud.com", "www.icloud.com",
    "ozon.ru", "www.ozon.ru", "ozone.ru", "www.ozone.ru",
    "ozonru.cn", "seller.ozonru.cn", "api-seller.ozonru.cn", "docs.ozonru.cn",
    "openai.com", "api.openai.com", "chatgpt.com", "chat.openai.com",
    "claude.ai", "anthropic.com",
}
LABEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")

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
    # 纯 Python 校验替代正则: 广告源里有海量长字符串 (CSS 选择器 / 路径
    # 片段), 正则嵌套量词在长非匹配串上灾难性回溯 (实测 22MB ABP 卡死)。
    if not value or len(value) > 253 or "." not in value:
        return False
    for label in value.split("."):
        if not label or len(label) > 63 or label[0] == "-" or label[-1] == "-":
            return False
        if not LABEL_CHARS.issuperset(label):
            return False
    return True


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


def parse_cats_domainset(text: str, rs: RuleSet) -> int:
    n = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("+.") or line.startswith("."):
            value = line.lstrip("+.").rstrip(".").lower()
        else:
            value = line.rstrip(".").lower()
        if is_domain(value):
            rs.suffix.add(value)
            n += 1
    return n


def parse_sukka_domainset(text: str, rs: RuleSet) -> int:
    n = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("."):
            value = line[1:].rstrip(".").lower()
            if is_domain(value):
                rs.suffix.add(value)
                n += 1
        elif is_domain(line.rstrip(".").lower()):
            rs.exact.add(line.rstrip(".").lower())
            n += 1
    return n


def parse_bluesky(text: str, rs: RuleSet) -> int:
    n = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("!", "#", "[", "@@")):
            continue
        value = None
        if line.startswith("||"):
            rest = line[2:]
            for cut in ("^", "$", "*"):
                idx = rest.find(cut)
                if idx != -1:
                    rest = rest[:idx]
            value = rest.rstrip(".").lower()
        elif line.startswith(("0.0.0.0 ", "127.0.0.1 ")):
            value = line.split(None, 1)[1].strip().rstrip(".").lower()
        else:
            value = line.rstrip(".").lower()
        if value and is_domain(value):
            rs.suffix.add(value)
            n += 1
    return n


def parse_cats_allowlist(text: str) -> set:
    allow = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        value = line.rstrip(".").lower()
        if is_domain(value):
            allow.add(value)
    return allow


def build_ads():
    domains = RuleSet()
    keywords = RuleSet()
    cats = fetch(SRC_CATS_DOMAINSET)
    cats_n = parse_cats_domainset(cats, domains)
    guard("cats domainset", cats_n, 10000)

    awa = fetch(SRC_AWA_SURGE)
    awa_lines = [l for l in awa.splitlines() if l.strip() and not l.startswith("#")]
    guard("awavenue", len(awa_lines), 500)
    for l in awa_lines:
        if l.strip().upper().startswith("DOMAIN-KEYWORD"):
            keywords.add_classical(l)
        else:
            domains.add_classical(l)

    n_sukka = parse_sukka_domainset(fetch(SRC_SUKKA_REJECT), domains)
    n_sukka += parse_sukka_domainset(fetch(SRC_SUKKA_REJECT_EXTRA), domains)
    guard("sukka reject", n_sukka, 3000)

    bluesky_n = parse_bluesky(fetch(SRC_BLUESKY_ALL, timeout=90), domains)
    bluesky_n += parse_bluesky(fetch(SRC_BLUESKY_LITE, timeout=90), domains)
    guard("bluesky", bluesky_n, 20000)

    allow = parse_cats_allowlist(fetch(SRC_CATS_ALLOW))
    guard("cats allowlist", len(allow), 100)

    def is_allowed(dom: str) -> bool:
        labels = dom.split(".")
        return any(
            ".".join(labels[i:]) in allow or ".".join(labels[i:]) in ADS_NEVER_BLOCK_SUFFIX
            for i in range(len(labels))
        )

    domains.finalize()
    domains.suffix = {
        s for s in domains.suffix
        if s not in allow and s not in ADS_NEVER_BLOCK_SUFFIX and not is_allowed(s)
    }
    domains.exact = {
        d for d in domains.exact
        if d not in allow and d not in ADS_NEVER_BLOCK_EXACT and not is_allowed(d)
    }
    keywords.finalize()
    keywords.keyword = {k for k in keywords.keyword if k and len(k) >= 4}
    guard("ads domains", len(domains.body_lines()), 20000)
    guard("ads keywords", len(keywords.keyword), 2)
    return domains, keywords


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
    return _header(title, sources, len(lines), DOMAINSET_NOTE) + NL + NL.join(lines) + NL


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
    if prev and path.exists():
        same = data.replace(BUILD_TIME, prev, 1)
        if path.read_bytes() == same.encode("utf-8"):
            return False
    if path.exists() and path.read_bytes() == now.encode("utf-8"):
        return False
    path.write_bytes(now.encode("utf-8"))
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
    global BUILD_TIME
    ap = argparse.ArgumentParser(description="生成 Ozon / AI / 去广告 规则集")
    ap.add_argument("--write", action="store_true", help="写回仓库文件（缺省只打印摘要）")
    ap.add_argument("--mihomo", default=None, help="mihomo 可执行文件路径，用于编译 .mrs")
    ap.add_argument("--stamp", default=None, help="文件头的构建时间 (UTC+8)，缺省取当前时间")
    args = ap.parse_args()
    if args.mihomo and not Path(args.mihomo).exists():
        ap.error(f"--mihomo 文件不存在: {args.mihomo}")

    # 构建时间: CI 传 --stamp（北京时间），本地跑取当前 UTC+8。
    BUILD_TIME = args.stamp or (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"))

    ai = build_ai()
    print(f"AI: {ai.counts()}", file=sys.stderr)
    ozon = build_ozon()
    print(f"Ozon: {ozon.counts()}", file=sys.stderr)
    ads_domains, ads_keywords = build_ads()
    print(f"Ads: {ads_domains.counts()} kw={ads_keywords.counts()}", file=sys.stderr)

    # ── 三类目统一结构：「纯域名主文件 + 非域名补充 (Extra)」 ────────────────
    #   Surge  : <Name>.list (DOMAIN-SET)          + <Name>.Extra.list (RULE-SET)
    #   Mihomo : <Name>.mrs  (behavior: domain)   + <Name>.Extra.yaml (classical)
    # Extra 为空则不生成（当前三类目都有非域名条目，故都会生成）。
    def extra_of(rs: RuleSet) -> RuleSet:
        e = RuleSet()
        e.keyword = set(rs.keyword)
        e.ips = set(rs.ips)
        return e

    ai_extra = extra_of(ai)
    ozon_extra = extra_of(ozon)
    ads_extra = ads_keywords  # build_ads 已单独拆出非域名部分

    outputs = [
        # Surge
        (SURGE_OUT / "Advertising.list", render_domainset("去广告", ads_domains, ADS_TAGS)),
        (SURGE_OUT / "Advertising.Extra.list", render_surge_ruleset("去广告", ads_extra, ADS_TAGS)),
        (SURGE_OUT / "AI.list", render_domainset("AI 服务（国外）", ai, AI_TAGS)),
        (SURGE_OUT / "AI.Extra.list", render_surge_ruleset("AI 服务（国外）", ai_extra, AI_TAGS)),
        (SURGE_OUT / "Ozon.list", render_domainset("Ozon 电商", ozon, OZON_TAGS)),
        (SURGE_OUT / "Ozon.Extra.list", render_surge_ruleset("Ozon 电商", ozon_extra, OZON_TAGS)),
        # Mihomo（域名走 .mrs；这里的文本版本供不便用二进制时引用）
        (MIHOMO_OUT / "AI.Extra.yaml", render_mihomo_classical("AI 服务（国外）", ai_extra, AI_TAGS)),
        (MIHOMO_OUT / "Ozon.Extra.yaml", render_mihomo_classical("Ozon 电商", ozon_extra, OZON_TAGS)),
        (MIHOMO_OUT / "Advertising.Extra.yaml", render_mihomo_classical("去广告", ads_extra, ADS_TAGS)),
    ]
    mrs_jobs = [
        ("Advertising", ads_domains, MIHOMO_OUT / "Advertising.mrs"),
        ("AI", ai, MIHOMO_OUT / "AI.mrs"),
        ("Ozon", ozon, MIHOMO_OUT / "Ozon.mrs"),
    ]
    # 上一版产物（旧命名），改造后由 <Name>.mrs + <Name>.Extra.yaml 取代
    stale = [
        MIHOMO_OUT / "AI.yaml",
        MIHOMO_OUT / "Ozon.yaml",
        MIHOMO_OUT / "Advertising.yaml",
    ]

    if not args.write:
        for name, rs, extra in (("Ads", ads_domains, ads_extra), ("AI", ai, ai_extra), ("Ozon", ozon, ozon_extra)):
            print(f"[dry-run] {name}: 域名 {len(rs.mrs_domain_lines())} 条 + Extra {len(extra.body_lines())} 条")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
