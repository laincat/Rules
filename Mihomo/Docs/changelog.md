# Mihomo 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 最近更新：2026-10-02T00:52:55Z（UTC）

数据来源：GitHub Release（正式版，含官方 release note）
与 **Alpha 分支提交历史**（测试版）。

> mihomo **没有** Surge 那样的 Beta 发布公告通道：它的「测试版」就是
> Alpha 分支，变更记录即提交历史。

---

## 一、最近 7 天

### 正式版

#### `v1.19.32` · 2026-09-30


**本版变更**
- 3025efad feat: add load-balance hash-key to pin a session on the inbound user (#3133) by @简直蠢丶

**缺陷与修复**
- 409ee57e fix: populate HWCap from auxv on linux by @artbred
- 41b8a059 fix: account for TCP options in effective MSS by @wwqgtxx
- 修复：anytls 出站空闲会话清理中的竞态（c.idleSession.Len()）
- 60f70cec fix: align unconnected UDP and raw IP ICMP errors with Linux for mipstack by @wwqgtxx
- 88dcbf7f fix: default listener tun to mips stack (#3264) by @Jiawen Geng
- 8d57a8c5 fix: exclude opcode from P_DATA_V1 AEAD additional data for OpenVPN (#3237) by @FlyingSB
- 8fa048d3 fix: half-close in sing-mux by @proxi
- ac652970 fix: nil pconn deref when ctx is canceled during h2 ClientConn setup by @BESTRUI
- 修复：mieru 入站未设置 UDP 的 InUser 元数据
- 修复：EasyTier 出站在 overlay 静默失败后自动重启

**维护性改动**
- 13417699 chore: support RX checksum offload for mipstack by @wwqgtxx
- 维护：convert 功能支持 xhttp 的 `extra.headers`
- 63bd52ec chore: change default IP stack mode to mips and support `congestion-controller` option for tun by @wwqgtxx
- 维护：mipstack 与 gvisor 支持惰性接收缓冲读取
- f103639c chore: update mieru version (#3242) by @enfein

### Alpha 分支（测试版）

本周 **8 条**提交：

| 日期 | 提交 | 说明 |
|---|---|---|
| 2026-09-30 | `88dcbf7` | fix: default listener tun to mips stack (#3264) |
| 2026-09-30 | `ac65297` | fix: nil pconn deref when ctx is canceled during h2 ClientConn setup |
| 2026-09-30 | `409ee57` | fix: populate HWCap from auxv on linux |
| 2026-09-30 | `8fa048d` | fix: half-close in sing-mux |
| 2026-09-30 | `1341769` | chore: support RX checksum offload for mipstack |
| 2026-09-29 | `60f70ce` | fix: align unconnected UDP and raw IP ICMP errors with Linux for mipstack |
| 2026-09-27 | `63bd52e` | chore: change default IP stack mode to mips and support `congestion-controller` option for tun |
| 2026-09-25 | `f103639` | chore: update mieru version (#3242) |

> ⚠️ **Alpha 有提交 ≠ 需要追 Alpha。** 多数是 bugfix，不涉配置面。
> 只有配置面（官方 `docs/config.yaml`）发生变化时才需要动文档。

---

## 二、正式版历史

| 版本 | 日期 |
|---|---|
| `v1.19.32` | 2026-09-30 |
| `v1.19.31` | 2026-09-14 |
| `v1.19.30` | 2026-08-16 |
| `v1.19.29` | 2026-07-18 |
| `v1.19.28` | 2026-07-08 |
| `v1.19.27` | 2026-06-06 |
| `v1.19.26` | 2026-05-31 |

> 完整 release note 见 [GitHub Releases](https://github.com/MetaCubeX/mihomo/releases)。

---

## 关于中文翻译

本页的发布说明由英文原文**人工对照翻译**，译文维护在
[`translations.json`](translations.json)。

为什么不用机器翻译：发布说明里全是专有名词（`pre-matching`、`rule-provider`、`behavior: classical`…），机器翻译会把它们译坏，反而误导。所以采用对照表 —— **译过的按中文显示，没译过的原样保留英文**，绝不自动生成。

想补译：在 `translations.json` 的 `entries` 里加一条 `{"en": "<英文原文>", "zh": "<中文>"}` 即可，英文原文可从下方待译清单复制（不必包含 commit sha 与 `by @作者`，脚本会先做归一化）。

**当前待译 11 条：**

- `chore: change default IP stack mode to mips and support `congestion-controller` option for tun`
- `chore: support RX checksum offload for mipstack`
- `chore: update mieru version (#3242)`
- `feat: add load-balance hash-key to pin a session on the inbound user (#3133)`
- `fix: account for TCP options in effective MSS`
- `fix: align unconnected UDP and raw IP ICMP errors with Linux for mipstack`
- `fix: default listener tun to mips stack (#3264)`
- `fix: exclude opcode from P_DATA_V1 AEAD additional data for OpenVPN (#3237)`
- `fix: half-close in sing-mux`
- `fix: nil pconn deref when ctx is canceled during h2 ClientConn setup`
- `fix: populate HWCap from auxv on linux`
