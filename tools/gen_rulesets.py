#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ozon / AI / 去广告 / Sukka 规则集生成器。

产物（全部由本脚本生成，勿手改）:
  Surge/Ruleset/Ozon.list   Surge DOMAIN-SET 域名主集
  Surge/Ruleset/AI.list     Surge DOMAIN-SET 域名主集
  Surge/Ruleset/*.Extra.list  Surge RULE-SET 非域名补集
  Mihomo/Ruleset/*.Extra.yaml mihomo classical 非域名补集
  Mihomo/Ruleset/Ozon.mrs   mihomo domain 二进制（需 --mihomo 提供 convert-ruleset）
  Mihomo/Ruleset/AI.mrs     mihomo domain 二进制
  Mihomo/Sukka/{domainset,non_ip,ip}/  Sukka 三层 Mihomo 规则
  Mihomo/Sukka/example.yaml            自动更新的单行引用范例

数据源（活跃度复核 2026-09-29）:
  AI   = MetaCubeX category-ai-chat-!cn（= v2fly domain-list-community 展开产物，不重复抓 v2fly）
       + SukkaW/Surge Source/non_ip/ai.conf
       + Rabbit-Spec/Surge Rules/AIGC.list
       + ACL4SSR Clash/Ruleset/AI.list
       + iplist.opencck.org 主站 ai 组域名（仅域名；其 CIDR 是 Cloudflare 整段聚合，误伤面过大，不用）
       + Kelee Clash AI 域名 + Loon AI 中已核验的共享云域名 AND 规则
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
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
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
MIHOMO_SUKKA_OUT = ROOT / "Mihomo" / "Sukka"
MIHOMO_CONFIG = ROOT / "Mihomo" / "config.yaml"
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
SRC_KELEE_AI = "https://kelee.one/Tool/Clash/Rule/AI.yaml"
SRC_KELEE_LOON_AI = "https://kelee.one/Tool/Loon/Lsr/AI.lsr"
KELEE_UA = "clash.meta"
# This China developer portal is not an overseas AI inference endpoint.
KELEE_EXCLUDE_EXACT = {"developer.amd.com.cn"}
KELEE_LOGICAL_PAIRS = {
    ("chatgpt-async-webps-prod-", "webpubsub.azure.com"),
    ("antigravity-auto-updater-", "run.app"),
}
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
AI_TAGS = ["metacubex-ai", "skk-ai", "rabbitspec-aigc", "acl4ssr-ai", "iplist-ai", "skk-voice-ip", "kelee-ai", "kelee-loon-ai"]
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
SRC_SUKKA_CLASH = "https://ruleset.skk.moe/Clash"


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

# --------------------------------------------------------------- Sukka 常规规则集
# 用户要求在 Mihomo/Sukka/ 目录下按 Sukka 的三个目录划分自动生成常规规则集。
# 与去广告分片不同：这里要保留 Sukka 对 domainset / non_ip / ip 的语义划分，
# 因为用户在 Mihomo 侧也会按同一顺序引用。

# 逐条 Sukka 分片定义：路径 / 最少条目数 / 语义说明。
# 与 SKK_ADS_SHARDS 不同：这里按平台划分而不是按处置策略划分。
@dataclass(frozen=True)
class SukkaList:
    """一个 Sukka 常规分片：子目录 / 成品路径 / 最少条目数 / 说明。

    清单顺序沿用 Sukka README 的推荐顺序，并始终保持
    ``domainset -> non_ip -> ip``。广告与 AI 清单不在此处定义。
    """

    directory: str     # domainset / non_ip / ip
    name: str          # 不带扩展名的文件名
    path: str          # ruleset.skk.moe 下的成品路径
    minimum: int
    note: str

    @property
    def url(self) -> str:
        return f"{SRC_SUKKA_CLASH}/{Path(self.path).with_suffix('.txt').as_posix()}"

    @property
    def file_base(self) -> str:
        return f"{self.directory}/{self.name}"


@dataclass
class SukkaRules:
    """Sukka 成品规则在进入 Mihomo 前的域名/classical 分层表示。

    ``USER-AGENT`` 与 ``URL-REGEX`` 是 Surge 专有类型，Mihomo 的 rule-provider
    不接受；Sukka 自己发布的 ``/Clash/`` 成品也会丢弃它们。本类显式计数，
    不会像通用 ``RuleSet`` 那样静默丢掉，也不会把它们写进无效 provider。
    """

    exact: set[str] = field(default_factory=set)
    suffix: set[str] = field(default_factory=set)
    classical: set[str] = field(default_factory=set)
    ip_cidrs: dict[str, bool] = field(default_factory=dict)
    ignored: dict[str, int] = field(default_factory=dict)

    def unique_count(self) -> int:
        return (
            len(self.exact)
            + len(self.suffix)
            + len(self.classical)
            + len(self.ip_cidrs)
        )

    def domain_lines(self) -> list[str]:
        return (
            ["+." + value for value in sorted(self.suffix)]
            + sorted(self.exact)
        )

    def yaml_lines(self, include_domains: bool = True,
                   include_ip_cidrs: bool = True) -> list[str]:
        # Only omit entries exported to an MRS trie. Classical fallback
        # DOMAIN rules (e.g. unifi / local) have no MRS representation in
        # this parser and must remain in the companion Extra provider.
        domain = []
        if include_domains:
            domain = ["DOMAIN-SUFFIX," + value for value in sorted(self.suffix)]
            domain += ["DOMAIN," + value for value in sorted(self.exact)]
        cidrs = []
        for value, no_resolve in sorted(self.ip_cidrs.items()):
            if not include_ip_cidrs:
                continue
            rule_type = (
                "IP-CIDR6"
                if ipaddress.ip_network(value).version == 6
                else "IP-CIDR"
            )
            suffix = ",no-resolve" if no_resolve else ""
            cidrs.append(f"{rule_type},{value}{suffix}")
        return domain + sorted(self.classical) + cidrs

    def payload_lines(self, behavior: str) -> list[str]:
        if behavior == "domain":
            return self.domain_lines()
        if behavior == "ipcidr":
            return sorted(self.ip_cidrs)
        if behavior == "classical":
            return self.yaml_lines()
        raise ValueError(f"unsupported behavior: {behavior}")

    def counts(self) -> str:
        ignored = " ".join(
            f"{name}={count}" for name, count in sorted(self.ignored.items())
        )
        return (
            f"suffix={len(self.suffix)} exact={len(self.exact)} "
            f"classical={len(self.classical)} ipcidr={len(self.ip_cidrs)}"
            + (f" ignored({ignored})" if ignored else "")
        )


# Sukka 的 marker 不是用户规则；它只用于验证文件真的由 Sukka 生成。
SUKKA_MARKER_DOMAINS = {
    "7h15.ru1353t.1s.m4d3.by.5ukk4w.skk.moe",
    "this_ruleset_is_made_by_sukkaw.ruleset.skk.moe",
}
SUKKA_IGNORED_TYPES = {"USER-AGENT", "URL-REGEX"}
SUKKA_CLASSICAL_TYPES = {
    "AND",
    "DOMAIN-KEYWORD",
    "DOMAIN-WILDCARD",
    "IP-ASN",
    "IP-CIDR",
    "IP-CIDR6",
    "NETWORK",
    "NOT",
    "OR",
    "PROCESS-NAME",
    "PROCESS-NAME-REGEX",
    "PROCESS-NAME-WILDCARD",
    "PROCESS-PATH",
    "PROCESS-PATH-REGEX",
}


# Sukka 常规规则集清单（去掉广告拦截与 AI 类目，用户仓库里已有对应规则）。
SUKKA_LISTS: list[SukkaList] = [
    # ── domainset ─────────────────────────────────────────────────────
    SukkaList("domainset", "speedtest", "domainset/speedtest.conf", 2000,
              "Speedtest 测速域名"),
    SukkaList("domainset", "cdn", "domainset/cdn.conf", 3000,
              "常见静态 CDN 域名"),
    SukkaList("domainset", "apple_cdn", "domainset/apple_cdn.conf", 100,
              "Apple CDN（自动生成）"),
    SukkaList("domainset", "download", "domainset/download.conf", 1000,
              "软件更新 / 大文件托管域名"),
    SukkaList("domainset", "game-download", "domainset/game-download.conf", 40,
              "游戏下载 CDN（不含国内 CDN，国内部分在 domestic）"),
    SukkaList("domainset", "icloud_private_relay",
              "domainset/icloud_private_relay.conf", 6,
              "iCloud Private Relay 域名"),
    # ── non_ip ───────────────────────────────────────────────────────
    SukkaList("non_ip", "sogouinput", "non_ip/sogouinput.conf", 10,
              "搜狗输入法回传"),
    SukkaList("non_ip", "cdn", "non_ip/cdn.conf", 60,
              "常见静态 CDN（关键词 / 通配）"),
    SukkaList("non_ip", "stream_us", "non_ip/stream_us.conf", 30,
              "北美流媒体"),
    SukkaList("non_ip", "stream_eu", "non_ip/stream_eu.conf", 8,
              "欧洲流媒体"),
    SukkaList("non_ip", "stream_jp", "non_ip/stream_jp.conf", 20,
              "日本流媒体"),
    SukkaList("non_ip", "stream_kr", "non_ip/stream_kr.conf", 2,
              "韩国流媒体"),
    SukkaList("non_ip", "stream_hk", "non_ip/stream_hk.conf", 20,
              "香港流媒体"),
    SukkaList("non_ip", "stream_tw", "non_ip/stream_tw.conf", 30,
              "台湾流媒体"),
    SukkaList("non_ip", "stream_biliintl", "non_ip/stream_biliintl.conf", 5,
              "哔哩哔哩国际版"),
    SukkaList("non_ip", "stream", "non_ip/stream.conf", 200,
              "所有流媒体"),
    SukkaList("non_ip", "telegram", "non_ip/telegram.conf", 10,
              "Telegram 域名"),
    SukkaList("non_ip", "apple_services", "non_ip/apple_services.conf", 20,
              "Apple 服务"),
    SukkaList("non_ip", "apple_cn", "non_ip/apple_cn.conf", 8,
              "Apple 中国大陆特供域名"),
    SukkaList("non_ip", "microsoft_cdn", "non_ip/microsoft_cdn.conf", 30,
              "Microsoft CDN（中国境内备案域名）"),
    SukkaList("non_ip", "microsoft", "non_ip/microsoft.conf", 50,
              "Microsoft 服务"),
    SukkaList("non_ip", "neteasemusic", "non_ip/neteasemusic.conf", 2,
              "网易云音乐"),
    SukkaList("non_ip", "download", "non_ip/download.conf", 8,
              "大文件托管（WILDCARD）"),
    SukkaList("non_ip", "lan", "non_ip/lan.conf", 30,
              "内网域名"),
    SukkaList("non_ip", "domestic_cdn", "non_ip/domestic_cdn.conf", 10,
              "中国大陆常见 CDN"),
    SukkaList("non_ip", "domestic", "non_ip/domestic.conf", 500,
              "中国大陆常见服务"),
    SukkaList("non_ip", "direct", "non_ip/direct.conf", 150,
              "无论身处何处都应直连的服务"),
    SukkaList("non_ip", "cloudmounter", "non_ip/cloudmounter.conf", 0,
              "CloudMounter / RaiDrive 的条件直连规则"),
    SukkaList("non_ip", "global", "non_ip/global.conf", 800,
              "其他国家/地区常见服务"),
    SukkaList("non_ip", "gitlab", "non_ip/gitlab.conf", 1,
              "GitLab 相关"),
    # ── ip ───────────────────────────────────────────────────────────
    SukkaList("ip", "stream_us", "ip/stream_us.conf", 0, "北美流媒体 IP"),
    SukkaList("ip", "stream_eu", "ip/stream_eu.conf", 0, "欧洲流媒体 IP"),
    SukkaList("ip", "stream_jp", "ip/stream_jp.conf", 0, "日本流媒体 IP"),
    SukkaList("ip", "stream_kr", "ip/stream_kr.conf", 0, "韩国流媒体 IP"),
    SukkaList("ip", "stream_hk", "ip/stream_hk.conf", 0, "香港流媒体 IP"),
    SukkaList("ip", "stream_tw", "ip/stream_tw.conf", 0, "台湾流媒体 IP"),
    SukkaList("ip", "stream_biliintl", "ip/stream_biliintl.conf", 0,
              "哔哩哔哩国际版 IP"),
    SukkaList("ip", "stream", "ip/stream.conf", 15, "所有流媒体 IP"),
    SukkaList("ip", "telegram", "ip/telegram.conf", 10, "Telegram IP CIDR"),
    SukkaList("ip", "telegram_asn", "ip/telegram_asn.conf", 5, "Telegram ASN"),
    SukkaList("ip", "teleproto", "ip/teleproto.conf", 10, "Telegram/MTPROTO IP"),
    SukkaList("ip", "apple_services", "ip/apple_services.conf", 10, "Apple 服务 IP"),
    SukkaList("ip", "neteasemusic", "ip/neteasemusic.conf", 15, "网易云音乐 IP"),
    SukkaList("ip", "download", "ip/download.conf", 8, "大文件托管 IP"),
    SukkaList("ip", "lan", "ip/lan.conf", 10, "局域网 IP"),
    SukkaList("ip", "domestic", "ip/domestic.conf", 2, "中国大陆 IP 补充"),
    SukkaList("ip", "cdn", "ip/cdn.conf", 3, "常见静态 CDN IP"),
    SukkaList("ip", "china_ip", "ip/china_ip.conf", 3000, "中国大陆 IPv4 CIDR"),
    SukkaList("ip", "china_ip_ipv6", "ip/china_ip_ipv6.conf", 2000, "中国大陆 IPv6 CIDR"),
]

# rule-providers 的顺序不影响匹配；rules 的顺序决定首个命中。此清单独立于
# SUKKA_LISTS，按 Sukka README 的章节顺序排列，并把更具体的清单放在同类宽泛
# 清单之前。任何 domainset / non_ip 必须排在所有 ip 规则之前。
SUKKA_RULE_ORDER: list[str] = [
    # domainset
    "domainset/speedtest",
    "domainset/cdn",
    "domainset/icloud_private_relay",
    "domainset/apple_cdn",
    "domainset/game-download",
    "domainset/download",
    # non_ip
    "non_ip/sogouinput",
    "non_ip/cdn",
    "non_ip/stream_us",
    "non_ip/stream_eu",
    "non_ip/stream_jp",
    "non_ip/stream_kr",
    "non_ip/stream_hk",
    "non_ip/stream_tw",
    "non_ip/stream_biliintl",
    "non_ip/stream",
    "non_ip/telegram",
    "non_ip/apple_services",
    "non_ip/apple_cn",
    "non_ip/microsoft_cdn",
    "non_ip/microsoft",
    "non_ip/neteasemusic",
    "non_ip/cloudmounter",
    "non_ip/download",
    "non_ip/lan",
    "non_ip/domestic_cdn",
    "non_ip/domestic",
    "non_ip/direct",
    "non_ip/gitlab",
    "non_ip/global",
    # ip
    "ip/stream_us",
    "ip/stream_eu",
    "ip/stream_jp",
    "ip/stream_kr",
    "ip/stream_hk",
    "ip/stream_tw",
    "ip/stream_biliintl",
    "ip/stream",
    "ip/telegram",
    "ip/telegram_asn",
    "ip/teleproto",
    "ip/apple_services",
    "ip/neteasemusic",
    "ip/download",
    "ip/lan",
    "ip/cdn",
    "ip/domestic",
    "ip/china_ip",
    "ip/china_ip_ipv6",
]

if set(SUKKA_RULE_ORDER) != {spec.file_base for spec in SUKKA_LISTS}:
    raise RuntimeError("SUKKA_RULE_ORDER must cover every Sukka source exactly once")
if len(SUKKA_RULE_ORDER) != len(set(SUKKA_RULE_ORDER)):
    raise RuntimeError("SUKKA_RULE_ORDER contains duplicate sources")

# These are only defaults for the maintained Mihomo config. The standalone
# example intentionally uses DIRECT so Mihomo can validate every provider
# without requiring a subscription or proxy group from the reader.
SUKKA_CONFIG_POLICIES: dict[str, str] = {
    "domainset/speedtest": "🎯 节点选择",
    "domainset/cdn": "🎯 节点选择",
    "domainset/icloud_private_relay": "DIRECT",
    "domainset/apple_cdn": "DIRECT",
    "domainset/game-download": "🎯 节点选择",
    "domainset/download": "🎯 节点选择",
    "non_ip/sogouinput": "REJECT",
    "non_ip/cdn": "🎯 节点选择",
    "non_ip/stream_us": "🇺🇸 美国",
    "non_ip/stream_eu": "🎯 节点选择",
    "non_ip/stream_jp": "🇯🇵 日本",
    "non_ip/stream_kr": "🇰🇷 韩国",
    "non_ip/stream_hk": "🇭🇰 香港",
    "non_ip/stream_tw": "🇹🇼 台湾",
    "non_ip/stream_biliintl": "📹 流媒体",
    "non_ip/stream": "📹 流媒体",
    "non_ip/telegram": "✈️ 电报",
    "non_ip/apple_services": "🎯 节点选择",
    "non_ip/apple_cn": "DIRECT",
    "non_ip/microsoft_cdn": "DIRECT",
    "non_ip/microsoft": "🎯 节点选择",
    "non_ip/neteasemusic": "DIRECT",
    "non_ip/cloudmounter": "DIRECT",
    "non_ip/download": "🎯 节点选择",
    "non_ip/lan": "DIRECT",
    "non_ip/domestic_cdn": "DIRECT",
    "non_ip/domestic": "DIRECT",
    "non_ip/direct": "DIRECT",
    "non_ip/gitlab": "🎯 节点选择",
    "non_ip/global": "🎯 节点选择",
    "ip/stream_us": "🇺🇸 美国",
    "ip/stream_eu": "🎯 节点选择",
    "ip/stream_jp": "🇯🇵 日本",
    "ip/stream_kr": "🇰🇷 韩国",
    "ip/stream_hk": "🇭🇰 香港",
    "ip/stream_tw": "🇹🇼 台湾",
    "ip/stream_biliintl": "📹 流媒体",
    "ip/stream": "📹 流媒体",
    "ip/telegram": "✈️ 电报",
    "ip/telegram_asn": "✈️ 电报",
    "ip/teleproto": "✈️ 电报",
    "ip/apple_services": "🎯 节点选择",
    "ip/neteasemusic": "DIRECT",
    "ip/download": "🎯 节点选择",
    "ip/lan": "DIRECT",
    "ip/cdn": "🎯 节点选择",
    "ip/domestic": "DIRECT",
    "ip/china_ip": "DIRECT",
    "ip/china_ip_ipv6": "DIRECT",
}

if set(SUKKA_CONFIG_POLICIES) != set(SUKKA_RULE_ORDER):
    raise RuntimeError("every Sukka source needs exactly one config policy")

SUKKA_CONFIG_PROVIDER_BEGIN = "  # BEGIN GENERATED SUKKA rule-providers"
SUKKA_CONFIG_PROVIDER_END = "  # END GENERATED SUKKA rule-providers"
SUKKA_CONFIG_DOMAIN_BEGIN = "  # BEGIN GENERATED SUKKA domainset + non_ip rules"
SUKKA_CONFIG_DOMAIN_END = "  # END GENERATED SUKKA domainset + non_ip rules"
SUKKA_CONFIG_IP_BEGIN = "  # BEGIN GENERATED SUKKA ip rules"
SUKKA_CONFIG_IP_END = "  # END GENERATED SUKKA ip rules"

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


def fetch(url: str, tries: int = 3, timeout: int = 30,
          user_agent: str | None = None) -> str:
    last: Exception | None = None
    for i in range(tries):
        try:
            headers = {**UA, "User-Agent": user_agent} if user_agent else UA
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8-sig")
                validate_source_text(url, text, resp.headers.get("Content-Type", ""))
                if user_agent:
                    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    print(f"[source] {url} HTTP={resp.status} UA={user_agent} "
                          f"sha256={digest}", file=sys.stderr)
                return text
        except (UnicodeError, ValueError) as exc:
            raise RuntimeError(f"invalid source: {url} ({exc})") from exc
        except Exception as exc:  # noqa: BLE001
            last = exc
            action = "retrying" if i + 1 < tries else "giving up"
            print(
                f"[fetch] {url} attempt={i + 1}/{tries} timeout={timeout}s "
                f"failed ({type(exc).__name__}: {exc}); {action}",
                file=sys.stderr,
            )
            if i + 1 < tries:
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


def normalize_sukka_domain(value: str) -> str | None:
    """Normalize a curated Sukka domain, allowing DNS service underscores.

    Public-host normalization intentionally rejects ``_``. Sukka's curated
    lists contain service labels such as ``sptkh1_tc.taiwanmobile.com`` and
    Mihomo can compile them into a domain trie, so preserve them after a
    strict label check rather than silently deleting the rule.
    """
    normalized = normalize_domain(value)
    if normalized:
        return normalized

    candidate = value.strip().rstrip(".").lower()
    labels = candidate.split(".")
    if len(labels) < 2:
        return None
    ascii_labels = []
    for label in labels:
        try:
            ascii_label = label.encode("idna").decode("ascii")
        except UnicodeError:
            return None
        if not re.fullmatch(
            r"[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?",
            ascii_label,
        ):
            return None
        ascii_labels.append(ascii_label)
    candidate = ".".join(ascii_labels)
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return candidate
    return None


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
        self.logical: set[str] = set()

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
        lines += sorted(self.logical)
        lines += [f"{t},{v},no-resolve" for t, v in sorted(self.ips)]
        return lines

    def mrs_domain_lines(self) -> list[str]:
        return ["+." + s for s in sorted(self.suffix)] + sorted(self.exact)

    def unique_count(self) -> int:
        """去重后的真实条目数 —— 健康检查必须用这个，而不是行数。"""
        return (len(self.exact) + len(self.suffix) + len(self.keyword)
                + len(self.wildcards) + len(self.ips) + len(self.logical))

    def counts(self) -> str:
        return (
            f"keyword={len(self.keyword)} suffix={len(self.suffix)} "
            f"exact={len(self.exact)} wildcard={len(self.wildcards)} "
            f"logical={len(self.logical)} ip={len(self.ips)}"
        )


def guard(name: str, value: int, minimum: int) -> None:
    if value < minimum:
        raise RuntimeError(f"{name}: 条目数 {value} 低于下限 {minimum}，上游可能异常，拒绝生成")


def parse_kelee_ai(clash: str, loon: str) -> RuleSet:
    """Import domains and audited AND pairs, never whole shared-cloud suffixes."""
    rs = RuleSet()
    rs.add_classical(clash)
    guard("kelee clash domains", len(rs.exact) + len(rs.suffix), 150)
    loon_domains = RuleSet()
    loon_domains.add_classical(loon)
    guard("kelee loon domains", len(loon_domains.exact) + len(loon_domains.suffix), 150)
    for raw in loon.splitlines():
        line = re.sub(r"\s+", "", raw)
        if not line.startswith("AND,"):
            continue
        match = re.fullmatch(
            r"AND,\(\(DOMAIN-KEYWORD,([a-z0-9._-]+)\),"
            r"\(DOMAIN-SUFFIX,([a-z0-9.-]+)\)\)", line)
        if not match:
            raise RuntimeError(f"unrecognized Kelee AND syntax: {raw}")
        pair = match.groups()
        if pair in KELEE_LOGICAL_PAIRS:
            rs.logical.add(line)
        elif pair != ("openaicom-api-", "azurefd.net"):
            raise RuntimeError(f"unaudited Kelee AND scope: {raw}")
        # The openaicom-api- pair is already covered by DOMAIN-KEYWORD,openai.
    rs.exact -= KELEE_EXCLUDE_EXACT
    # Kelee is a domain supplement; keep the existing reviewed IP/keyword sources.
    rs.keyword.clear()
    rs.wildcards.clear()
    rs.ips.clear()
    print(f"[kelee] imported {rs.counts()}", file=sys.stderr)
    return rs


def fetch_kelee_with_mihomo(mihomo: str) -> tuple[str, str]:
    """Download through native HTTP providers using fresh, isolated core state."""
    urls = {"clash": SRC_KELEE_AI, "loon": SRC_KELEE_LOON_AI}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        config = {
            "mode": "direct", "log-level": "info", "global-ua": KELEE_UA,
            "external-controller": f"127.0.0.1:{port}",
            "dns": {"enable": False},
            "rule-providers": {
                name: {"type": "http", "behavior": "classical",
                       "format": "yaml" if name == "clash" else "text",
                       "url": url, "path": f"./{name}.txt", "interval": 86400}
                for name, url in urls.items()
            },
            "rules": [f"RULE-SET,{name},DIRECT" for name in urls] + ["MATCH,DIRECT"],
        }
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        log_path = root / "core.log"
        with log_path.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [str(Path(mihomo).resolve()), "-d", directory, "-f", str(config_path)],
                stdout=output, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                deadline = time.monotonic() + 60
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        with urllib.request.urlopen(
                                f"http://127.0.0.1:{port}/providers/rules", timeout=1) as r:
                            providers = json.load(r)["providers"]
                        if all(providers.get(name, {}).get("ruleCount", 0) >= 150
                               and (root / f"{name}.txt").exists() for name in urls):
                            texts = []
                            for name, url in urls.items():
                                data = (root / f"{name}.txt").read_bytes()
                                text = data.decode("utf-8-sig")
                                validate_source_text(url, text)
                                texts.append(text)
                                print(f"[source-core] {url} HTTP=2xx UA={KELEE_UA} "
                                      f"rules={providers[name]['ruleCount']} "
                                      f"sha256={hashlib.sha256(data).hexdigest()}",
                                      file=sys.stderr)
                            return texts[0], texts[1]
                    except (urllib.error.URLError, TimeoutError):
                        pass
                    time.sleep(0.5)
                output.flush()
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
                raise RuntimeError(f"mihomo Kelee download/parse failed:\n{detail}")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def build_ai(mihomo: str | None = None) -> RuleSet:
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

    kelee_texts = fetch_kelee_with_mihomo(mihomo) if mihomo else (
        fetch(SRC_KELEE_AI, user_agent=KELEE_UA),
        fetch(SRC_KELEE_LOON_AI, user_agent=KELEE_UA))
    kelee = parse_kelee_ai(*kelee_texts)
    rs.exact.update(kelee.exact)
    rs.suffix.update(kelee.suffix)
    rs.logical.update(kelee.logical)

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
            network = ipaddress.ip_network(net, strict=False)
            kind = "IP-CIDR" if network.version == 4 else "IP-CIDR6"
            rs.ips.add((kind, str(network)))
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
    """Resolve literal string arrays and named spreads without executing TypeScript.

    Fail closed on an unknown expression, missing constant, cycle or malformed
    array so a changed upstream format cannot silently discard protections.
    """
    cache: dict[str, set[str]] = {}
    visiting: set[str] = set()

    def parse(name: str) -> set[str]:
        if name in visiting:
            raise ValueError(f"Cyclic whitelist spread: {name}")
        if name in cache:
            return cache[name]
        marker = re.search(r"\b(?:export\s+)?const\s+" + re.escape(name)
                           + r"\s*=\s*\[", text)
        if not marker:
            raise ValueError(f"Whitelist array not found: {name}")
        visiting.add(name)
        pos = marker.end()
        values: set[str] = set()
        expect_value = True
        while True:
            skip = re.match(r"(?:\s+|//[^\n]*(?:\n|$)|/\*[\s\S]*?\*/)*", text[pos:])
            pos += skip.end()
            if pos >= len(text):
                raise ValueError(f"Unterminated whitelist array: {name}")
            if text[pos] == "]":
                tail = text[pos + 1:]
                end = re.match(r"(?:\s+|//[^\n]*(?:\n|$)|/\*[\s\S]*?\*/)*(?:as\s+const\s*)?(?:;|$)", tail)
                if not end:
                    raise ValueError(f"Unsupported whitelist array suffix in {name}")
                break
            if not expect_value:
                if text[pos] != ",":
                    raise ValueError(f"Unsupported whitelist expression in {name}")
                pos += 1
                expect_value = True
                continue
            spread = re.match(r"\.\.\.([A-Za-z_$][\w$]*)", text[pos:])
            literal = re.match(r"(['\"])([^'\"\\\r\n]*)\1", text[pos:])
            if spread:
                values.update(parse(spread.group(1)))
                pos += spread.end()
            elif literal:
                value = literal.group(2)
                domain = value[1:] if value.startswith(".") else value
                if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain):
                    raise ValueError(f"Invalid whitelist domain in {name}: {value!r}")
                values.add(value)
                pos += literal.end()
            else:
                raise ValueError(f"Unsupported whitelist expression in {name}")
            expect_value = False
        visiting.remove(name)
        cache[name] = values
        return values

    return parse("PREDEFINED_WHITELIST")


