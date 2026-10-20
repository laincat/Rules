# Surge 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 最近更新：2026-10-20T00:25:50Z（UTC）

数据来源：Surge Mac 的 **appcast 双通道**（官方更新日志页读的就是它）
与 **Telegram @SurgeTestFlightFeed**。
iOS 版本来自 **App Store**。

---

## 一、最近 7 天

### 正式版（本周无新版本，最近一次如下）

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

#### `6.11.0`（build 12570） · 2026-10-19


**自适应 QUIC 阻断**
- 为代理策略添加了 `block-quic=adaptive`。Surge 最初会阻止 QUIC，从而使应用程序回退到基于 TCP 的 HTTPS。如果应用程序未能在 1 秒内回退（例如仅支持 QUIC 的应用程序），则允许该主机使用 QUIC。结果会按主机缓存。此选项在 Mac 和 iOS 上的代理编辑器中也可用。
- `block-quic=auto` 现在对除 DIRECT 外的所有策略采用自适应模式，使仅支持 QUIC 的应用仍能通过代理工作。无法转发 UDP 的策略仍会阻断 QUIC。
- QUIC 主机名识别现在支持跨多个数据包的 TLS ClientHello；采用后量子密钥交换的新浏览器常见这种情况。同时支持 QUIC v2 和 draft-29。规则、MITM 与请求记录现在能识别更多 QUIC 连接的主机名。
- 端口 443 上的 DTLS、WireGuard、STUN 及其他 non-QUIC UDP 流量不再被当作 QUIC，因此 `block-quic` 不再影响这些流量。

**Tailscale 和 WireGuard 的入站连接**
现在，Surge 不仅可以发送出站流量，还可以接受通过 Tailscale 和 WireGuard 传入的连接。入站请求的处理方式与其他请求相同：它们会经过您的规则集和策略组，并显示在请求列表中。
**Tailscale**
- `allow-peer-access = true`：Tailnet 中的其他设备可通过此设备的 tailnet 地址连接到它。例如，它们可以使用 Surge 的 HTTP/SOCKS5 代理或该设备上的其他服务。（旧参数 `accept-incoming` 已重命名，但为了兼容仍会读取。）
- `advertise-exit-node = true`: 将此设备提供为出口节点。选择它的其他 tailnet 设备会通过 Surge 的规则发送其所有互联网流量。
- `advertise-routes = 192.168.1.0/24, ...`: 将此设备作为所列网络的子网路由器提供。
- 退出节点和子网路由在您于 Tailscale 管理控制台中批准后生效。
**WireGuard**
- `allow-peer-access = true`: 对端可以通过现有隧道与此设备建立连接。
- `listen-port = 51820`: Surge 充当 WireGuard 服务器，手机、笔记本电脑和其他客户端都可以连接到它。对等方可以省略 `endpoint`; Surge 会在客户端连接时获知其地址，并在地址变更时保持同步。
- 客户端可以将 Surge 的隧道地址设置为自己的 DNS 服务器，Surge 的 DNS 将响应其查询。
注意：Surge 不会将您的 Tailscale 访问控制策略应用于入站连接。请使用 `SRC-IP` 等规则来限制谁可以访问哪些目标。

**规则集编辑器**
- 现在可以在规则集中通过 Enable/Disable 滑动操作禁用单条规则。禁用规则会保存为 commented-out 行。

**HTTP API**
- HTTP API 的 `GET /v1/policies` 现在接受 `include_external=true` 查询参数。响应中将包含一个额外的 `external-policies` 字段，用于列出从外部策略组 (`policy-path`) 加载的策略。每个条目都包含策略名称、所属策略组以及一个标识符。由于外部策略无法通过名称引用，因此请将此标识符作为 `$httpClient` 的 `policy` 选项传递，以便通过该策略发送请求。

**改进**
- Snell v6：UDP 数据现在会在隧道命令后立即发送，无需等待服务器响应的一次往返。通过 Snell v6 建立 QUIC 连接的速度会明显更快；这需要 v6 服务器。
- Ponte：如果设备记录是在其远程通道重启期间捕获的，设备不再一直卡在“LAN-only 模式”。Surge 会在放弃前刷新设备列表，错误信息现在也会说明原因。
- 当 SOCKS5 代理拒绝连接时，Surge 现在会显示服务器给出的原因（例如 connection refused 或 host unreachable），不再只显示“invalid response”错误。
- 解决了在同一设备上使用多个用户或多个操作系统时需要反复激活的问题。有关具体方法，请参阅知识库的授权 FAQ。

**修复**
- 修复了一个问题：当 `external` 策略被直接用作另一策略的 `underlying-proxy` 时，其进程不会自动启动。只有在执行延迟测试后，该进程才会启动。
- 修复了服务器在 304 或其他本应无响应体的响应后仍发送 body 时，请求返回 503 的问题（例如 ASUSWRT-Merlin 路由器）。

### 官方公告（Telegram）

