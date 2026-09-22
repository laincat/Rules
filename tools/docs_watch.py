#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集 Surge / Mihomo 上游状态，生成可每日刷新的知识库基线。

为什么需要它
------------
`Surge/Docs/` 与 `Mihomo/Docs/` 记的是**上游的版本与配置面状态**，
而"上游到底有没有变"这件事不该靠人肉记忆：

  · Surge 的 Beta 通道**会静默发版** —— appcast 里 build 号变了，
    Telegram 频道却没有对应公告（实测 #413 停在 2026-09-14）。
    只盯 TG 会漏；只盯版本号会误判（build 变了 ≠ 配置面变了）。
  · Mihomo 的 Alpha 分支每天都在动，但绝大多数是 bugfix、不涉配置面 ——
    需要"领先几条、分别是什么"才能判断要不要改文档。
  · 官方手册与知识库新增 / 改写页面时没有任何通知机制。

所以本脚本做三件事：
  1. 采集一组**机器可判定**的上游事实（版本 / build / 提交 / 页面清单 / 内容哈希）
  2. 与上次记录逐项对比，**只在真变化时**更新 `changed_at`
  3. 写出 `upstream.json`，并重写两份 readme.md 里的 AUTO 区块

自动化边界（必须说清楚）
------------------------
脚本能自动回答「**上游变了没有**」，不能自动回答「**变了之后文档该怎么写**」——
后者要读发布说明、要判断是否触及配置面，属于人的工作。
所以每日流水线只做两件事：刷新基线 + 有变化就开 / 更新一个 issue 提醒。

用法
----
    python tools/docs_watch.py                      # 两个目标都采集，写 state + 重写 AUTO 区块
    python tools/docs_watch.py --target surge       # 只采集 Surge
    python tools/docs_watch.py --dry-run            # 不写任何文件
    python tools/docs_watch.py --fail-on-change     # 有变化时退出 1（给 CI 做门禁用）

