# Mihomo 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 最近更新：2026-10-03T23:52:58Z（UTC）

数据来源：GitHub Release（正式版，含官方 release note）
与 **Alpha 分支提交历史**（测试版）。

> mihomo **没有** Surge 那样的 Beta 发布公告通道：它的「测试版」就是
> Alpha 分支，变更记录即提交历史。

---

## 一、最近 7 天

### 正式版

#### `v1.19.32` · 2026-09-30


**本版变更**
- 新功能：load-balance 新增 `hash-key`，可按入站认证用户名为会话稳定选择节点（#3133）

**缺陷与修复**
- 修复：Linux 上从 auxv 填充 HWCap
- 修复：计算有效 MSS 时计入 TCP 选项
- 修复：anytls 出站空闲会话清理中的竞态（c.idleSession.Len()）
- 修复：mipstack 下未连接 UDP 与原始 IP 的 ICMP 错误与 Linux 行为对齐
- 修复：TUN 入站监听器默认改用 MIPS 网络栈（#3264）
- 修复：OpenVPN 的 P_DATA_V1 AEAD 附加认证数据（AAD）不再包含 opcode（#3237）
- 修复：sing-mux 的半关闭
- 修复：HTTP/2 ClientConn 建立过程中，上下文 ctx 被取消时触发 pconn 空指针访问
- 修复：mieru 入站未设置 UDP 的 InUser 元数据
- 修复：EasyTier 出站在 overlay 静默失败后自动重启

**维护性改动**
- 维护：mipstack 支持接收方向（RX）的校验和卸载
- 维护：convert 功能支持 xhttp 的 `extra.headers`
- 维护：默认 IP 网络栈模式改为 MIPS，并为 TUN 新增 `congestion-controller`（拥塞控制算法）选项
- 维护：mipstack 与 gvisor 支持惰性接收缓冲读取
- 维护：更新 mieru 版本（#3242）

### Alpha 分支（测试版）

本周 **8 条**提交：

| 日期 | 提交 | 说明 |
|---|---|---|
| 2026-10-02 | `9f053c4` | 维护：wireguard 设备与协议栈改为延迟初始化 |
| 2026-09-30 | `88dcbf7` | 修复：TUN 入站监听器默认改用 MIPS 网络栈（#3264） |
| 2026-09-30 | `ac65297` | 修复：HTTP/2 ClientConn 建立过程中，上下文 ctx 被取消时触发 pconn 空指针访问 |
| 2026-09-30 | `409ee57` | 修复：Linux 上从 auxv 填充 HWCap |
| 2026-09-30 | `8fa048d` | 修复：sing-mux 的半关闭 |
| 2026-09-30 | `1341769` | 维护：mipstack 支持接收方向（RX）的校验和卸载 |
| 2026-09-29 | `60f70ce` | 修复：mipstack 下未连接 UDP 与原始 IP 的 ICMP 错误与 Linux 行为对齐 |
| 2026-09-27 | `63bd52e` | 维护：默认 IP 网络栈模式改为 MIPS，并为 TUN 新增 `congestion-controller`（拥塞控制算法）选项 |

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

**当前没有待译条目 —— 最近一周的全部发布说明均已译为中文。**