# Exact playback/thumbnail exception declared by HongGuo.sgmodule.
# A covering suffix must also be removed because pre-matching precedes DIRECT.
LOCAL_ADS_WHITELIST = {"p3-tt.byteimg.com"}


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
        if key == "non_ip_drop":
            rs.finalize()
        else:
            whitelist = (skk_whitelist | LOCAL_ADS_WHITELIST) if key.startswith("domainset") else set()
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
    print("Ads validation: " + json.dumps(report.get("removed", {}), ensure_ascii=False), file=sys.stderr)
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


def extra_of(rs: RuleSet) -> RuleSet:
    extra = RuleSet()
    extra.keyword = set(rs.keyword)
    extra.wildcards = set(rs.wildcards)
    extra.logical = set(rs.logical)
    extra.ips = set(rs.ips)
    return extra


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


def parse_sukka_list(text: str, directory: str) -> SukkaRules:
    """解析一个 Sukka 成品文件，并保留 Mihomo 可表达的全部规则类型。

    ``domainset`` 是裸域名语法；``non_ip`` / ``ip`` 是完整规则行。marker
    domain 会在计数和输出前剔除。Surge 专有的 ``USER-AGENT`` 与
    ``URL-REGEX`` 在 Mihomo 中不受支持，跳过并显式记数；未知类型则硬失败，
    避免上游格式变化后静默少规则。
    """
    if directory not in {"domainset", "non_ip", "ip"}:
        raise ValueError(f"unsupported Sukka directory: {directory}")

    parsed = SukkaRules()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//", ";", "!")):
            continue
        if line in SUKKA_MARKER_DOMAINS:
            continue

        if directory == "domainset":
            if line.startswith("+."):
                value = normalize_sukka_domain(line[2:])
                if not value:
                    raise RuntimeError(f"invalid Sukka domainset value: {line}")
                parsed.suffix.add(value)
            elif line.startswith("."):
                # In Clash syntax .example.com matches subdomains only;
                # +.example.com also matches the apex. The curated Clash
                # sources use +.; never silently apply Surge's dot semantics.
                raise RuntimeError(
                    f"unsupported subdomain-only Sukka Clash pattern: {line}"
                )
            else:
                value = normalize_sukka_domain(line)
                if not value:
                    raise RuntimeError(f"invalid Sukka domainset value: {line}")
                parsed.exact.add(value)
            continue

        # The large China CIDR files use one bare prefix per line.
        if directory == "ip" and "," not in line:
            try:
                network = ipaddress.ip_network(line, strict=False)
            except ValueError as exc:
                raise RuntimeError(
                    f"invalid Sukka IP value in {directory}: {line}"
                ) from exc
            value = str(network)
            if parsed.ip_cidrs.setdefault(value, False) is not False:
                raise RuntimeError(
                    f"conflicting Sukka IP resolution options: {line}"
                )
            continue

        parts = [part.strip() for part in line.split(",")]
        rule_type = parts[0].upper()
        if rule_type in SUKKA_IGNORED_TYPES:
            parsed.ignored[rule_type] = parsed.ignored.get(rule_type, 0) + 1
            continue
        if rule_type == "DOMAIN" and len(parts) >= 2:
            if parts[1] in SUKKA_MARKER_DOMAINS:
                continue
            value = normalize_sukka_domain(parts[1])
            # Single-label local names such as ``unifi`` are valid Mihomo
            # classical rules although our DNS normalizer intentionally
            # requires a public suffix.
            if value:
                parsed.exact.add(value)
            else:
                parsed.classical.add(line)
            continue
        if rule_type == "DOMAIN-SUFFIX" and len(parts) >= 2:
            if parts[1] in SUKKA_MARKER_DOMAINS:
                continue
            value = normalize_sukka_domain(parts[1])
            if value:
                parsed.suffix.add(value)
            else:
                parsed.classical.add(line)
            continue
        if rule_type in {"IP-CIDR", "IP-CIDR6"} and len(parts) >= 2:
            try:
                network = ipaddress.ip_network(parts[1], strict=False)
            except ValueError as exc:
                raise RuntimeError(
                    f"invalid Sukka {rule_type} value: {line}"
                ) from exc
            options = [part.lower() for part in parts[2:] if part]
            if options not in ([], ["no-resolve"]):
                raise RuntimeError(f"unsupported Sukka IP options: {line}")
            normalized_type = "IP-CIDR6" if network.version == 6 else "IP-CIDR"
            if normalized_type != rule_type:
                raise RuntimeError(
                    f"Sukka IP prefix version mismatch: {line}"
                )
            value = str(network)
            no_resolve = bool(options)
            if parsed.ip_cidrs.setdefault(value, no_resolve) != no_resolve:
                raise RuntimeError(
                    f"conflicting Sukka IP resolution options: {line}"
                )
            continue
        if rule_type in SUKKA_CLASSICAL_TYPES:
            parsed.classical.add(line)
            continue
        raise RuntimeError(
            f"unsupported Sukka rule type {rule_type!r} in {directory}: {line}"
        )
    return parsed


