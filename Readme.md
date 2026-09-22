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
