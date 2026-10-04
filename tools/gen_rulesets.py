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
SRC_CATS_DOMAINSET = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/adrules_domainset.txt"
SRC_CATS_ALLOW = "https://raw.githubusercontent.com/Cats-Team/AdRules/main/mod/rules/dns-allowlist.txt"
SRC_AWA_SURGE = "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Surge-RULE-SET.list"
SRC_SUKKA_REJECT = "https://raw.githubusercontent.com/SukkaW/Surge/master/Source/domainset/reject.conf"
SRC_SUKKA_REJECT_EXTRA = "https://raw.githubusercontent.com/SukkaW/Surge/master/Source/domainset/reject_extra.conf"
SRC_PUBLIC_SUFFIX = "https://publicsuffix.org/list/public_suffix_list.dat"

ADS_TAGS = ["cats-domainset", "skk-reject", "awa-surge"]
# Cats 官方白名单用于回剔误杀，单独记录（它不贡献规则，只做过滤）
ADS_ALLOWLIST = SRC_CATS_ALLOW

# 去广告的 NEVER_BLOCK: 这些域即使出现在广告源里也不拦 (核心基础设施 / 本仓库其他规则集的主体)
ADS_NEVER_BLOCK_SUFFIX: dict[str, str] = {
    # —— 溯源：每条都写明为什么放行，防止白名单腐烂（来源/理由）——
    # Apple 全家（推送/支付/登录被误拦 = 全设备级故障）
    "apple.com": "audit P1 苹果主域", "icloud.com": "audit P1 iCloud",
    "mzstatic.com": "audit P1 苹果图标 CDN", "cdn-apple.com": "audit P1 苹果 CDN",
    # 本仓库其他规则集的主体域（拦截会自相矛盾）
    "ozon.ru": "本仓库 Ozon 主体", "ozone.ru": "本仓库 Ozon 主体",
    "ozonru.cn": "本仓库 Ozon 中国域名",
    "openai.com": "本仓库 AI 主体", "chatgpt.com": "本仓库 AI 主体",
    "anthropic.com": "本仓库 AI 主体", "claude.ai": "本仓库 AI 主体",
    "gemini.google.com": "本仓库 AI 主体",
    # 静态资源 / CDN（整站拦截 → 页面大面积损坏）
    "jsdelivr.net": "audit 公共 CDN", "akamai.net": "audit Akamai CDN",
    "akamaiedge.net": "audit Akamai CDN", "amazonaws.com": "audit AWS",
    "cloudfront.net": "audit AWS CloudFront",
    "qpic.cn": "audit 腾讯图片", "gtimg.cn": "audit 腾讯系图片",
    "alicdn.com": "audit 阿里 CDN", "bdstatic.com": "audit 百度静态",
    "360buyimg.com": "audit 京东图片",
    "googleapis.com": "audit Google API", "gstatic.com": "audit Google 静态",
    "aliyun.com": "audit 阿里云", "aliyuncs.com": "audit 阿里云 OSS",
    "qiniucdn.com": "audit 七牛 CDN", "bootcdn.net": "audit BootCDN",
    "staticfile.org": "audit Staticfile CDN",
    # 国内核心电商 / 支付（整站拦截 → 交易阻断）
    "taobao.com": "audit 淘宝", "tmall.com": "audit 天猫",
    "jd.com": "audit 京东", "paypal.com": "audit PayPal",
    "alipay.com": "audit 支付宝", "alipayobjects.com": "audit 支付宝 CDN",
    "ebay.com": "audit eBay",
    # 推送 / 统计 SDK（整站拦截 → App 收不到推送、统计丢失）
    "jpush.cn": "audit 极光推送", "getui.com": "audit 个推",
    "umeng.com": "audit 友盟", "umengcloud.com": "audit 友盟云",
    # 跟踪 SDK 公共域名（整站拦会把正常页面 JS 一并干掉）
    "google-analytics.com": "audit GA", "googletagmanager.com": "audit GTM",
    # 错误监控 / 统计 SDK（每个现代 App 都埋，整站拦 = 上报全丢）
    "sentry.io": "audit P1 Sentry 错误监控", "pstatp.com": "audit P1 字节统计",
    # 搜索引擎 / 门户（上游误伤）
    "baidu.com": "audit 百度", "xinhuanet.com": "audit 新华网",
    # 国外社交 / 门户（访问量大，整站拦截 = 全站不可用）
    "facebook.com": "audit Facebook", "fbcdn.net": "audit FB CDN",
    "instagram.com": "audit Instagram", "twitter.com": "audit Twitter",
    "x.com": "audit X/Twitter", "twimg.com": "audit Twitter 图片",
    "t.co": "X 外链跳转必经的短链服务，拦截会阻断链接跳转",
    # 国内门户 / 视频 / 社区
    "163.com": "audit 网易", "126.com": "audit 网易邮箱",
    "sina.com.cn": "audit 新浪", "sohu.com": "audit 搜狐",
    "sogou.com": "audit 搜狗",
    "toutiao.com": "audit 今日头条", "douban.com": "audit 豆瓣",
    "youku.com": "audit 优酷", "iqiyi.com": "audit 爱奇艺",
    "acg.tv": "audit B站短域", "bilibili.com": "audit B站",
    "zhimg.com": "audit 知乎图片", "zhihu.com": "audit 知乎",
    # 全量筛查器（audit_rules.py）P1 命中的其余关键服务
    "126.net": "audit P1 网易", "sina.cn": "audit P1 新浪主域",
    "sinaimg.cn": "audit P1 新浪图片", "bdimg.com": "audit P1 百度图片",
    "gtimg.com": "audit P1 腾讯图片",
    "akamaihd.net": "audit P1 Akamai", "azureedge.net": "audit P1 Azure CDN",
    "cdn77.org": "audit P1 CDN77", "huya.com": "audit P1 虎牙",
    # 搜索引擎主域（微软必应整站被上游收录）
    "bing.com": "audit P1 必应", "bing.net": "audit 必应",
}