def build_sukka() -> dict[str, SukkaRules]:
    """抓取并解析 Sukka 常规规则组，返回 {file_base: SukkaRules}。"""
    out: dict[str, SukkaRules] = {}
    for spec in SUKKA_LISTS:
        rules = parse_sukka_list(fetch(spec.url), spec.directory)
        guard(f"sukka {spec.file_base}", rules.unique_count(), spec.minimum)
        out[spec.file_base] = rules
    return out


def render_sukka_yaml(title: str, rules: SukkaRules, sources: list[str],
                      behavior: str, note: str | None = None,
                      include_domains: bool = True,
                      include_ip_cidrs: bool = True) -> str:
    """渲染 Mihomo YAML provider。文件使用标准 payload 列表写法。"""
    if behavior == "domain":
        body = rules.domain_lines()
    elif behavior == "classical":
        body = rules.yaml_lines(
            include_domains=include_domains,
            include_ip_cidrs=include_ip_cidrs,
        )
    elif behavior == "ipcidr":
        body = sorted(rules.ip_cidrs)
    else:
        raise ValueError(f"unsupported behavior: {behavior}")
    payload = NL.join(f"  - {line}" for line in body)
    extra = [
        *( [f"# {note}"] if note else [] ),
        f"# 引用方式: behavior: {behavior}",
    ]
    if rules.ignored:
        ignored = " ".join(
            f"{name}={count}" for name, count in sorted(rules.ignored.items())
        )
        extra.append(f"# 已跳过 Mihomo 不支持的 Surge 类型: {ignored}")
    head = _header(title, sources, len(body), extra)
    return head + NL + "payload:" + NL + payload + NL


