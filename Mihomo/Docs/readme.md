# Mihomo 知识库 · laincat/Rules

> mihomo（原 Clash Meta）的配置、规则、Providers、Geodata 与运维参考。
>
> **本知识库只讲 mihomo，不掺 Surge。** 两者在规则语法、策略模型、外部集合
> 格式上没有一一对应的关系 —— mihomo 的 `behavior`、`format` 在 Surge 里
> **根本不存在**，套用只会写出静默失效的配置。Surge 请看
> [`../../Surge/Docs/readme.md`](../../Surge/Docs/readme.md)。

---

## 一、文档导航

| 章节 | 内容 | 适合谁 |
|---|---|---|
| [01-basics.md](01-basics.md) | 配置骨架、全局字段、TUN、实验性配置 | 刚上手 |
| [02-dns.md](02-dns.md) | DNS 子系统（`enhanced-mode`、`nameserver`、`fake-ip`、`nameserver-policy`） | 排查解析 |
| [03-providers.md](03-providers.md) | **`proxy-providers` / `rule-providers` 与 `behavior` 三态** | 引用本仓库规则集 |
| [04-rules.md](04-rules.md) | 规则类型、`GEOIP` / `GEOSITE`、`RULE-SET`、`SUB-RULE`、逻辑规则 | 写规则 |
| [05-geodata.md](05-geodata.md) | `geox-url`、`.mrs` / `.dat` / `.mmdb` 的取舍 | 配地理库 |
| [06-policy-groups.md](06-policy-groups.md) | 策略组类型、`filter` / `exclude-filter`、`use` / providers | 配策略组 |
| [07-operations.md](07-operations.md) | RESTful API、排错、性能 | 运维排错 |

---

## 二、本仓库的 Mihomo 产物

外链前缀：

```
https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/
```

| 目录 | 内容 |
|---|---|
| `Mihomo/Advertising/` | 去广告规则集（`Comic.yaml`） |
| `Mihomo/Ruleset/` | 常规规则集（`Special.yaml`、`Ozon.yaml`、`Comics.yaml` 等） |

**本仓库的 Rule Provider 文件是 `classical` 格式**（payload 里是完整规则行，
如 `DOMAIN-SUFFIX,steamserver.net`）。引用时必须写 `behavior: classical`：

```yaml
rule-providers:
  special:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/Special.yaml"
    path: ./ruleset/Special.yaml
    interval: 43200
  comic:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Comic.yaml"
    path: ./ruleset/Comic.yaml
    interval: 43200

rules:
  - RULE-SET,special,Proxy
  - RULE-SET,comic,REJECT
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,Proxy
```

> ⚠️ **`behavior` 填错不会报错，而是规则静默全部失效。**
> 本仓库文件是完整规则行 → 必须是 `classical`，写成 `domain` 会一条都不命中。
> 详见 [03-providers.md](03-providers.md)。

---

## 三、四个最容易静默失效的点

| 约束 | 后果 |
|---|---|
| **`behavior` 必须与 payload 语法一致** | 不一致 → 规则**静默全部失效**（不报错） |
| **`no-resolve` 写在 `rules:` 的引用行上** | 写进 provider 内无效 |
| **provider 拉取失败 = 空集合 = 全部放行** | 容易误判为「规则没生效」 |
| **`GEOIP` / `GEOSITE` 依赖 geodata** | 未配置 `geox-url` 或本地库时全部不命中 |

> 与 Surge 的根本差异：mihomo 的 `RULE-SET` 需要 provider 声明来描述
> **payload 的语法**（`behavior`），而 Surge 是由引用关键字
> （`RULE-SET` / `DOMAIN-SET`）决定的。两者不能互相套用。

---

## 四、上游状态（自动维护）

<!-- AUTO-STATE:BEGIN -->
> ⚙️ **本节由 `tools/docs_watch.py` 每日自动重写，请勿手工编辑。**
> 采集时间：2026-09-22T08:48:54Z（UTC）

| 上游 | 当前值 | 日期 | 上次变化 |
|---|---|---|---|
| 最新正式版 | `v1.19.31` | 2026-09-14 | 2026-09-22T08:37:52Z |
| Alpha HEAD | `5019cc0` | 2026-09-19 | 2026-09-22T08:37:52Z |
| 正式版 → Alpha 领先 | 2 条提交 | — | 2026-09-22T08:37:52Z |
| 官方默认配置 `docs/config.yaml` | sha256 `47f28f65758fdd15…`（141835 字节） | — | 2026-09-22T08:37:52Z |
| wiki 源仓库 MetaCubeX/Meta-Docs | `517f4c2` | 2026-09-14 | 2026-09-22T08:37:52Z |
| 官网 wiki sitemap | 285 个 URL | lastmod 2026-09-14 | 2026-09-22T08:37:52Z |
| 社区合集 HenryChiao/MIHOMO_YAMLS | `2cdfc8f` | 2026-09-21 | 2026-09-22T08:37:52Z |

> 判据提醒：**Alpha 有提交 ≠ 需要追 Alpha**。当前正式版与 Alpha 的差异多为
> bugfix，不涉配置面；真正要盯的是上表里 `docs/config.yaml` 的哈希 ——
> 字段增删改一定会落在那个文件上。
<!-- AUTO-STATE:END -->

---

## 五、版本体系怎么读

mihomo 有两条线：

| 线 | 说明 |
|---|---|
| **正式版** | 有 tag（如 `v1.19.31`）、可回退。**日常用这个** |
| **Alpha 分支** | 持续开发，正式版是它的定期合入 |

> **Alpha 有提交 ≠ 需要追 Alpha。** 多数增量是 bugfix，不涉及配置面。
> 判断依据是「正式版到 Alpha 领先几条、分别是什么」——
> 这组数字由第四节自动维护。
>
> 配置面的权威清单是官方默认配置
> [`docs/config.yaml`](https://github.com/MetaCubeX/mihomo/raw/refs/heads/Alpha/docs/config.yaml)
> —— 字段的增删改一定会落在那个文件上，盯它的哈希比翻 wiki 可靠。
