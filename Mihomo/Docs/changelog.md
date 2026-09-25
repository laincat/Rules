# Mihomo 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 最近更新：2026-09-25T23:57:57Z（UTC）

数据来源：GitHub Release（正式版，含官方 release note）
与 **Alpha 分支提交历史**（测试版）。

> mihomo **没有** Surge 那样的 Beta 发布公告通道：它的「测试版」就是
> Alpha 分支，变更记录即提交历史。

---

## 一、最近 7 天

**本周没有新的正式版。**

mihomo 的正式版是**按月**发的（`v1.19.28` → … → `v1.19.31` 跨度约两个月），
一周窗口内没有正式版是常态，不是漏抓。

#### 最近一次正式版：`v1.19.31` · 2026-09-14


**本版变更**
- 新功能：新增 EasyTier 出站（去中心化组网）
- 新功能：TUN 支持 `stack: mips`（mihomo 自研用户态 IP 栈）
- 新功能：ZeroTier 支持 `identity-secret`（身份内嵌、不落盘）

**缺陷与修复**
- 修复：恢复 Hysteria v1 的 UDP 处理
- 修复：doq 出错后未关闭连接
- 修复：mkcp 出站出错后未关闭连接
- 修复：tsnet 模式下上游是 tailnet 对端时，split-DNS 的 UDP 查询静默失败
- 修复：Snell 出站出错后未关闭连接
- 修复：服务端解密握手错误未被处理
- 修复：VLESS 解密清理时的 panic
- 修复：AmneziaWG v3 的 RandomPaddingAddition 与 DisableCookies
- 修复：DomainSet 通配规则重叠时的匹配错误
- 修复：连接关闭时 Hysteria2 的 UDP 会话未关闭
- 修复：xhttp 的 IPv6 地址解析错误
- 修复：OpenVPN 的 tls-auth HMAC 摘要改为按 auth 推导，不再硬编码 SHA-1
- 修复：DomainSet 遍历（Foreach）往返过程中域名规则丢失
- 修复：kcptun 出错后未关闭连接
- 修复：sudoku 出站里 safeConnClose 的使用错误
- 修复：mieru 入站未遵守 `listen` 配置
- 修复：WireGuard 初始化时的空指针解引用
- 修复：更新器里 Android amd64 内核包名写错
- 修复：Tailscale 对上游 TCP DNS 服务器应始终使用 UserDial
- 修复：Shadowsocks none 缺少 NeedHandshake 标记
- 修复：handleContextListener 出错后未关闭连接
- 修复：mieru 服务端未关闭 UDP 端点
- 修复：TUIC 服务端出错后未关闭连接
- 修复：config.yaml 中的拼写错误
- 修复：TrustTunnel 客户端未等待 TCP 连接建立

**维护性改动**
- 维护：OpenVPN 不再依赖底层连接的 deadline 函数
- 维护：改善 mipstack 在设备背压下的表现
- 维护：非法的 Clash 风格域名规则现在会报详细错误
- 维护：YAML 库换为 go.yaml.in/yaml/v3
- 维护：DomainSet 中去除冗余的 select 计算
- 维护：对齐 mipstack 与 gvisor 的 API
- 维护：convert 功能支持 REALITY 的 ML-KEM 选项
- 维护：DumpMrs 中不再额外分配规则切片
- 维护：降低转换器的内存占用
- 维护：DomainSet 中去除冗余的 rank 计算
- 维护：Tailscale 升级到 v1.102.3
- 维护：sudoku 升级到 v0.5.0
- 维护：降低 gVisor 内存占用
- 维护：共享构建基准测试所用的合成数据集
- 维护：抽出独立的 DomainSetBuilder
- 维护：geodata 读取改用 16 KiB 缓冲
- 维护：新增基于 succinct DomainSet 的 DomainMap 实现
- 维护：降低 mipstack 的连接内存与 actor 栈开销
- 维护：DomainSet 构建期间复用队列
- 维护：因 API 调整而更新 mipstack
- 维护：为新 DomainMap 补充基准测试代码
- 维护：更新 mieru 版本

### Alpha 分支（测试版）

本周 **8 条**提交：

| 日期 | 提交 | 说明 |
|---|---|---|
| 2026-09-25 | `f103639` | chore: update mieru version (#3242) |
| 2026-09-24 | `8d57a8c` | fix: exclude opcode from P_DATA_V1 AEAD additional data for OpenVPN (#3237) |
| 2026-09-24 | `41b8a05` | fix: account for TCP options in effective MSS |
| 2026-09-24 | `3025efa` | feat: add load-balance hash-key to pin a session on the inbound user (#3133) |
| 2026-09-22 | `3c947c7` | 维护：convert 功能支持 xhttp 的 `extra.headers` |
| 2026-09-22 | `afe94da` | 修复：mieru 入站未设置 UDP 的 InUser 元数据 |
| 2026-09-22 | `91dd03a` | 维护：mipstack 与 gvisor 支持惰性接收缓冲读取 |
| 2026-09-19 | `5019cc0` | 修复：anytls 出站空闲会话清理中的竞态（c.idleSession.Len()） |

> ⚠️ **Alpha 有提交 ≠ 需要追 Alpha。** 多数是 bugfix，不涉配置面。
> 只有配置面（官方 `docs/config.yaml`）发生变化时才需要动文档。

---

## 二、正式版历史

| 版本 | 日期 |
|---|---|
| `v1.19.31` | 2026-09-14 |
| `v1.19.30` | 2026-08-16 |
| `v1.19.29` | 2026-07-18 |
| `v1.19.28` | 2026-07-08 |
| `v1.19.27` | 2026-06-06 |
| `v1.19.26` | 2026-05-31 |
| `v1.19.25` | 2026-05-16 |

> 完整 release note 见 [GitHub Releases](https://github.com/MetaCubeX/mihomo/releases)。

---

## 关于中文翻译

本页的发布说明由英文原文**人工对照翻译**，译文维护在
[`translations.json`](translations.json)。

为什么不用机器翻译：发布说明里全是专有名词（`pre-matching`、`rule-provider`、`behavior: classical`…），机器翻译会把它们译坏，反而误导。所以采用对照表 —— **译过的按中文显示，没译过的原样保留英文**，绝不自动生成。

想补译：在 `translations.json` 的 `entries` 里加一条 `{"en": "<英文原文>", "zh": "<中文>"}` 即可，英文原文可从下方待译清单复制（不必包含 commit sha 与 `by @作者`，脚本会先做归一化）。

**当前待译 4 条：**

- `chore: update mieru version (#3242)`
- `feat: add load-balance hash-key to pin a session on the inbound user (#3133)`
- `fix: account for TCP options in effective MSS`
- `fix: exclude opcode from P_DATA_V1 AEAD additional data for OpenVPN (#3237)`
