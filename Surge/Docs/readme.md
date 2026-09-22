# Surge 知识库 · laincat/Rules

> Surge 的配置、规则、策略、模块、脚本与运维参考。
>
> **本知识库只讲 Surge，不掺 mihomo。** 两者在规则语法、策略模型、外部集合
> 格式上没有一一对应关系，混在一页里只会互相误导 —— mihomo 请看
> [`../../Mihomo/Docs/readme.md`](../../Mihomo/Docs/readme.md)。

---

## 一、文档导航

| 章节 | 内容 | 适合谁 |
|---|---|---|
| [01-profile.md](01-profile.md) | Profile 结构、`[Section]` 一览、`#!include`、托管配置 | 刚上手写配置 |
| [02-rules.md](02-rules.md) | 规则求值顺序、规则类型、参数（`no-resolve` / `extended-matching` / `pre-matching`） | 写规则 |
| [03-ruleset.md](03-ruleset.md) | **`RULE-SET` vs `DOMAIN-SET` 的性能取舍**、外部集合写法 | 想让规则跑得快 |
| [04-dns-and-policy.md](04-dns-and-policy.md) | DNS、`[Host]`、Fake-IP、策略与策略组 | 排查解析 / 配策略 |
| [05-module-and-script.md](05-module-and-script.md) | Module（`.sgmodule`）、脚本类型与 `$done()` 契约 | 写模块 / 脚本 |
| [06-operations.md](06-operations.md) | 调试、HTTP API、常见错误对照、排错流程 | 运维排错 |
| [changelog.md](changelog.md) | **最近一周 + 30 天的正式版 / 测试版更新日志**（自动生成） | 想跟进版本 |

---

## 二、本仓库的 Surge 产物

外链前缀统一为：

```
https://raw.githubusercontent.com/laincat/Rules/main/Surge/
```

| 目录 | 内容 |
|---|---|
| `Surge/Advertising/` | 去广告：各上游的 `.sgmodule` 与 `Comics.list` |
| `Surge/Module/` | 功能性模块（Telegram、Ozon、下载分流、MITM 等） |
| `Surge/Ruleset/` | 常规规则集（`Japan.list`、`Special.list`、`Ozon.list` 等） |

订阅用 `.sgmodule` 直接指向 `raw.githubusercontent.com` 即可；
纯规则集（`.list`）用 `RULE-SET` 引用。

> ⚠️ 本仓库的 `.list` 是**完整规则行**（`DOMAIN-SUFFIX,xxx`）格式，属于 `RULE-SET`。
> **不是** `DOMAIN-SET` 要的「一行一个纯域名」格式 —— 引用方式写错不会报错，
> 而是规则静默失效。详见 [03-ruleset.md](03-ruleset.md)。

---

## 三、三条硬性约束（官方明确，违反会静默失效）

| 约束 | 说明 |
|---|---|
| **同一 URL / 文件不能同时用作 `RULE-SET` 和 `DOMAIN-SET`** | 一个配置里对同一地址只能用一种类型引用 |
| **`pre-matching` 仅限顶层规则，且策略必须是 REJECT 家族** | 不能用于代理 / `DIRECT`；不能写在子规则里 |
| **`[Rule]` 必须以一条已启用的 `FINAL` 结尾** | 否则配置不合法 |

> Surge **对未知参数一律静默忽略** —— 参数名写错不会报错，只是不生效。
> 所以"改了没反应"时，第一件事是核对该参数的**平台与最低版本**。

---

## 四、上游状态（自动维护）

<!-- AUTO-STATE:BEGIN -->
> ⚙️ **本节由 `tools/docs_watch.py` 每日自动重写，请勿手工编辑。**
> 采集时间：2026-09-22T23:37:31Z（UTC）

| 上游 | 版本 | Build | 条目 / 页数 | 上次变化 |
|---|---|---:|---:|---|
| Surge Mac 稳定版（appcast） | 6.9.1 | 12290 | 22 | 2026-09-22T08:37:49Z |
| Surge Mac Beta（appcast） | 6.10.0 | 12360 | 23 | 2026-09-22T23:37:31Z |
| Surge iOS 稳定版（App Store） | 5.22.1 | — | 发布于 2026-09-13 | 2026-09-22T08:37:49Z |
| 官方手册 manual.nssurge.com | — | — | 86 页 | 2026-09-22T08:37:49Z |
| 官方知识库 kb.nssurge.com | — | — | 中文 31 / 英文 31 页 | 2026-09-22T08:37:49Z |
| Telegram @SurgeTestFlightFeed | — | — | 最大消息 ID 413 | 2026-09-22T08:37:49Z |

内容指纹（任意页面正文被改写都会变）：手册 `009699542b22d248` · 知识库 `726351d96c0a0011`

> 判据提醒：**build 号变了 ≠ 配置面变了**。Beta 会静默发版（appcast 更新而
> TG 无公告），且存在「build 涨了但发布说明逐字未变」的重构建 —— 必须读
> 发布说明才能定论，所以本节只负责报告「变了」，不替你做结论。
>
> 版本来源**分平台**：Mac 走 appcast（有 build 号），iOS 走 App Store。
> 知识库的 `release-notes/surge-ios.md` 长期滞后（实测停在 5.14.6），
> 判断 iOS 最新版**不要**以它为准。
<!-- AUTO-STATE:END -->

---

## 五、版本标记怎么读

文中出现的版本标记：

| 标记 | 含义 |
|---|---|
| `iOS 5.14.0+` / `Mac 5.9.0+` | 该功能的**最低版本**；低于此版本的 Surge 会忽略该参数 |
| `Mac Only` / `iOS Only` | 仅该平台支持 |

> ⚠️ 版本来源**分平台，不要混用**：
> **Mac** 走 appcast（`nssurge.com/mac/latest/appcast-signed.xml`，带 build 号）；
> **iOS** 走 App Store。知识库里的 `release-notes/surge-ios.md` **长期滞后**
> （实测停在 5.14.6，而 App Store 已是 5.22.1），判断 iOS 最新版不要以它为准。