**[#422](https://t.me/SurgeTestFlightFeed/422) · 2026-10-19**


**Surge tvOS Beta 测试版**
- 现在可以直接在 Apple TV 上控制 Surge tvOS。Surge 运行时，启动界面新增一列，包含：
- 出站模式按钮。其菜单还可开启或关闭 MitM、Rewrite 与 Scripting。
- 策略组页面。你可以选择策略、覆盖自动组、运行延迟测试并查看 Smart Group 使用情况。使用 `icon-url` 设置的组图标会采用与 iOS 相同的显示方式。
- 外部资源页面。你可以逐个更新资源，也可以一次全部更新。
- 请注意，使用新版 tvOS 版本前，需要先通过最新版 Surge iOS TestFlight 重新部署，否则无法启用。

**[#421](https://t.me/SurgeTestFlightFeed/421) · 2026-10-19**


**Snell 6.0.0 版本**
Snell 6.0.0 RC2 已作为最终 6.0.0 版本发布，下载链接也已更新。此外新增了 macOS arm64 二进制。
请检查：https://kb.nssurge.com/surge-knowledge-base/release-notes/snell

**[#420](https://t.me/SurgeTestFlightFeed/420) · 2026-10-19**


**Beta 更新**

**Tailscale 和 WireGuard 的入站连接**
- 旧参数 `accept-incoming` 已重命名为 `allow-peer-access`，但为了兼容仍会读取该旧参数。
- 修复了目标地址为本机时，入站 UDP 数据包无法转发的问题。
- 请注意，由于 Apple Screen Sharing 的通信机制特殊，即使启用 `allow-peer-access`，也无法使用 high-performance（高性能）模式。我们正在研究专门的处理方案。

**规则集编辑器**
- 现在可以在规则集中通过 Enable/Disable 滑动操作禁用单条规则。禁用规则会保存为 commented-out 行。

**改进**
- Snell v6：UDP 数据现在会在隧道命令后立即发送，无需等待服务器响应的一次往返。通过 Snell v6 建立 QUIC 连接的速度会明显更快；这需要 v6 服务器。
- 自适应 QUIC 阻断：现在只从新的 QUIC 握手开始检测。此前，已经存在的 QUIC 连接（例如 Surge 启动前建立的连接）发来的数据包可能被错误地记为已允许。现在会阻断这些数据包，使应用重新发起新的握手。
- 端口 443 上的 DTLS、WireGuard、STUN 及其他 non-QUIC UDP 流量不再被当作 QUIC，因此 `block-quic` 不再影响这些流量。
- 当 SOCKS5 代理拒绝连接时，Surge 现在会显示服务器给出的原因（例如 connection refused 或 host unreachable），不再只显示“invalid response”错误。
- Ponte：如果设备记录是在其远程通道重启期间捕获的，设备不再一直卡在“LAN-only 模式”。Surge 会在放弃前刷新设备列表，错误信息现在也会说明原因。
- [Mac] 解决了在同一设备上使用多个用户或多个操作系统时需要反复激活的问题。有关具体方法，请参阅知识库的授权 FAQ。

**修复**
- 修复了服务器在 304 或其他本应无响应体的响应后仍发送 body 时，请求返回 503 的问题（例如 ASUSWRT-Merlin 路由器）。
- [iOS] 修复了客户端读取较慢时 MITM HTTP/2 连接占用内存过高的问题；此前可能使网络扩展超过内存上限。
- [iOS] 修复了日志中脚本记录很大时查看 Logbook 可能导致网络扩展崩溃的问题。
- [iOS] 修复了外部资源视图有时重复弹出的问题。
- [iOS] 修复了部分弹窗尺寸下文本框被键盘遮挡，以及键盘收起后为键盘预留的空间有时没有移除的问题。
- [iOS] 优化了 iPhone Duo 的键盘布局。

**[#419](https://t.me/SurgeTestFlightFeed/419) · 2026-10-14**


**Tailscale 和 WireGuard 的入站连接**
现在，Surge 不仅可以发送出站流量，还可以接受通过 Tailscale 和 WireGuard 传入的连接。入站请求的处理方式与其他请求相同：它们会经过您的规则集和策略组，并显示在请求列表中。

**Tailscale**
- `accept-incoming = true`: 您 tailnet 网络中的其他设备可以通过该设备的 tailnet 地址连接到此设备。例如，它们可以使用 Surge 的 HTTP/SOCKS5 代理或运行在此设备上的其他服务。
- `advertise-exit-node = true`: 将此设备提供为出口节点。选择它的其他 tailnet 设备会通过 Surge 的规则发送其所有互联网流量。
- `advertise-routes = 192.168.1.0/24, ...`: 将此设备作为所列网络的子网路由器提供。
- 退出节点和子网路由在您于 Tailscale 管理控制台中批准后生效。

**WireGuard**
- `accept-incoming = true`: 对端可以通过现有隧道与此设备建立连接。
- `listen-port = 51820`: Surge 充当 WireGuard 服务器，手机、笔记本电脑和其他客户端都可以连接到它。对等方可以省略 `endpoint`; Surge 会在客户端连接时获知其地址，并在地址变更时保持同步。
- 客户端可以将 Surge 的隧道地址设置为自己的 DNS 服务器，Surge 的 DNS 将响应其查询。
注意：Surge 不会将您的 Tailscale 访问控制策略应用于入站连接。请使用 `SRC-IP` 等规则来限制谁可以访问哪些目标。
需要 iOS 5.24.0+ / Mac 6.11.0+. 有关详细信息和示例配置，请参阅手册中的 Tailscale 和 WireGuard 页面。

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
| Beta | `6.11.0` | 12570 | 2026-10-19 |
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