def render_sukka_mrs_src(rules: SukkaRules, behavior: str) -> str:
    """Render the text source consumed by ``mihomo convert-ruleset``."""
    return NL.join(rules.payload_lines(behavior)) + NL


@dataclass(frozen=True)
class SukkaArtifact:
    spec: SukkaList
    relative: str
    behavior: str
    file_format: str
    provider_id: str
    is_extra: bool = False
    no_resolve: bool = False

    @property
    def path(self) -> Path:
        return MIHOMO_SUKKA_OUT / self.relative

    @property
    def repo_path(self) -> str:
        return "Mihomo/Sukka/" + self.relative


def plan_sukka_artifacts(
    grouped: dict[str, SukkaRules],
) -> list[SukkaArtifact]:
    """按阈值规划可表达的 Mihomo 文件。

    - domainset >100：domain ``.mrs``。
    - non_ip >100：可进入 domain trie 的部分写 ``.mrs``，其余类型写
      ``.Extra.yaml``。
    - ip >100：可进入 IP trie 的 CIDR 写 ``ipcidr`` ``.mrs``，其余类型写
      ``.Extra.yaml``。
    - 其余清单写一个 classical/domain/ipcidr ``.yaml``。
    """
    artifacts: list[SukkaArtifact] = []
    for spec in SUKKA_LISTS:
        rules = grouped[spec.file_base]
        count = rules.unique_count()
        cidr_modes = set(rules.ip_cidrs.values())
        cidr_no_resolve = (
            next(iter(cidr_modes)) if len(cidr_modes) == 1 else None
        )
        if count == 0:
            continue
        provider_base = (
            "sukka-"
            + spec.file_base.replace("/", "-").replace("_", "-").lower()
        )
        split_domain = (
            count > 100
            and spec.directory in {"domainset", "non_ip"}
            and bool(rules.domain_lines())
        )
        if split_domain:
            artifacts.append(SukkaArtifact(
                spec=spec,
                relative=f"{spec.directory}/{spec.name}.mrs",
                behavior="domain",
                file_format="mrs",
                provider_id=provider_base,
            ))
            if rules.classical or rules.ip_cidrs:
                artifacts.append(SukkaArtifact(
                    spec=spec,
                    relative=f"{spec.directory}/{spec.name}.Extra.yaml",
                    behavior="classical",
                    file_format="yaml",
                    provider_id=provider_base + "-extra",
                    is_extra=True,
                ))
            continue
        if (
            count > 100
            and spec.directory == "ip"
            and cidr_no_resolve is not None
        ):
            artifacts.append(SukkaArtifact(
                spec=spec,
                relative=f"{spec.directory}/{spec.name}.mrs",
                behavior="ipcidr",
                file_format="mrs",
                provider_id=provider_base,
                no_resolve=cidr_no_resolve,
            ))
            if rules.exact or rules.suffix or rules.classical:
                artifacts.append(SukkaArtifact(
                    spec=spec,
                    relative=f"{spec.directory}/{spec.name}.Extra.yaml",
                    behavior="classical",
                    file_format="yaml",
                    provider_id=provider_base + "-extra",
                    is_extra=True,
                ))
            continue

        if spec.directory == "domainset":
            behavior = "domain"
        elif (
            spec.directory == "ip"
            and rules.ip_cidrs
            and not rules.exact
            and not rules.suffix
            and not rules.classical
            and cidr_no_resolve is not None
        ):
            behavior = "ipcidr"
        else:
            behavior = "classical"
        artifacts.append(SukkaArtifact(
            spec=spec,
            relative=f"{spec.directory}/{spec.name}.yaml",
            behavior=behavior,
            file_format="yaml",
            provider_id=provider_base,
            no_resolve=behavior == "ipcidr" and cidr_no_resolve is True,
        ))
    return artifacts


