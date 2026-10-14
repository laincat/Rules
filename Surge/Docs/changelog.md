# Surge 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 最近更新：2026-10-13T15:26:52Z（UTC）

数据来源：Surge Mac 的 **appcast 双通道**（官方更新日志页读的就是它）
与 **Telegram @SurgeTestFlightFeed**。
iOS 版本来自 **App Store**。

---

## 一、最近 7 天

### 正式版（稳定通道）

#### `6.10.0`（build 12500） · 2026-10-12


**VS Code 扩展**
新增对 VS Code 的 Surge Language Support 扩展的支持：为 profile、模块和规则集提供语法高亮与实时诊断；主 profile 打开时还会自动检测拆分配置，并校验其中的策略引用。
该扩展依赖本机的 Surge App 包做解析，要求 Surge Mac 6.10.0 或更高版本；Surge 升级后，扩展的 profile 解析能力会自动跟随更新。
https://marketplace.visualstudio.com/items?itemName=SurgeNetworks.surge-language-support

**IP Rewrite**
- 新增 `[IP Rewrite]` 配置段。它在 IP 层按目标地址处理进入 Surge VIF 的数据包，发生在到达任何规则或策略之前。可用动作：
- `reflect`：交换源地址与目标地址，把数据包发回发送方。
- `reject`：对连接尝试回 TCP RST；对其它数据包回 ICMP administratively prohibited，使发送方立即失败。
- `drop`：静默丢弃数据包。

**改进**
- 策略组新增 `category` 参数，用于分组展示。策略组很多时可用。
- 所有 `test-url` 参数现在都支持 HTTPS 测试地址。结果仍表示单次 HTTP 往返（RTT）的延迟；TLS 握手会增加测试总耗时，策略数量较多时尤为明显。
- 上一版为加强 MITM 安全性，为每个不同域名各生成一对密钥。这导致同时对大量不同域名做 MITM 时出现明显延迟。经评估后**该项改动已回退**。
- 改进：对没有互联网出口的点对点 Tailscale / WireGuard 策略，UDP 测试会直接报告不支持，避免一直等待至超时。
- 同名内联规则集现在会在主配置与模块之间**合并**，而不再互相覆盖 —— 每个来源贡献的规则都会保留。
- 优化：切换网络时 Tailscale 与 WireGuard 的行为。
- 新增一个选项，可主动更新已关联托管配置（linked profile）的配置。
- HTTP API 现已新增外部资源管理功能及其他一些辅助 API。

**修复**
- 修复：逻辑规则无法正确解析含括号的策略名。
- 针对 macOS 27.2 beta 的系统 bug 加了规避措施，避免 Dashboard 崩溃。

### 测试版（Beta 通道）

#### `6.11.0`（build 12510） · 2026-10-13


**自适应 QUIC 阻断**
- 为代理策略添加了 `block-quic=adaptive`。Surge 最初会阻止 QUIC，从而使应用程序回退到基于 TCP 的 HTTPS。如果应用程序未能在 1 秒内回退（例如仅支持 QUIC 的应用程序），则允许该主机使用 QUIC。结果会按主机缓存。此选项在 Mac 和 iOS 上的代理编辑器中也可用。
- `block-quic=auto` 现在对除 DIRECT 外的所有策略采用自适应模式，使仅支持 QUIC 的应用仍能通过代理工作。无法转发 UDP 的策略仍会阻断 QUIC。
- QUIC 主机名识别现在支持跨多个数据包的 TLS ClientHello；采用后量子密钥交换的新浏览器常见这种情况。同时支持 QUIC v2 和 draft-29。规则、MITM 与请求记录现在能识别更多 QUIC 连接的主机名。

**HTTP API**
- HTTP API 的 `GET /v1/policies` 现在接受 `include_external=true` 查询参数。响应中将包含一个额外的 `external-policies` 字段，用于列出从外部策略组 (`policy-path`) 加载的策略。每个条目都包含策略名称、所属策略组以及一个标识符。由于外部策略无法通过名称引用，因此请将此标识符作为 `$httpClient` 的 `policy` 选项传递，以便通过该策略发送请求。

#### `6.10.0`（build 12500） · 2026-10-12