ADS_NEVER_BLOCK_EXACT: dict[str, str] = {
    "apple.com": "audit 苹果主域", "www.apple.com": "audit 苹果",
    "icloud.com": "audit iCloud", "www.icloud.com": "audit iCloud",
    "ozon.ru": "本仓库 Ozon", "www.ozon.ru": "本仓库 Ozon",
    "ozone.ru": "本仓库 Ozon", "www.ozone.ru": "本仓库 Ozon",
    "ozonru.cn": "本仓库 Ozon 中国域名",
    "seller.ozonru.cn": "本仓库 Ozon 卖家", "api-seller.ozonru.cn": "本仓库 Ozon API",
    "docs.ozonru.cn": "本仓库 Ozon 文档",
    "openai.com": "本仓库 AI", "api.openai.com": "本仓库 AI",
    "chatgpt.com": "本仓库 AI", "chat.openai.com": "本仓库 AI",
    "claude.ai": "本仓库 AI", "anthropic.com": "本仓库 AI",
}

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


def is_domain(value: str) -> bool:
    return normalize_domain(value) is not None


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
            value = normalize_domain(line[2:] if line.startswith("+.") else line[1:])
        else:
            value = normalize_domain(line)
        if value:
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
            value = normalize_domain(line[1:])
            if value:
                rs.suffix.add(value)
                n += 1
        elif normalize_domain(line):
            rs.exact.add(normalize_domain(line))
            n += 1
    return n


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


def build_ads(report: dict | None = None):
    domains = RuleSet()
    keywords = RuleSet()
    report = report if report is not None else {}
    report["sources"] = []

    def source_info(name: str, url: str, text: str, accepted: int) -> None:
        report["sources"].append({
            "name": name, "url": url,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "accepted": accepted,
        })

    cats = fetch(SRC_CATS_DOMAINSET)
    cats_rules = RuleSet()
    parse_cats_domainset(cats, cats_rules)
    cats_n = len(cats_rules.suffix)
    guard("cats domainset", cats_n, 10000)
    source_info("cats-domainset", SRC_CATS_DOMAINSET, cats, cats_n)
    domains.suffix.update(cats_rules.suffix)

    awa = fetch(SRC_AWA_SURGE)
    awa_rules = RuleSet()
    awa_rules.add_classical(awa)
    awa_n = len(awa_rules.exact) + len(awa_rules.suffix) + len(awa_rules.keyword)
    guard("awavenue parsed rules", awa_n, 500)
    source_info("awa-surge", SRC_AWA_SURGE, awa, awa_n)
    domains.exact.update(awa_rules.exact)
    domains.suffix.update(awa_rules.suffix)
    keywords.keyword.update(awa_rules.keyword)

    n_sukka = 0
    for name, url in (("skk-reject", SRC_SUKKA_REJECT), ("skk-reject-extra", SRC_SUKKA_REJECT_EXTRA)):
        text = fetch(url)
        source_rules = RuleSet()
        parse_sukka_domainset(text, source_rules)
        n = len(source_rules.exact) + len(source_rules.suffix)
        source_info(name, url, text, n)
        n_sukka += n
        domains.exact.update(source_rules.exact)
        domains.suffix.update(source_rules.suffix)
    guard("sukka reject", n_sukka, 3000)

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
    filter_ads_domains(domains, allow, public_suffixes, report)
    filter_ads_keywords(keywords, allow, report)
    guard("ads domains", len(domains.exact) + len(domains.suffix), 20000)
    guard("ads keywords", len(keywords.keyword), 2)
    report["output"] = {"suffix": len(domains.suffix), "exact": len(domains.exact),
                        "keywords": len(keywords.keyword)}
    print("Ads validation: " + json.dumps(report["removed"], ensure_ascii=False), file=sys.stderr)
    return domains, keywords