def ordered_sukka_artifacts(
    artifacts: list[SukkaArtifact],
) -> list[SukkaArtifact]:
    """Sort rules by Sukka matching order, keeping Extra directly after main."""
    positions = {source: index for index, source in enumerate(SUKKA_RULE_ORDER)}
    unknown = {
        artifact.spec.file_base for artifact in artifacts
        if artifact.spec.file_base not in positions
    }
    if unknown:
        raise RuntimeError(
            "Sukka artifacts missing from SUKKA_RULE_ORDER: "
            + ", ".join(sorted(unknown))
        )
    return sorted(
        artifacts,
        key=lambda artifact: (
            positions[artifact.spec.file_base],
            1 if artifact.is_extra else 0,
        ),
    )


def render_sukka_example(
    artifacts: list[SukkaArtifact], sources: list[str],
) -> str:
    """生成单行 provider / 单行 rule 的 Mihomo 引用范例。"""
    head = _header(
        "Sukka Mihomo 引用范例", sources, len(artifacts) + 1,
        [
            "# 规则匹配顺序: 具体清单优先，随后 domainset -> non_ip -> ip",
            "# 策略统一用 DIRECT 便于直接校验；复制后请按自己的代理组替换",
            "# 每个 rule-provider 与 rules 条目均为单行写法",
        ],
    )
    lines = [head, "rule-providers:"]
    for artifact in artifacts:
        url = (
            "https://raw.githubusercontent.com/laincat/Rules/main/"
            + artifact.repo_path
        )
        path = "./sukka/" + artifact.relative
        lines.append(
            f"  {artifact.provider_id}: {{type: http, "
            f"behavior: {artifact.behavior}, format: {artifact.file_format}, "
            f"interval: 43200, url: \"{url}\", path: \"{path}\"}}"
        )
    lines += ["", "rules:"]
    for artifact in ordered_sukka_artifacts(artifacts):
        options = ",no-resolve" if artifact.no_resolve else ""
        lines.append(
            f"  - RULE-SET,{artifact.provider_id},DIRECT{options}"
        )
    lines.append("  - MATCH,DIRECT")
    return NL.join(lines) + NL