**VS Code 扩展**
新增对 VS Code 的 Surge Language Support 扩展的支持：为 profile、模块和规则集提供语法高亮与实时诊断；主 profile 打开时还会自动检测拆分配置，并校验其中的策略引用。
该扩展依赖本机的 Surge App 包做解析，要求 Surge Mac 6.10.0 或更高版本；Surge 升级后，扩展的 profile 解析能力会自动跟随更新。
https://marketplace.visualstudio.com/items?itemName=SurgeNetworks.surge-language-support

**IP Rewrite**
- 新增 `[IP Rewrite]` 配置段。它在 IP 层按目标地址处理进入 Surge VIF 的数据包，发生在到达任何规则或策略之前。可用动作：
- `reflect`：交换源地址与目标地址，把数据包发回发送方。
- `reject`：对连接尝试回 TCP RST；对其它数据包回 ICMP administratively prohibited，使发送方立即失败。
- `drop`：静默丢弃数据包。

**改进**
- 策略组新增 `category` 参数，用于分组展示。策略组很多时可用。
- 所有 `test-url` 参数现在都支持 HTTPS 测试地址。结果仍表示单次 HTTP 往返（RTT）的延迟；TLS 握手会增加测试总耗时，策略数量较多时尤为明显。
- 上一版为加强 MITM 安全性，为每个不同域名各生成一对密钥。这导致同时对大量不同域名做 MITM 时出现明显延迟。经评估后**该项改动已回退**。
- 改进：对没有互联网出口的点对点 Tailscale / WireGuard 策略，UDP 测试会直接报告不支持，避免一直等待至超时。
- 同名内联规则集现在会在主配置与模块之间**合并**，而不再互相覆盖 —— 每个来源贡献的规则都会保留。
- 优化：切换网络时 Tailscale 与 WireGuard 的行为。
- 新增一个选项，可主动更新已关联托管配置（linked profile）的配置。
- HTTP API 现已新增外部资源管理功能及其他一些辅助 API。

**修复**
- 修复：逻辑规则无法正确解析含括号的策略名。
- 针对 macOS 27.2 beta 的系统 bug 加了规避措施，避免 Dashboard 崩溃。

### 官方公告（Telegram）