def filter_ads_domains(domains: RuleSet, allow: set[str],
                       public_suffixes: PublicSuffixList | None = None,
                       report: dict | None = None) -> None:
    """剔除受保护域名；独立于抓取，支持现有产物的定向修复与离线验证。"""
    # 双向保护：排除受保护域的后代，也排除会覆盖保护域的祖先后缀。
    def is_allowed(dom: str) -> bool:
        labels = dom.split(".")
        return any(
            ".".join(labels[i:]) in allow or ".".join(labels[i:]) in ADS_NEVER_BLOCK_SUFFIX
            for i in range(len(labels))
        )

    protected = allow | set(ADS_NEVER_BLOCK_SUFFIX) | set(ADS_NEVER_BLOCK_EXACT)
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
        and d not in ADS_NEVER_BLOCK_EXACT and not is_allowed(d)
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


def filter_ads_keywords(keywords: RuleSet, allow: set[str], report: dict | None = None) -> None:
    protected = allow | set(ADS_NEVER_BLOCK_SUFFIX) | set(ADS_NEVER_BLOCK_EXACT)
    before = set(keywords.keyword)
    keywords.keyword = {
        k for k in before if len(k) >= 4 and re.fullmatch(r"[a-z0-9._-]+", k)
        and not any(k in d for d in protected)
    }
    keywords.finalize()
    if report is not None:
        report.setdefault("removed", {})["unsafe_keyword"] = len(before - keywords.keyword)


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
    ads_report: dict = {}
    ads_domains, ads_keywords = build_ads(ads_report)
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
        (SURGE_ADS_OUT / "Advertising.list", render_domainset("去广告", ads_domains, ADS_TAGS)),
        (SURGE_ADS_OUT / "Advertising.Extra.list", render_surge_ruleset("去广告", ads_extra, ADS_TAGS)),
        (SURGE_OUT / "AI.list", render_domainset("AI 服务（国外）", ai, AI_TAGS)),
        (SURGE_OUT / "AI.Extra.list", render_surge_ruleset("AI 服务（国外）", ai_extra, AI_TAGS)),
        (SURGE_OUT / "Ozon.list", render_domainset("Ozon 电商", ozon, OZON_TAGS)),
        (SURGE_OUT / "Ozon.Extra.list", render_surge_ruleset("Ozon 电商", ozon_extra, OZON_TAGS)),
        # Mihomo（域名走 .mrs；这里的文本版本供不便用二进制时引用）
        (MIHOMO_OUT / "AI.Extra.yaml", render_mihomo_classical("AI 服务（国外）", ai_extra, AI_TAGS)),
        (MIHOMO_OUT / "Ozon.Extra.yaml", render_mihomo_classical("Ozon 电商", ozon_extra, OZON_TAGS)),
        (MIHOMO_ADS_OUT / "Advertising.Extra.yaml", render_mihomo_classical("去广告", ads_extra, ADS_TAGS)),
    ]
    mrs_jobs = [
        ("Advertising", ads_domains, MIHOMO_ADS_OUT / "Advertising.mrs"),
        ("AI", ai, MIHOMO_OUT / "AI.mrs"),
        ("Ozon", ozon, MIHOMO_OUT / "Ozon.mrs"),
    ]
    # 上一版产物（旧命名），改造后由 <Name>.mrs + <Name>.Extra.yaml 取代
    stale = [
        MIHOMO_OUT / "AI.yaml",
        MIHOMO_OUT / "Ozon.yaml",
        MIHOMO_ADS_OUT / "Advertising.yaml",
    ]

    if not args.write:
        if args.report:
            write_if_changed(Path(args.report), json.dumps(ads_report, ensure_ascii=False, indent=2) + NL)
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
    if args.report:
        write_if_changed(Path(args.report), json.dumps(ads_report, ensure_ascii=False, indent=2) + NL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