def _replace_managed_config_block(
    lines: list[str],
    begin: str,
    end: str,
    body: list[str],
) -> list[str]:
    starts = [index for index, line in enumerate(lines) if line == begin]
    ends = [index for index, line in enumerate(lines) if line == end]
    if len(starts) != 1 or len(ends) != 1:
        raise RuntimeError(
            f"config markers must appear exactly once: {begin!r}, {end!r}"
        )
    if starts[0] >= ends[0]:
        raise RuntimeError(f"config marker order is invalid: {begin!r}")
    return lines[:starts[0] + 1] + body + lines[ends[0]:]


def sync_sukka_config(
    text: str,
    artifacts: list[SukkaArtifact],
) -> str:
    """Update only the managed Sukka blocks in Mihomo/config.yaml."""
    ordered = ordered_sukka_artifacts(artifacts)
    provider_lines = []
    for artifact in artifacts:
        anchor = "*rs_mrs" if artifact.file_format == "mrs" else "*rs_classical"
        url = (
            "https://cnb.cool/laincat/Rules/-/git/raw/main/"
            + artifact.repo_path
        )
        path = "./ruleset/Sukka/" + artifact.relative
        provider_lines.append(
            f"  {artifact.provider_id}: {{ <<: {anchor}, "
            f"behavior: {artifact.behavior}, url: \"{url}\", path: \"{path}\"}}"
        )

    domain_rule_lines = []
    ip_rule_lines = []
    for artifact in ordered:
        policy = SUKKA_CONFIG_POLICIES[artifact.spec.file_base]
        options = ",no-resolve" if artifact.no_resolve else ""
        line = f"  - RULE-SET,{artifact.provider_id},{policy}{options}"
        if artifact.spec.directory == "ip":
            ip_rule_lines.append(line)
        else:
            domain_rule_lines.append(line)

    lines = text.splitlines()
    lines = _replace_managed_config_block(
        lines,
        SUKKA_CONFIG_PROVIDER_BEGIN,
        SUKKA_CONFIG_PROVIDER_END,
        provider_lines,
    )
    lines = _replace_managed_config_block(
        lines,
        SUKKA_CONFIG_DOMAIN_BEGIN,
        SUKKA_CONFIG_DOMAIN_END,
        domain_rule_lines,
    )
    lines = _replace_managed_config_block(
        lines,
        SUKKA_CONFIG_IP_BEGIN,
        SUKKA_CONFIG_IP_END,
        ip_rule_lines,
    )
    return NL.join(lines) + NL