退出码默认恒为 0 —— 采集失败是网络问题，不该把流水线标红。
"""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import html as html_module
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

UA = {"User-Agent": "laincat-rules-docs-watch/1.0 (+https://github.com/laincat/Rules)"}
TIMEOUT = 30
WORKERS = 8

MANUAL_BASE = "https://manual.nssurge.com"
KB_BASE = "https://kb.nssurge.com"

# 更新日志的展示窗口（天）：一周内的高亮，更早的作为上下文保留。
CHANGELOG_DAYS = 7
CHANGELOG_EXTRA_DAYS = 30

TARGETS = {
    "surge": os.path.join(ROOT, "Surge", "Docs"),
    "mihomo": os.path.join(ROOT, "Mihomo", "Docs"),
}


# --------------------------------------------------------------------------- 基础工具

def log(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def week_start(days: int = CHANGELOG_DAYS) -> str:
    """最近一周的起点日期（UTC）。"""
    d = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return d.strftime("%Y-%m-%d")


def http_get(url: str, timeout: int = TIMEOUT) -> bytes | None:
    """抓取失败一律返回 None —— CI 网络策略不可控，不能让采集本身成为故障源。"""
    headers = dict(UA)
    # ⚠️ GitHub 的 REST API 对**匿名请求限流很紧**（按来源 IP 计，约 60 次/小时）。
    # 实测本机 IP 很快就被打到 403 `rate limit exceeded`，发布列表整个抓空 ——
    # 而抓空若直接落盘，更新日志就会变成一张空表。所以带 token 请求
    # （CI 用 `secrets.GITHUB_TOKEN`，本地用 `GITHUB_TOKEN` / `GH_TOKEN`）。
    if "api.github.com" in url:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
            headers["Accept"] = "application/vnd.github+json"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:                                        # noqa: BLE001
        return None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_of(hashes: dict[str, str]) -> str | None:
    """把「路径 -> 内容哈希」折叠成一个总指纹，用于一眼看出整站有没有动过。"""
    if not hashes:
        return None
    joined = "\n".join("%s\t%s" % (k, hashes[k]) for k in sorted(hashes))
    return sha256_hex(joined.encode())


def fetch_many(urls: list[str]) -> dict[str, bytes]:
    """并发抓一批（小）文件；失败的条目直接缺席，由调用方按 None 处理。"""
    out: dict[str, bytes] = {}
    if not urls:
        return out
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(http_get, u): u for u in urls}
        for fut in concurrent.futures.as_completed(futures):
            url = futures[fut]
            try:
                data = fut.result()
            except Exception:                                # noqa: BLE001
                data = None
            if data:
                out[url] = data
    return out


# --------------------------------------------------------------------------- Surge

def surge_appcast(kind: str) -> dict | None:
    """Surge Mac 的 appcast 是 Sparkle 格式。

    build 号藏在 `<enclosure ... sparkle:version="12350" ...>` 里，**不是独立标签** ——
    这一点很容易看错（同时还有 `sparkle:shortVersionString` 才是版本号）。
    """
    url = "https://nssurge.com/mac/latest/appcast-signed%s.xml" % ("-beta" if kind == "beta" else "")
    xml = http_get(url)
    if not xml:
        return None
    text = xml.decode("utf-8", "replace")
    items = re.findall(r"<item>(.*?)</item>", text, re.S)
    if not items:
        return None
    top = items[0]
    ver = re.search(r"<title>(?:Version\s*)?([\d.]+)</title>", top)
    build = re.search(r'sparkle:version="(\d+)"', top)
    return {
        "version": ver.group(1) if ver else None,
        "build": build.group(1) if build else None,
        "items": len(items),
    }


def surge_releases(kind: str) -> list[dict]:
    """把 appcast 解析成**带发布日期与发布说明**的版本列表。

    为什么这份数据要单独抓：appcast 的 `<markdownDescription>` 里就是官方
    完整的发布说明，而且**每个版本只保留一条**（同一版本的多个 beta build
    会在原地被覆盖）—— 也就是说 appcast 拿得到"版本级"日志，
    但拿不到"build 级"的中间过程（那要靠 TG 频道补）。

    这也是 nssurge.com/support/mac/release-notes 那个页面的**同一个数据源**：
    读它的 JS 可以看到它就是在 fetch `/mac/latest/appcast*.xml`，
    所以直接读 appcast 等价于读官方更新日志页，还省掉一次渲染。
    """
    url = "https://nssurge.com/mac/latest/appcast-signed%s.xml" % ("-beta" if kind == "beta" else "")
    xml = http_get(url)
    if not xml:
        return []
    text = xml.decode("utf-8", "replace")
    out: list[dict] = []
    for item in re.findall(r"<item>(.*?)</item>", text, re.S):
        ver = re.search(r'sparkle:shortVersionString="([\d.]+)"', item) \
            or re.search(r"<title>(?:Version\s*)?([\d.]+)</title>", item)
        build = re.search(r'sparkle:version="(\d+)"', item)
        pub = re.search(r"<pubDate>(\d+)</pubDate>", item)
        desc = re.search(r"(?s)<markdownDescription><!\[CDATA\[(.*?)\]\]></markdownDescription>", item)
        date = None
        if pub:
            try:
                date = datetime.datetime.fromtimestamp(
                    int(pub.group(1)), datetime.timezone.utc).strftime("%Y-%m-%d")
            except Exception:                                # noqa: BLE001
                date = None
        out.append({
            "version": ver.group(1) if ver else None,
            "build": build.group(1) if build else None,
            "date": date,
            "notes": (desc.group(1).strip() if desc else ""),
        })
    return out


def surge_tg_posts(limit: int = 40) -> list[dict]:
    """Telegram 频道的帖子（带时间与正文）。

    这里补的是 appcast **拿不到的那一层**：同一版本的多个 beta build。
    例如 Beta build 12320 → 12330 → 12350，appcast 里只剩最后一条，
    而频道里每次发版都有独立公告。
    """
    html = http_get("https://t.me/s/SurgeTestFlightFeed")
    if not html:
        return []
    text = html.decode("utf-8", "replace")
    ids = re.findall(r'data-post="SurgeTestFlightFeed/(\d+)"', text)
    times = re.findall(r'<time datetime="([^"]+)"', text)
    bodies = re.findall(r'(?s)<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', text)
    out: list[dict] = []
    for i, pid in enumerate(ids[:limit]):
        raw = bodies[i] if i < len(bodies) else ""
        plain = re.sub(r"<br\s*/?>", "\n", raw)
        plain = re.sub(r"<[^>]+>", "", plain)
        plain = html_module.unescape(plain).strip()
        out.append({
            "id": pid,
            "date": (times[i][:10] if i < len(times) else None),
            "text": plain,
        })
    return out


def surge_tg_max_id() -> int | None:
    """Telegram 频道的最大消息 ID。

    注意：**appcast 会静默发版而 TG 不公告**，所以这个值只作为"公告数"的参考，
    不能当"有没有新版"的判据 —— 反过来它也仍然有用：TG 涨了说明有公告可读。
    """
    html = http_get("https://t.me/s/SurgeTestFlightFeed")
    if not html:
        return None
    ids = [int(i) for i in re.findall(rb'data-post="SurgeTestFlightFeed/(\d+)"', html)]
    return max(ids) if ids else None


def surge_manual_pages() -> list[str]:
    """官方手册的页面清单来自 llms.txt（`- path/to.md: 描述` 形式）。

    必须排除 `## Entry Points` 里的 README.md / SUMMARY.md —— 它们是入口文件、
    不是内容页，算进去会多数 2 篇。
    """
    txt = http_get(MANUAL_BASE + "/llms.txt")
    if not txt:
        return []
    entry = {"README.md", "SUMMARY.md"}
    pages = re.findall(r"(?m)^-\s+(\S+\.md):", txt.decode("utf-8", "replace"))
    return [p for p in pages if p not in entry]


def surge_kb_pages() -> dict[str, list[str]]:
    """官方知识库（GitBook）的页面清单来自根部的 llms.txt，按语言分组。"""
    txt = http_get(KB_BASE + "/llms.txt")
    if not txt:
        return {}
    text = txt.decode("utf-8", "replace")
    urls = re.findall(r"(https://kb\.nssurge\.com/[^\s\)]+\.md)", text)
    out: dict[str, list[str]] = {"zh": [], "en": []}
    for u in urls:
        rest = u[len(KB_BASE) + 1:]
        if rest.startswith("surge-knowledge-base/zh/"):
            out["zh"].append(rest)
        elif rest.startswith("surge-knowledge-base/"):
            out["en"].append(rest)
    return out


def surge_ios_version() -> dict | None:
    """iOS 当前版本改用 **iTunes Lookup API**。

    为什么不读知识库的更新日志：那份 `release-notes/surge-ios.md` **明显滞后** ——
    实测停在第 5.14.6 条，而 App Store 上早已是 5.22.1。文档要写"iOS 最新版"
    就只能信 App Store。

    Mac 侧则相反：Surge Mac 不走 App Store，只能读 appcast。
    两个平台的版本来源**必须分开**，混用会得到错误结论。
    """
    data = http_get("https://itunes.apple.com/lookup?id=1442620678")
    if not data:
        return None
    try:
        r = json.loads(data)["results"][0]
    except Exception:                                        # noqa: BLE001
        return None
    return {
        "version": r.get("version"),
        "released": (r.get("currentVersionReleaseDate") or "")[:10],
        "app": r.get("trackName"),
    }


def surge_collect() -> tuple[dict, dict[str, str], dict]:
    facts: dict[str, object] = {}
    pages: dict[str, str] = {}
    log: dict = {}

    stable = surge_appcast("stable")
    if stable:
        facts["mac-stable"] = stable
    beta = surge_appcast("beta")
    if beta:
        facts["mac-beta"] = beta

    tg = surge_tg_max_id()
    if tg is not None:
        facts["tg-max-id"] = tg

    ios = surge_ios_version()
    if ios:
        facts["ios-stable"] = ios

    # 更新日志用的数据（版本 + 发布日期 + 发布说明）—— 不进 facts，
    # 它属于"历史记录"，参与状态比对只会让每次发版都误报"文档需复核"。
    log["stable"] = surge_releases("stable")
    log["beta"] = surge_releases("beta")
    log["tg"] = surge_tg_posts()

    manual = surge_manual_pages()
    if manual:
        facts["manual-pages"] = len(manual)
        fetched = fetch_many([MANUAL_BASE + "/" + p for p in manual])
        for p in manual:
            data = fetched.get(MANUAL_BASE + "/" + p)
            if data is not None:
                pages["manual/" + p] = sha256_hex(data)[:16]

    kb = surge_kb_pages()
    if kb.get("zh"):
        facts["kb-pages-zh"] = len(kb["zh"])
    if kb.get("en"):
        facts["kb-pages-en"] = len(kb["en"])
    kb_all = list(kb.get("zh", [])) + list(kb.get("en", []))
    if kb_all:
        fetched = fetch_many([KB_BASE + "/" + p for p in kb_all])
        for p in kb_all:
            data = fetched.get(KB_BASE + "/" + p)
            if data is not None:
                pages["kb/" + p] = sha256_hex(data)[:16]

    return facts, pages, log


# --------------------------------------------------------------------------- Mihomo

def mihomo_release() -> dict | None:
    data = http_get("https://api.github.com/repos/MetaCubeX/mihomo/releases/latest")
    if not data:
        return None
    try:
        d = json.loads(data)
    except Exception:                                        # noqa: BLE001
        return None
    return {"tag": d.get("tag_name"), "published": (d.get("published_at") or "")[:10]}


def mihomo_releases(limit: int = 8) -> list[dict]:
    """正式版的发布列表，含官方 release note 正文。

    mihomo 的正式版是**按月**发一个（实测 1.19.28→29→30→31 跨度约两个月），
    所以"最近一周"在正式版这条线上**大概率是空的** ——
    这正是要如实写出来的结论，不该硬凑。
    """
    data = http_get("https://api.github.com/repos/MetaCubeX/mihomo/releases?per_page=%d" % limit)
    if not data:
        return []
    try:
        items = json.loads(data)
    except Exception:                                        # noqa: BLE001
        return []
    out: list[dict] = []
    for d in items:
        if d.get("prerelease"):
            continue
        out.append({
            "tag": d.get("tag_name"),
            "date": (d.get("published_at") or "")[:10],
            "body": (d.get("body") or "").strip(),
        })
    return out


def mihomo_alpha_commits(limit: int = 60) -> list[dict]:
    """Alpha 分支的提交列表 —— 这是 mihomo 侧真正的"测试版日志"。

    Alpha 没有逐个 build 的发布公告，它的变更记录**就是提交历史**；
    正式版正是从这些提交里按周期挑出来打的 tag。
    """
    data = http_get("https://api.github.com/repos/MetaCubeX/mihomo/commits?sha=Alpha&per_page=%d" % limit)
    if not data:
        return []
    try:
        items = json.loads(data)
    except Exception:                                        # noqa: BLE001
        return []
    out: list[dict] = []
    for c in items:
        commit = c.get("commit") or {}
        msg = (commit.get("message") or "").split("\n")[0]
        out.append({
            "sha": (c.get("sha") or "")[:7],
            "date": (commit.get("committer", {}).get("date") or "")[:10],
            "message": msg,
        })
    return out


def mihomo_alpha() -> dict | None:
    data = http_get("https://api.github.com/repos/MetaCubeX/mihomo/commits/Alpha")
    if not data:
        return None
    try:
        d = json.loads(data)
    except Exception:                                        # noqa: BLE001
        return None
    return {"sha": d["sha"][:7], "date": d["commit"]["committer"]["date"][:10]}


def mihomo_alpha_ahead(release_tag: str | None) -> int | None:
    """正式版到 Alpha 之间差几条提交 —— 判断"要不要追 Alpha"的核心依据。

    光看"Alpha 又动了"没有意义（多数是 bugfix）；差几条、内容是什么才决定
    是否触及配置面。
    """
    if not release_tag:
        return None
    data = http_get("https://api.github.com/repos/MetaCubeX/mihomo/compare/%s...Alpha" % release_tag)
    if not data:
        return None
    try:
        return int(json.loads(data).get("ahead_by"))
    except Exception:                                        # noqa: BLE001
        return None


def mihomo_config_yaml() -> dict | None:
    """官方默认配置 `docs/config.yaml`（Alpha 分支）—— 配置面的**权威清单**。

    用哈希盯着它：字段增删改都会反映在这一个文件上，比翻 wiki 可靠。
    """
    data = http_get("https://raw.githubusercontent.com/MetaCubeX/mihomo/Alpha/docs/config.yaml")
    if not data:
        return None
    return {"sha256": sha256_hex(data)[:16], "size": len(data)}


def mihomo_metadocs() -> dict | None:
    """新版官网 wiki（wiki.metacubex.one）的**源仓库**就是 MetaCubeX/Meta-Docs。

    直接盯源码仓库比抓 HTML 可靠：sitemap 的 lastmod 只精确到天且整站一个值，
    而这里能看到每个提交动了哪些页。
    """
    data = http_get("https://api.github.com/repos/MetaCubeX/Meta-Docs/commits/main")
    if not data:
        return None
    try:
        d = json.loads(data)
    except Exception:                                        # noqa: BLE001
        return None
    return {"sha": d["sha"][:7], "date": d["commit"]["committer"]["date"][:10]}


def mihomo_wiki_sitemap() -> dict | None:
    """wiki 的 sitemap —— 只用来数页面量级，lastmod 整站同一个值（别当变更信号）。"""
    data = http_get("https://wiki.metacubex.one/sitemap.xml")
    if not data:
        return None
    text = data.decode("utf-8", "replace")
    locs = re.findall(r"<loc>([^<]+)</loc>", text)
    lastmods = sorted(set(re.findall(r"<lastmod>([\d-]+)</lastmod>", text)))
    return {"urls": len(locs), "lastmod": lastmods[-1] if lastmods else None}


def mihomo_yamls_repo() -> dict | None:
    """HenryChiao/MIHOMO_YAMLS —— 社区里最常被直接抄的配置合集，作参考实现盯版本。"""
    data = http_get("https://api.github.com/repos/HenryChiao/MIHOMO_YAMLS/commits/main")
    if not data:
        return None
    try:
        d = json.loads(data)
    except Exception:                                        # noqa: BLE001
        return None
    return {"sha": d["sha"][:7], "date": d["commit"]["committer"]["date"][:10]}


def mihomo_collect() -> tuple[dict, dict[str, str], dict]:
    facts: dict[str, object] = {}
    log: dict = {}

    rel = mihomo_release()
    if rel:
        facts["release"] = rel
    alpha = mihomo_alpha()
    if alpha:
        facts["alpha"] = alpha
    ahead = mihomo_alpha_ahead((rel or {}).get("tag"))
    if ahead is not None:
        facts["alpha-ahead"] = ahead

    cfg = mihomo_config_yaml()
    if cfg:
        facts["config-yaml"] = cfg
    docs = mihomo_metadocs()
    if docs:
        facts["metadocs"] = docs
    wiki = mihomo_wiki_sitemap()
    if wiki:
        facts["wiki"] = wiki
    yamls = mihomo_yamls_repo()
    if yamls:
        facts["community-yamls"] = yamls

    # 更新日志用的数据 —— 同样不进 facts（见 surge_collect 的说明）。
    log["releases"] = mihomo_releases()
    log["alpha"] = mihomo_alpha_commits()

    return facts, {}, log


# --------------------------------------------------------------------------- 状态合并

def merge_state(old: dict, facts: dict, pages: dict[str, str]) -> dict:
    """把新采集的值并进旧状态，**只在值真的变了**才更新 changed_at。

    为什么保留 changed_at：光看"当前值"没法回答"上次变化是什么时候"，
    而这正是判断"要不要现在去读发布说明"的依据。
    """
    stamp = now_iso()
    old_facts = (old or {}).get("facts") or {}
    old_pages = (old or {}).get("pages") or {}

    new_facts: dict[str, dict] = {}
    for key, value in facts.items():
        prev = old_facts.get(key)
        if prev and prev.get("value") == value:
            new_facts[key] = {"value": value, "changed_at": prev.get("changed_at", stamp)}
        else:
            new_facts[key] = {"value": value, "changed_at": stamp}

    # 采集失败的字段沿用上次的值与时间戳，避免一次网络抖动把基线抹成 null。
    for key, prev in old_facts.items():
        if key not in new_facts:
            new_facts[key] = prev

    # 页面哈希同理：这一轮没抓到的页保留上次结果，否则会误报"页面消失了"。
    new_pages = dict(old_pages)
    new_pages.update(pages)

    # 摘要指纹**必须在合并之后算**。
    # 采集时算过一次（只覆盖本轮抓成功的页），但那样有个致命缺陷：任意一页
    # 因超时抓失败，摘要就会变 —— 于是一次网络抖动被误报成「上游改版」。
    # 合并后的页集合是稳定的，摘要才真正只反映**内容**变化。
    manual_digest = digest_of({k: v for k, v in new_pages.items() if k.startswith("manual/")})
    kb_digest = digest_of({k: v for k, v in new_pages.items() if k.startswith("kb/")})
    if manual_digest:
        new_facts["manual-digest"] = _stamp_if_changed(
            old_facts, "manual-digest", manual_digest[:16], stamp)
    if kb_digest:
        new_facts["kb-digest"] = _stamp_if_changed(
            old_facts, "kb-digest", kb_digest[:16], stamp)

    # 更新日志**不进 facts**：它是"发布记录"而非"当前状态"，
    # 拿它参与变化比对只会让每次上游发版都触发"文档需复核"的误报
    # （发版本来就该记进日志，不等于文档正文要改）。

    # ⚠️ generated_at 只在**内容真的变了**时才刷新。
    # 否则每天都会因为「时间戳不同」产生一次无意义的提交 —— 巡检线上
    # 95% 的日子上游毫无变化，那种提交只会把 git 历史淹掉。
    same = (old_facts == new_facts) and (old_pages == new_pages)
    generated_at = (old or {}).get("generated_at", stamp) if same else stamp

    return {"generated_at": generated_at, "facts": new_facts, "pages": new_pages}


def _stamp_if_changed(old_facts: dict, key: str, value, stamp: str) -> dict:
    """值没变就沿用旧的 changed_at，变了才盖新时间戳。"""
    prev = old_facts.get(key)
    if prev and prev.get("value") == value:
        return {"value": value, "changed_at": prev.get("changed_at", stamp)}
    return {"value": value, "changed_at": stamp}


def diff_facts(old: dict, new: dict) -> list[str]:
    msgs: list[str] = []
    old_facts = (old or {}).get("facts") or {}
    new_facts = new.get("facts") or {}
    for key, entry in new_facts.items():
        prev = old_facts.get(key)
        if prev is None:
            continue                                    # 首次记录不算"变化"
        if prev.get("value") != entry.get("value"):
            msgs.append("%s: %s -> %s" % (key, json.dumps(prev.get("value"), ensure_ascii=False),
                                          json.dumps(entry.get("value"), ensure_ascii=False)))
    return msgs


def changed_pages(old: dict, new: dict) -> list[str]:
    old_pages = (old or {}).get("pages") or {}
    new_pages = new.get("pages") or {}
    if not old_pages:
        return []                    # 首次建立基线：全部页面都是"新的"，不算变化
    out = [k for k, v in new_pages.items() if k in old_pages and old_pages[k] != v]
    out += [k for k in new_pages if k not in old_pages]
    return sorted(out)


# --------------------------------------------------------------------------- 渲染

def _val(facts: dict, key: str, default="—"):
    entry = facts.get(key)
    return entry.get("value") if entry else default


def render_surge_block(state: dict) -> str:
    f = state["facts"]
    stable = _val(f, "mac-stable", {}) or {}
    beta = _val(f, "mac-beta", {}) or {}
    ios = _val(f, "ios-stable", {}) or {}
    lines = [
        "<!-- AUTO-STATE:BEGIN -->",
        "> ⚙️ **本节由 `tools/docs_watch.py` 每日自动重写，请勿手工编辑。**",
        "> 采集时间：%s（UTC）" % state["generated_at"],
        "",
        "| 上游 | 版本 | Build | 条目 / 页数 | 上次变化 |",
        "|---|---|---:|---:|---|",
        "| Surge Mac 稳定版（appcast） | %s | %s | %s | %s |" % (
            stable.get("version", "—"), stable.get("build", "—"), stable.get("items", "—"),
            _changed_at(f, "mac-stable")),
        "| Surge Mac Beta（appcast） | %s | %s | %s | %s |" % (
            beta.get("version", "—"), beta.get("build", "—"), beta.get("items", "—"),
            _changed_at(f, "mac-beta")),
        "| Surge iOS 稳定版（App Store） | %s | — | 发布于 %s | %s |" % (
            ios.get("version", "—"), ios.get("released", "—"), _changed_at(f, "ios-stable")),
        "| 官方手册 manual.nssurge.com | — | — | %s 页 | %s |" % (
            _val(f, "manual-pages"), _changed_at(f, "manual-pages")),
        "| 官方知识库 kb.nssurge.com | — | — | 中文 %s / 英文 %s 页 | %s |" % (
            _val(f, "kb-pages-zh"), _val(f, "kb-pages-en"), _changed_at(f, "kb-pages-zh")),
        "| Telegram @SurgeTestFlightFeed | — | — | 最大消息 ID %s | %s |" % (
            _val(f, "tg-max-id"), _changed_at(f, "tg-max-id")),
        "",
        "内容指纹（任意页面正文被改写都会变）：手册 `%s` · 知识库 `%s`" % (
            _val(f, "manual-digest"), _val(f, "kb-digest")),
        "",
        "> 判据提醒：**build 号变了 ≠ 配置面变了**。Beta 会静默发版（appcast 更新而",
        "> TG 无公告），且存在「build 涨了但发布说明逐字未变」的重构建 —— 必须读",
        "> 发布说明才能定论，所以本节只负责报告「变了」，不替你做结论。",
        ">",
        "> 版本来源**分平台**：Mac 走 appcast（有 build 号），iOS 走 App Store。",
        "> 知识库的 `release-notes/surge-ios.md` 长期滞后（实测停在 5.14.6），",
        "> 判断 iOS 最新版**不要**以它为准。",
        "<!-- AUTO-STATE:END -->",
    ]
    return "\n".join(lines)


def render_mihomo_block(state: dict) -> str:
    f = state["facts"]
    rel = _val(f, "release", {}) or {}
    alpha = _val(f, "alpha", {}) or {}
    cfg = _val(f, "config-yaml", {}) or {}
    docs = _val(f, "metadocs", {}) or {}
    wiki = _val(f, "wiki", {}) or {}
    yamls = _val(f, "community-yamls", {}) or {}
    lines = [
        "<!-- AUTO-STATE:BEGIN -->",
        "> ⚙️ **本节由 `tools/docs_watch.py` 每日自动重写，请勿手工编辑。**",
        "> 采集时间：%s（UTC）" % state["generated_at"],
        "",
        "| 上游 | 当前值 | 日期 | 上次变化 |",
        "|---|---|---|---|",
        "| 最新正式版 | `%s` | %s | %s |" % (
            rel.get("tag", "—"), rel.get("published", "—"), _changed_at(f, "release")),
        "| Alpha HEAD | `%s` | %s | %s |" % (
            alpha.get("sha", "—"), alpha.get("date", "—"), _changed_at(f, "alpha")),
        "| 正式版 → Alpha 领先 | %s 条提交 | — | %s |" % (
            _val(f, "alpha-ahead"), _changed_at(f, "alpha-ahead")),
        "| 官方默认配置 `docs/config.yaml` | sha256 `%s…`（%s 字节） | — | %s |" % (
            cfg.get("sha256", "—"), cfg.get("size", "—"), _changed_at(f, "config-yaml")),
        "| wiki 源仓库 MetaCubeX/Meta-Docs | `%s` | %s | %s |" % (
            docs.get("sha", "—"), docs.get("date", "—"), _changed_at(f, "metadocs")),
        "| 官网 wiki sitemap | %s 个 URL | lastmod %s | %s |" % (
            wiki.get("urls", "—"), wiki.get("lastmod", "—"), _changed_at(f, "wiki")),
        "| 社区合集 HenryChiao/MIHOMO_YAMLS | `%s` | %s | %s |" % (
            yamls.get("sha", "—"), yamls.get("date", "—"), _changed_at(f, "community-yamls")),
        "",
        "> 判据提醒：**Alpha 有提交 ≠ 需要追 Alpha**。当前正式版与 Alpha 的差异多为",
        "> bugfix，不涉配置面；真正要盯的是上表里 `docs/config.yaml` 的哈希 ——",
        "> 字段增删改一定会落在那个文件上。",
        "<!-- AUTO-STATE:END -->",
    ]
    return "\n".join(lines)


def _changed_at(facts: dict, key: str) -> str:
    entry = facts.get(key)
    return entry.get("changed_at", "—") if entry else "—"


RENDERERS = {"surge": render_surge_block, "mihomo": render_mihomo_block}


# --------------------------------------------------------------------------- 更新日志
#
# 为什么单独成页、而不是塞进 readme 的 AUTO 区块：
#   readme 的 AUTO 区块记的是**当前状态**（现在是什么版本），
#   更新日志记的是**历史**（这几周发生了什么）。两者更新频率与用途都不同 ——
#   状态区块天天被重写，日志则是只增不改的流水。混在一起会让状态区块越来越长。
#
# 为什么"最近一周"常常是空的：
#   实测 Surge Mac 正式版约每月一发（6.8.0 → 6.9.0 → 6.9.1），
#   mihomo 正式版更是按月计（v1.19.28 → … → v1.19.31 跨约两个月）。
#   一周窗口内**很可能一个正式版都没有** —— 这是事实，如实写出来，
#   不能为了"每天都有内容"去硬凑。所以每页都额外给一个 30 天的上下文窗口。


def _fmt_notes(notes: str) -> list[str]:
    """把官方 Markdown 说明转成适度缩进的列表，保持可读。"""
    out: list[str] = []
    for raw in notes.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("#"):
            out.append("")
            out.append("**%s**" % line.lstrip("# ").strip())
        elif line.lstrip().startswith(("-", "*")):
            out.append("- " + line.lstrip().lstrip("-*").strip())
        else:
            out.append(line.strip())
    return out


def render_surge_changelog(log: dict) -> str:
    # 注意：这些列表挂在 log 顶层（不是 log["facts"]）——
    # facts 是"当前状态"、要参与变化比对；发布记录是"历史"，两者刻意分开。
    stable = log.get("stable") or []
    beta = log.get("beta") or []
    tg = log.get("tg") or []
    week = log.get("week_start")

    L = [
        "# Surge 更新日志（自动生成）",
        "",
        "> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**",
        "> 生成时间：%s（UTC） · 最近一周 = %s 起" % (log.get("generated_at", "—"), week),
        "",
        "数据来源：Surge Mac 的 **appcast 双通道**（官方更新日志页读的就是它）",
        "与 **Telegram @SurgeTestFlightFeed**。",
        "iOS 版本来自 **App Store**。",
        "",
        "---",
        "",
        "## 一、最近一周（%s 起）" % week,
        "",
    ]

    recent_stable = [r for r in stable if (r.get("date") or "") >= week]
    recent_beta = [r for r in beta if (r.get("date") or "") >= week]
    recent_tg = [p for p in tg if (p.get("date") or "") >= week]

    if not recent_stable and not recent_beta and not recent_tg:
        L += [
            "**本周两个通道都没有新发布。**",
            "",
            "这不是漏抓 —— Surge Mac 正式版大约**按月**发布（6.8.0 → 6.9.0 → 6.9.1），",
            "Beta 也不保证每周都有。下方给出更长时间的上下文。",
            "",
        ]

    if recent_stable:
        L += ["### 正式版（稳定通道）", ""]
        for r in recent_stable:
            L += ["#### `%s`（build %s） · %s" % (r.get("version"), r.get("build"), r.get("date")), ""]
            L += _fmt_notes(r.get("notes", "")) + [""]
    elif stable:
        # 本周没发正式版时，把最近一次的说明列出来 ——
        # 日志的意义是"最近改了什么"，不是"这七天有没有发版"。
        latest = stable[0]
        L += ["### 正式版（本周无新版本，最近一次如下）", "",
              "#### `%s`（build %s） · %s" % (latest.get("version"), latest.get("build"), latest.get("date")), ""]
        L += _fmt_notes(latest.get("notes", "")) + [""]

    if recent_beta:
        L += ["### 测试版（Beta 通道）", ""]
        for r in recent_beta:
            L += ["#### `%s`（build %s） · %s" % (r.get("version"), r.get("build"), r.get("date")), ""]
            L += _fmt_notes(r.get("notes", "")) + [""]

    if recent_tg:
        L += ["### 官方公告（Telegram）", ""]
        for p in recent_tg:
            L += ["**#%s · %s**" % (p.get("id"), p.get("date")), ""]
            L += _fmt_notes(p.get("text", "")) + [""]

    L += [
        "---",
        "",
        "## 二、最近 30 天上下文",
        "",
        "| 通道 | 版本 | build | 日期 |",
        "|---|---|---:|---|",
    ]
    for r in stable[:6]:
        L.append("| 正式版 | `%s` | %s | %s |" % (r.get("version"), r.get("build"), r.get("date")))
    for r in beta[:6]:
        L.append("| Beta | `%s` | %s | %s |" % (r.get("version"), r.get("build"), r.get("date")))
    L += ["", "> 同一版本的多个 beta build 在 appcast 里会**原地被覆盖**（只剩最后一条），",
          "> 所以 build 级的中间过程要看上一节的 Telegram 公告。", ""]
    return "\n".join(L)


def render_mihomo_changelog(log: dict) -> str:
    # 同 surge：发布记录挂在顶层，不进 facts。
    releases = log.get("releases") or []
    alpha = log.get("alpha") or []
    week = log.get("week_start")

    L = [
        "# Mihomo 更新日志（自动生成）",
        "",
        "> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**",
        "> 生成时间：%s（UTC） · 最近一周 = %s 起" % (log.get("generated_at", "—"), week),
        "",
        "数据来源：GitHub Release（正式版，含官方 release note）",
        "与 **Alpha 分支提交历史**（测试版）。",
        "",
        "> mihomo **没有** Surge 那样的 Beta 发布公告通道：它的「测试版」就是",
        "> Alpha 分支，变更记录即提交历史。",
        "",
        "---",
        "",
        "## 一、最近一周（%s 起）" % week,
        "",
    ]

    recent_rel = [r for r in releases if (r.get("date") or "") >= week]
    recent_alpha = [c for c in alpha if (c.get("date") or "") >= week]

    if not recent_rel:
        L += [
            "**本周没有新的正式版。**",
            "",
            "mihomo 的正式版是**按月**发的（`v1.19.28` → … → `v1.19.31` 跨度约两个月），",
            "一周窗口内没有正式版是常态，不是漏抓。",
            "",
        ]
        # 本周没有新正式版时，把**最近那个**的说明照样列出来 ——
        # 日志的价值在于"最近这次更新改了什么"，而不是"这七天有没有发版"。
        if releases:
            latest = releases[0]
            L += ["#### 最近一次正式版：`%s` · %s" % (latest.get("tag"), latest.get("date")), ""]
            L += _fmt_notes(latest.get("body", "")) + [""]
    else:
        L += ["### 正式版", ""]
        for r in recent_rel:
            L += ["#### `%s` · %s" % (r.get("tag"), r.get("date")), ""]
            L += _fmt_notes(r.get("body", "")) + [""]

    L += ["### Alpha 分支（测试版）", ""]
    if not recent_alpha:
        L += ["本周 Alpha 也没有新提交。", ""]
    else:
        L += ["本周 **%d 条**提交：" % len(recent_alpha), "",
              "| 日期 | 提交 | 说明 |", "|---|---|---|"]
        for c in recent_alpha:
            msg = (c.get("message") or "").replace("|", "\\|")
            L.append("| %s | `%s` | %s |" % (c.get("date"), c.get("sha"), msg))
        L += ["",
              "> ⚠️ **Alpha 有提交 ≠ 需要追 Alpha。** 多数是 bugfix，不涉配置面。",
              "> 只有配置面（官方 `docs/config.yaml`）发生变化时才需要动文档。", ""]

    L += [
        "---",
        "",
        "## 二、正式版历史",
        "",
        "| 版本 | 日期 |",
        "|---|---|",
    ]
    for r in releases[:8]:
        L.append("| `%s` | %s |" % (r.get("tag"), r.get("date")))
    L += ["", "> 完整 release note 见 [GitHub Releases](https://github.com/MetaCubeX/mihomo/releases)。", ""]
    return "\n".join(L)


CHANGELOG_RENDERERS = {"surge": render_surge_changelog, "mihomo": render_mihomo_changelog}


def changelog_marker(target: str, log: dict) -> str:
    """更新日志的「内容版本号」—— 只在它变化时才重写文件。

    为什么不靠日期窗口判断：窗口会随日子自然滑动（今天在窗内的条目，
    明天可能掉出去），照此重写就是每天都在刷内容几乎相同的文件。
    改用「最新发布 / 最新提交」当判据，则**只有真有新东西时才落盘**。
    """
    if target == "surge":
        stable = (log.get("stable") or [{}])[0]
        beta = (log.get("beta") or [{}])[0]
        tg = (log.get("tg") or [{}])[0]
        return "%s/%s|%s/%s|tg%s" % (
            stable.get("version"), stable.get("build"),
            beta.get("version"), beta.get("build"), tg.get("id"))
    rel = (log.get("releases") or [{}])[0]
    alpha = (log.get("alpha") or [{}])[0]
    return "%s|%s" % (rel.get("tag"), alpha.get("sha"))


def write_changelog(docs_dir: str, target: str, log: dict, dry_run: bool) -> str:
    path = os.path.join(docs_dir, "changelog.md")
    # ⚠️ 抓取失败时**绝不覆盖**已有日志。
    # GitHub API 一旦限流，发布列表会返回空 —— 照写就把整页清成空表，
    # 而"空"与"确实没有发布"从数据上分辨不出来。宁可保留上一次的日志。
    if target == "mihomo":
        if not log.get("releases") and not log.get("alpha") and os.path.exists(path):
            return "跳过（本轮没抓到发布数据，保留原文件）"
    else:
        if not log.get("stable") and not log.get("beta") and os.path.exists(path):
            return "跳过（本轮没抓到发布数据，保留原文件）"
    # ⚠️ 只在**确有新发布 / 新提交**（或文件尚不存在）时重写。
    # 否则"最近一周"这个窗口每天自然滑动，会变成每天一次内容几乎相同的提交。
    marker = changelog_marker(target, log)
    if log.get("last_marker") == marker and os.path.exists(path):
        return "未变化（无新发布）"
    text = CHANGELOG_RENDERERS[target](log)
    old = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old == text:
        return "未变化"
    if not dry_run:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return "已更新"


def update_readme_block(docs_dir: str, block: str, dry_run: bool) -> str:
    """把 AUTO 区块替换进 readme.md；markers 缺失时**只警告、不报错**。

    故意不自动新建 readme —— 骨架里的正文（导航、约束、示例）是手写的，
    自动生成物只该占其中一个可替换的区块。
    """
    path = os.path.join(docs_dir, "readme.md")
    if not os.path.exists(path):
        return "跳过（readme.md 不存在）"
    with open(path, encoding="utf-8") as f:
        text = f.read()
    begin, end = "<!-- AUTO-STATE:BEGIN -->", "<!-- AUTO-STATE:END -->"
    if begin not in text or end not in text:
        return "跳过（未找到 AUTO-STATE 标记）"
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    new_text = head + block + tail
    if new_text == text:
        return "未变化"
    if not dry_run:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
    return "已更新"


def process(target: str, dry_run: bool, fail_on_change: bool) -> bool:
    docs_dir = TARGETS[target]
    state_path = os.path.join(docs_dir, "upstream.json")

    log("══ %s ══" % target)
    facts, pages, changelog = (surge_collect if target == "surge" else mihomo_collect)()
    if not facts:
        log("  ⚠️  本轮没有采集到任何数据（网络问题？），保持原状态不动")
        return False

    old: dict = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:                                    # noqa: BLE001
            old = {}

    state = merge_state(old, facts, pages)
    msgs = diff_facts(old, state)
    page_changes = changed_pages(old, state)

    for key, entry in sorted(state["facts"].items()):
        log("  · %-22s %s" % (key, json.dumps(entry["value"], ensure_ascii=False)))

    first_run = not old
    if first_run:
        log("  ℹ️  首次运行，已建立基线（本次不计为「变化」）")
    elif msgs or page_changes:
        log("  ⚠️  检测到上游变化：")
        for m in msgs:
            log("      %s" % m)
        for p in page_changes[:20]:
            log("      页面内容变化：%s" % p)
        if len(page_changes) > 20:
            log("      …（另有 %d 页）" % (len(page_changes) - 20))
        log("      → 请读发布说明 / diff，确认是否触及配置面，再更新正文。")
    else:
        log("  ✓ 与上次记录一致，无需更新文档")

    if not dry_run:
        os.makedirs(docs_dir, exist_ok=True)
        with open(state_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    log("  state: %s" % ("（未写入，dry-run）" if dry_run else os.path.relpath(state_path, ROOT)))
    log("  readme: %s" % update_readme_block(docs_dir, RENDERERS[target](state), dry_run))
    changelog["week_start"] = week_start()
    changelog["generated_at"] = state["generated_at"]
    changelog["last_marker"] = old.get("changelog_marker")
    log("  changelog: %s" % write_changelog(docs_dir, target, changelog, dry_run))
    log("")

    # 记下更新日志的内容版本，供下次判断"要不要重写这一页"。
    if not dry_run:
        state["changelog_marker"] = changelog_marker(target, changelog)
        with open(state_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")

    return bool((msgs or page_changes) and not first_run)


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    fail_on_change = "--fail-on-change" in args

    target = "all"
    if "--target" in args:
        i = args.index("--target")
        if i + 1 < len(args):
            target = args[i + 1]
    if target not in ("all", "surge", "mihomo"):
        log("用法：docs_watch.py [--target surge|mihomo|all] [--dry-run] [--fail-on-change]")
        return 2

    changed = False
    for name in ("surge", "mihomo"):
        if target in ("all", name):
            changed = process(name, dry_run, fail_on_change) or changed

    return 1 if (changed and fail_on_change) else 0


if __name__ == "__main__":
    sys.exit(main())
