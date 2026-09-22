# Laincat-Rules

自用 Rules —— Surge 与 Mihomo 两套配置，各自独立，互不混用。

```
Surge/      Surge 规则集、模块与知识库（Docs/）
Mihomo/     Mihomo 规则集与知识库（Docs/）
```

| 目录 | 面向 | 知识库入口 |
|---|---|---|
| [`Surge/`](Surge/Readme.md) | Surge Mac / iOS / tvOS | [`Surge/Docs/readme.md`](Surge/Docs/readme.md) |
| [`Mihomo/`](Mihomo/Readme.md) | mihomo（原 Clash Meta） | [`Mihomo/Docs/readme.md`](Mihomo/Docs/readme.md) |

> **两套知识库彼此独立。** Surge 与 Mihomo 在规则语法、策略模型、外部集合格式上
> 没有一一对应的关系，写在一起只会互相误导 —— 各自看各自的 `Docs/`。

## 知识库的维护方式

`Surge/Docs/` 与 `Mihomo/Docs/` 记录的是**上游的版本与配置面状态**，靠两件事保持不腐烂：

1. `tools/docs_watch.py` 每日采集上游事实（版本号 / build / 提交 / 页面清单 / 内容哈希），
   写进各自的 `upstream.json`，并重写 readme 里标记为 `AUTO-STATE` 的区块。
2. 检测到变化时自动开 issue 提醒 —— **「该怎么改文档」仍需人读发布说明后判断**，
   脚本只负责回答「上游变了没有」。

采集覆盖的上游：

| | Surge | Mihomo |
|---|---|---|
| 版本源 | appcast（Mac）+ App Store（iOS） | GitHub Release + Alpha 分支 |
| 文档源 | manual.nssurge.com、kb.nssurge.com | wiki.metacubex.one 及其源仓库 MetaCubeX/Meta-Docs |
| 配置源 | — | `docs/config.yaml`（Alpha 分支，官方默认配置） |
| 公告源 | Telegram @SurgeTestFlightFeed | 仓库提交历史 |

### 哪些源不能自动化

| 源 | 状态 | 原因 |
|---|---|---|
| `x.com/SurgeBeta` | ❌ 无法抓取 | 推文正文在客户端渲染，服务端返回的 HTML 里只有固定简介；官方 API 需付费且返回 **401** |
| `t.me/SurgeTestFlightFeed` | ⚠️ 可抓但不可靠 | 能拿到消息 ID 与正文，但 Beta **会静默发版**（appcast 更新而 TG 无公告），不能当版本判据 |
| `kb.nssurge.com` 的 iOS 更新日志 | ⚠️ 已滞后 | 实测停在 5.14.6，而 App Store 已是 5.22.1 —— iOS 版本一律以 App Store 为准 |

> 结论：**Surge 的版本完全靠 appcast + App Store 两条链路**，社媒只作人工参考。
> mihomo 侧无此问题 —— 版本与配置面都能从仓库直接读到。