def render_sukka_artifact(
    artifact: SukkaArtifact, rules: SukkaRules, sources: list[str],
) -> str:
    role = "classical 补充" if artifact.is_extra else artifact.behavior
    title = f"Sukka · {artifact.spec.directory} · {artifact.spec.name} · {role}"
    return render_sukka_yaml(
        title, rules, sources, artifact.behavior, artifact.spec.note,
        include_domains=not (
            artifact.is_extra and artifact.spec.directory == "non_ip"
        ),
        include_ip_cidrs=not (
            artifact.is_extra and artifact.spec.directory == "ip"
        ),
    )


def write_if_changed(path: Path, data: str | bytes) -> bool:
    data_bytes = data.encode("utf-8") if isinstance(data, str) else data
    if path.exists() and path.read_bytes() == data_bytes:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(now.encode("utf-8"))
    return True


def convert_mrs(mihomo: str, name: str, src_text: str, dst: Path,
                behavior: str = "domain") -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dst.parent) as tmp:
        src = Path(tmp) / (name + ".txt")
        compiled = Path(tmp) / (name + ".mrs")
        src.write_text(src_text, encoding="utf-8")
        proc = subprocess.run(
            [mihomo, "convert-ruleset", behavior, "text", str(src), str(compiled)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not compiled.exists() or not compiled.stat().st_size:
            raise RuntimeError(f"mrs 编译失败 {name}: {proc.stderr.strip() or proc.stdout.strip()}")
        compiled.replace(dst)


def require_existing_mrs(paths: list[Path]) -> None:
    """Allow text-only writes while protecting threshold crossings."""
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(
            "未提供 --mihomo，且本轮需要生成以下缺失的 MRS；"
            "为避免删除旧 YAML 后留下失效引用，已拒绝写回: "
            + ", ".join(missing)
        )


def main() -> int:
    global BUILD_TIME
    ap = argparse.ArgumentParser(
        description="生成 Ozon / AI / Sukka / 去广告 规则集"
    )
    ap.add_argument("--write", action="store_true", help="写回仓库文件（缺省只打印摘要）")
    ap.add_argument("--mihomo", default=None, help="mihomo 可执行文件路径，用于编译 .mrs")
    ap.add_argument("--stamp", default=None, help="文件头的构建时间 (UTC+8)，缺省取当前时间")
    ap.add_argument("--report", default=None, help="写入去广告来源哈希与校验统计（JSON）")
    args = ap.parse_args()
    if args.mihomo and not Path(args.mihomo).exists():
        ap.error(f"--mihomo 文件不存在: {args.mihomo}")

    # 构建时间: CI 传 --stamp（北京时间），本地跑取当前 UTC+8。
    BUILD_TIME = args.stamp or (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"))

    ai = build_ai(args.mihomo)
    print(f"AI: {ai.counts()}", file=sys.stderr)
    ozon = build_ozon()
    print(f"Ozon: {ozon.counts()}", file=sys.stderr)
    sukka = build_sukka()
    for base, rules in sukka.items():
        print(f"Sukka[{base}]: {rules.counts()}", file=sys.stderr)
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

    # ── Sukka 常规规则集：Mihomo/Sukka/{domainset,non_ip,ip}/ ─────────────
    #   保持 Sukka 的三目录和 README 顺序。超过 100 条且 MRS 能表达的
    #   域名或 CIDR 部分写 .mrs；其余规则按目录语义写 .Extra.yaml。
    sukka_sources = ["skk-clash"]
    sukka_yaml_jobs: list[tuple[Path, str]] = []
    sukka_mrs_jobs: list[tuple[str, SukkaRules, Path, str]] = []
    sukka_artifacts = plan_sukka_artifacts(sukka)
    rules_by_spec = {
        spec.file_base: sukka[spec.file_base] for spec in SUKKA_LISTS
    }
    for artifact in sukka_artifacts:
        rules = rules_by_spec[artifact.spec.file_base]
        if artifact.file_format == "mrs":
            sukka_mrs_jobs.append((
                artifact.spec.file_base.replace("/", "-"),
                rules,
                artifact.path,
                artifact.behavior,
            ))
        else:
            sukka_yaml_jobs.append((
                artifact.path,
                render_sukka_artifact(artifact, rules, sukka_sources),
            ))
    sukka_yaml_jobs.append((
        MIHOMO_SUKKA_OUT / "example.yaml",
        render_sukka_example(sukka_artifacts, sukka_sources),
    ))
    outputs += sukka_yaml_jobs
    outputs.append((
        MIHOMO_CONFIG,
        sync_sukka_config(
            MIHOMO_CONFIG.read_text(encoding="utf-8"),
            sukka_artifacts,
        ),
    ))

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

    if args.write and not args.mihomo:
        require_existing_mrs(
            [job[2] for job in mrs_jobs]
            + [job[2] for job in sukka_mrs_jobs]
        )

    if not args.write:
        if args.report:
            report = {"surge": ads_surge_report, "mihomo": ads_mihomo_report}
            write_if_changed(Path(args.report),
                             json.dumps(report, ensure_ascii=False, indent=2) + NL)
        for name, rs, extra in (("AI", ai, ai_extra), ("Ozon", ozon, ozon_extra)):
            print(f"[dry-run] {name}: 域名 {len(rs.mrs_domain_lines())} 条 + Extra {len(extra.body_lines())} 条")
        for key, rs in ads_mihomo.items():
            print(f"[dry-run] Ads[{key}]: {rs.counts()}")
        for artifact in sukka_artifacts:
            rules = rules_by_spec[artifact.spec.file_base]
            print(
                f"[dry-run] Sukka[{artifact.repo_path}]: "
                f"{artifact.behavior}/{artifact.file_format} {rules.counts()}"
            )
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
        for name, rules, dst, behavior in sukka_mrs_jobs:
            before = dst.read_bytes() if dst.exists() else None
            convert_mrs(
                args.mihomo, name,
                render_sukka_mrs_src(rules, behavior), dst, behavior,
            )
            if dst.read_bytes() != before:
                changed.append(str(dst))
                print(f"已更新 {dst}", file=sys.stderr)
    else:
        print("未提供 --mihomo，跳过 .mrs 编译", file=sys.stderr)

    for path in stale:
        if path.exists():
            path.unlink()
            print(f"已删除废弃文件 {path}", file=sys.stderr)

    expected_sukka = {artifact.path for artifact in sukka_artifacts}
    expected_sukka.add(MIHOMO_SUKKA_OUT / "example.yaml")
    if MIHOMO_SUKKA_OUT.exists():
        for path in MIHOMO_SUKKA_OUT.rglob("*"):
            if (
                path.is_file()
                and path not in expected_sukka
                and path.suffix in {".mrs", ".yaml"}
            ):
                path.unlink()
                print(f"已删除过期 Sukka 产物 {path}", file=sys.stderr)

    print("变更文件: " + (", ".join(changed) if changed else "无"))
    if args.report:
        report = {"surge": ads_surge_report, "mihomo": ads_mihomo_report}
        write_if_changed(Path(args.report),
                         json.dumps(report, ensure_ascii=False, indent=2) + NL)
    return 0


if __name__ == "__main__":
    sys.exit(main())