**[#418](https://t.me/SurgeTestFlightFeed/418) · 2026-10-13**


**Beta 更新**

**自适应 QUIC 阻断**
- 为代理策略添加了 `block-quic=adaptive`。Surge 最初会阻止 QUIC，从而使应用程序回退到基于 TCP 的 HTTPS。如果应用程序未能在 1 秒内回退（例如仅支持 QUIC 的应用程序），则允许该主机使用 QUIC。结果会按主机缓存。此选项在 Mac 和 iOS 上的代理编辑器中也可用。
- `block-quic=auto` 现在对除 DIRECT 外的所有策略采用自适应模式，使仅支持 QUIC 的应用仍能通过代理工作。无法转发 UDP 的策略仍会阻断 QUIC。
- QUIC 主机名识别现在支持跨多个数据包的 TLS ClientHello；采用后量子密钥交换的新浏览器常见这种情况。同时支持 QUIC v2 和 draft-29。规则、MITM 与请求记录现在能识别更多 QUIC 连接的主机名。

**HTTP API**
- HTTP API 的 `GET /v1/policies` 现在接受 `include_external=true` 查询参数。响应中将包含一个额外的 `external-policies` 字段，用于列出从外部策略组 (`policy-path`) 加载的策略。每个条目都包含策略名称、所属策略组以及一个标识符。由于外部策略无法通过名称引用，因此请将此标识符作为 `$httpClient` 的 `policy` 选项传递，以便通过该策略发送请求。

**[#417](https://t.me/SurgeTestFlightFeed/417) · 2026-10-13**

我们很高兴地宣布，Surge Mac 6.10.0、Surge iOS 5.23.0 和 Surge tvOS 5.23.0 现已发布。

**VS Code 扩展程序 (Mac)**
新增对 VS Code 的 Surge Language Support 扩展的支持：为 profile、模块和规则集提供语法高亮与实时诊断；主 profile 打开时还会自动检测拆分配置，并校验其中的策略引用。
该扩展依赖本机的 Surge App 包做解析，要求 Surge Mac 6.10.0 或更高版本；Surge 升级后，扩展的 profile 解析能力会自动跟随更新。
https://marketplace.visualstudio.com/items?itemName=SurgeNetworks.surge-language-support

**IP Rewrite**
新增 `[IP Rewrite]` 配置段，在数据包进入任何规则或策略之前，在 IP 层按目标地址处理进入 Surge VIF 的数据包。它可为某些 iOS 开发工具链提供设备本机回环功能。可用动作：
- `reflect`：交换源地址与目标地址，把数据包发回发送方。
- `reject`：对连接尝试回 TCP RST；对其它数据包回 ICMP administratively prohibited，使发送方立即失败。
- `drop`：静默丢弃数据包。

**其他新功能**
- 为策略组添加了 `category` 参数，用于分组显示，在策略组数量较多时非常有用。
- 所有 `test-url` 参数现在都支持 HTTPS URL。结果仍衡量单次 HTTP 往返的延迟；策略数量较多时，TLS 握手可能显著增加整体测试耗时。
- 新增主动更新已关联配置文件的选项。基于 URL 的已关联配置现在可以手动更新。
- 为 HTTP API 添加了外部资源管理及其他辅助端点。
- 为 Include All 模式新增设备通信接管选项。（iOS）

**界面与规则**
- 更新了 iPhone Duo 支持的 UI 布局和细节。(iOS)
- 改进“添加规则”页面：现在可根据 SNI 嗅探的请求创建域名规则，并直接选择相应规则的专用选项。
- 名称相同的内联规则集现在会在主配置文件和模块之间合并，而不是相互替换，从而保留每个来源贡献的规则。
- 修复：逻辑规则无法正确解析含括号的策略名。

**网络与可靠性**
- 改进了在网络间切换时 Tailscale 和 WireGuard 的行为。
- 改进：对没有互联网出口的点对点 Tailscale / WireGuard 策略，UDP 测试会直接报告不支持，避免一直等待至超时。
- 之前的版本通过为每个不同域名生成独立密钥对来加强了 MITM 安全性，但这导致在同时拦截多个不同域名时出现了明显的延迟。经过评估，此更改已被撤销。
- 移除了在使用策略组中的 Ponte 策略时出现的错误 Ponte 通知。
- 修复了脚本引擎的一个兼容性问题。
- 针对 macOS 27.2 beta 的系统错误加入规避措施，防止 Dashboard 崩溃。（Mac）
- 改进了性能和内存使用情况，修复了罕见的崩溃问题，并解决了其他一些小问题。

---

## 二、最近 30 天上下文

| 通道 | 版本 | build | 日期 |
|---|---|---:|---|
| 正式版 | `6.10.0` | 12500 | 2026-10-12 |
| 正式版 | `6.9.1` | 12290 | 2026-09-09 |
| 正式版 | `6.9.0` | 12250 | 2026-08-31 |
| 正式版 | `6.8.1` | 12030 | 2026-08-10 |
| 正式版 | `6.8.0` | 11990 | 2026-08-06 |
| 正式版 | `6.7.0` | 11730 | 2026-07-15 |
| Beta | `6.11.0` | 12510 | 2026-10-13 |
| Beta | `6.10.0` | 12500 | 2026-10-12 |
| Beta | `6.9.1` | 12290 | 2026-09-09 |
| Beta | `6.9.0` | 12250 | 2026-08-31 |
| Beta | `6.8.1` | 12030 | 2026-08-10 |
| Beta | `6.8.0` | 11990 | 2026-08-06 |

> 同一版本的多个 beta build 在 appcast 里会**原地被覆盖**（只剩最后一条），
> 所以 build 级的中间过程要看上一节的 Telegram 公告。

---

## 关于中文翻译

本页复用已有译文，新增发布说明由 **Index-Translate 自动翻译**，译文缓存于
[`translations.json`](translations.json)。

自动译文通过技术内容与输出格式校验后直接使用，无需逐条人工审核。代码、参数、版本号、URL 和 Markdown 链接会受到保护。**格式校验不保证语义完全正确**；配置使用条件请以上游原文为准。

接口超时、限流或校验失败时保留英文，后续巡检自动重试；每套文档每轮最多处理 40 条、调用时间预算 120 秒，剩余条目留待后续处理。本地可用 `--no-auto-translate` 禁用调用；`--dry-run` 不调用翻译接口。

想补译：在 `translations.json` 的 `entries` 里加一条 `{"en": "<英文原文>", "zh": "<中文>"}` 即可，英文原文可从下方待译清单复制（不必包含 commit sha 与 `by @作者`，脚本会先做归一化）。

**当前没有待译条目 —— 最近一周的全部发布说明均已译为中文。**
