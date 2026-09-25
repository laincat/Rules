# Surge 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 最近更新：2026-09-25T23:57:54Z（UTC）

数据来源：Surge Mac 的 **appcast 双通道**（官方更新日志页读的就是它）
与 **Telegram @SurgeTestFlightFeed**。
iOS 版本来自 **App Store**。

---

## 一、最近 7 天

### 正式版（本周无新版本，最近一次如下）

#### `6.9.1`（build 12290） · 2026-09-09


**改进**
- macOS 的逻辑规则编辑器现在支持给使用 reject 策略的 AND / OR / NOT 规则配置 Pre-Matching，并会在保存前指出不受支持的子规则。
- `GEOIP` 与 `IP-ASN` 规则新增 `UNKNOWN` 取值，用于匹配在国家 / ASN 数据库里查不到对应记录的目标 IP。单条规则与规则集都支持。

**修复**
- 修复：经由代理与隧道（含 WireGuard、Tailscale）的 UDP 连接缺失流量统计。
- 修复：极少数情况下，UDP 代理连接在收包期间关闭会拖住 Surge 处理的其它流量。
- 修复：macOS 26 上深色模式菜单文字不可读；并改善了系统外观切换时菜单栏图标的配色。
- 修复：已启用的功能并不需要 Surge Helper 时，启动仍弹出安装 / 升级提示。
- 修复：当服务端的 HTTP/3 Datagram 协商干扰 UDP 转发时，Hysteria 的 UDP 流量失败。
- 修复：macOS 上 Smart 策略组的右键菜单显示了过期的使用情况或错误的优先级调整。

### 测试版（Beta 通道）

#### `6.10.0`（build 12380） · 2026-09-25


**改进**
- 策略组新增 `category` 参数，用于分组展示。策略组很多时可用。
- 所有 `test-url` 参数现在都支持配置 HTTPS 地址。测试结果仍按单次 HTTP RTT 的延迟计，但由于要完成 TLS 握手，策略数量多时测试耗时可能明显增加。
- 上一版为加强 MITM 安全性，为每个不同域名各生成一对密钥。这导致同时对大量不同域名做 MITM 时出现明显延迟。经评估后**该项改动已回退**。
- 针对 macOS 27.2 beta 的系统 bug 加了规避措施，避免 Dashboard 崩溃。
- 改进：对没有互联网出口的点对点 Tailscale / WireGuard 策略，UDP 测试改为直接报告不支持，而不再干等到超时。
- 修复：逻辑规则无法正确解析含括号的策略名。
- 同名内联规则集现在会在主配置与模块之间**合并**，而不再互相覆盖 —— 每个来源贡献的规则都会保留。

### 官方公告（Telegram）

**#414 · 2026-09-25**

A new guide has been added to the Surge Knowledge Base, covering how to remotely manage a Surge instance.
https://kb.nssurge.com/surge-knowledge-base/guidelines/remote-management

---

## 二、最近 30 天上下文

| 通道 | 版本 | build | 日期 |
|---|---|---:|---|
| 正式版 | `6.9.1` | 12290 | 2026-09-09 |
| 正式版 | `6.9.0` | 12250 | 2026-08-31 |
| 正式版 | `6.8.1` | 12030 | 2026-08-10 |
| 正式版 | `6.8.0` | 11990 | 2026-08-06 |
| 正式版 | `6.7.0` | 11730 | 2026-07-15 |
| 正式版 | `6.6.0` | 11270 | 2026-06-01 |
| Beta | `6.10.0` | 12380 | 2026-09-25 |
| Beta | `6.9.1` | 12290 | 2026-09-09 |
| Beta | `6.9.0` | 12250 | 2026-08-31 |
| Beta | `6.8.1` | 12030 | 2026-08-10 |
| Beta | `6.8.0` | 11990 | 2026-08-06 |
| Beta | `6.7.0` | 11730 | 2026-07-15 |

> 同一版本的多个 beta build 在 appcast 里会**原地被覆盖**（只剩最后一条），
> 所以 build 级的中间过程要看上一节的 Telegram 公告。

---

## 关于中文翻译

本页的发布说明由英文原文**人工对照翻译**，译文维护在
[`translations.json`](translations.json)。

为什么不用机器翻译：发布说明里全是专有名词（`pre-matching`、`rule-provider`、`behavior: classical`…），机器翻译会把它们译坏，反而误导。所以采用对照表 —— **译过的按中文显示，没译过的原样保留英文**，绝不自动生成。

想补译：在 `translations.json` 的 `entries` 里加一条 `{"en": "<英文原文>", "zh": "<中文>"}` 即可，英文原文可从下方待译清单复制（不必包含 commit sha 与 `by @作者`，脚本会先做归一化）。

**当前待译 2 条：**

- `A new guide has been added to the Surge Knowledge Base, covering how to remotely manage a Surge instance.`
- `https://kb.nssurge.com/surge-knowledge-base/guidelines/remote-management`
