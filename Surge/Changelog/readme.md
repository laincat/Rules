# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#427](https://t.me/SurgeTestFlightFeed/427) · 2026-10-25

### Surge iOS 6 正在路上！
我们目前正在为即将发布的 Surge iOS 6 做准备。
在我们专注于完成新重大版本的最终开发并为其发布做好准备期间，TestFlight 更新将暂时暂停。在此期间，我们将不会通过 TestFlight 分发任何新的测试版本构建。
这是我们在过渡到下一个主要版本期间计划进行的暂停。一旦我们准备好继续测试 Surge iOS 6，TestFlight 更新就会恢复。
感谢您持续的支持与耐心。
敬请期待 — 我们很快将带来更多更新！

## [#426](https://t.me/SurgeTestFlightFeed/426) · 2026-10-22

### Beta 更新
对等访问
- 由于 `peer-access-passthrough` 存在副作用，现已被移除，其行为已恢复为先前版本。现在已内置针对 Apple 屏幕共享的特殊处理，无需任何配置即可正常工作。
规则集
- 移除了规则集和域集上 1,000,000 条目的限制。
Surge VM
- [Mac] 网关设置中新增“禁用 UDP 快速路径”选项。当设备在短时间内创建大量 UDP 流时（例如 P2P 下载），Surge VM 通常会将这些流移至 UDP 快速路径。该路径会直接在 L3 层转发 UDP 流量，而不会应用任何规则。启用此选项后，所有设备都将不再使用快速路径，从而确保所有 UDP 流量始终经过您的规则。
修复
- 修复了 iCloud Drive 同步无法再从其他设备拉取更改的问题。本地更改仍会正常上传。该问题源于旧版本遗留下来的一个缺少写入权限的锁定文件。Surge 现在会自动修复该文件。

## [#425](https://t.me/SurgeTestFlightFeed/425) · 2026-10-21

### Beta 更新
SOCKS5 UDP
- built-in SOCKS5 代理服务器现已支持 UDP ASSOCIATE。SOCKS5 客户端可以通过 Surge 发送 UDP 流量，这些流量会像 TCP 流量一样，经过您的规则集和策略组。每个关联的第一个数据报会根据您的规则集进行匹配，后续数据报则使用相同的策略组。
对等访问直通
- 为 Tailscale 和 WireGuard 策略组引入了新的 `peer-access-passthrough` 选项。当启用 `accept-incoming` / `allow-peer-access` 时，该选项默认开启。- 到此设备隧道地址的入站连接将直接交给本地服务处理，因此服务可以看到对端的真实地址和端口。
- 此设备发送到对等地址的流量会直接进入隧道。
- 规则和请求列表不适用于这些流。
- 这对于那些会连接回其看到的对等地址的协议是必需的，例如 Apple 屏幕共享的 high-performance 模式。
- 将 `peer-access-passthrough = false` 设置为保留之前的行为。此时，入站连接将通过 Surge，并应用规则集和请求记录。
- 现在，通过 Tailscale 或 WireGuard 转发的 UDP 流量在源端口空闲时，会保留客户端的源端口。
QUIC 块模式
- [iOS] 现在可以在 iOS 上的代理列表编辑器中更改全局 `block-quic` 设置，与 Mac 上的操作方式相同。
改进
- Tailscale：管理控制台不再为运行 Surge 的设备显示更新警告。
- Tailscale：现在，若 DERP 连接在 120 秒内未收到任何数据，则会被视为已断开并重新连接。此前，静默丢失的连接可能会导致所有转发的流量中断，直到 Surge 重启。
- Ponte：当两端具有相同的虚拟机桥接地址时（OrbStack、Parallels、UTM 及类似情况），设备不再被错误地视为处于同一局域网。
- Ponte：当 LAN 连接尝试失败时，Surge 现在会回退到 Internet 模式并刷新设备记录，而不会因 ping 超时而终止。
- Ponte：日志中的设备记录现在不再包含 PSK 或控制器密钥。
- 流量统计：Tailscale MagicDNS 主机（`*.ts.net`）现在会以其完整主机名显示，而不会全部归入 `ts.net`。per-host 报告现在会对同一主机的条目进行汇总，而不再是仅保留其中一条。
- HTTP 代理：`Proxy-Authorization` 标头将不再转发到上游服务器。它用于承载 Surge 自身代理的凭据。
- HTTP/2：格式错误的请求现在只会重置其自身的流，而不会重置整个连接。
- HTTP/2：当上游服务器在响应中途关闭连接时，Surge 现在会将其报告为“截断”，而非“完整响应”。
- `$httpClient`: 现在，URL 中的 percent-encoded 用户名和密码在作为基本身份验证发送之前会先被解码。无法解码的响应正文现在将报告为错误。
修复
- [iOS] 修复了在 iOS 上被拒绝的大小超过 2 MB 的地图本地数据文件的问题。现在，限制已调整为 15 MB，与手册中的说明一致。
- 修复了当响应脚本和正文重写规则均匹配时，HTTP/2 响应中无正文（304、204 或对 HEAD 的响应）未被正确处理的问题。
- 修复了在未返回任何策略组列表时，使用 WebView 引擎的脚本中 `$surge.retestGroup` 失效的问题。
- 修复了在分块请求体之后发送的流水线 HTTP/1 请求被作为该请求体的一部分转发，而非作为独立请求处理的问题。
- 修复了 HTTP/1 连接复用和关闭过程中的几个边缘情况，这些问题可能导致响应混淆或连接保持打开状态。

## [#424](https://t.me/SurgeTestFlightFeed/424) · 2026-10-21

### 安全通告：eMudhra 中间 CA 证书遭泄露
最近披露了一起涉及 eMudhra 中间证书颁发机构 (CA) 的严重安全事件。CA 私钥遭泄露可能会使攻击者能够为任意域名签发看似合法的 TLS 证书，从而有可能对 HTTPS 连接实施 man-in-the-middle (MITM) 攻击。
包括 Apple、Google、Microsoft 和 Mozilla 在内的主要平台供应商已采取措施，不再信任受影响的 CA 证书。
Surge 用户无需执行任何操作。尽管 Surge 使用其自身的 TLS 协议栈和 MITM 引擎，但它严格依赖操作系统的证书信任评估机制来验证证书链。因此，Surge 能够受益于操作系统所强制实施的相同证书信任和吊销保护。
安全提醒：除非明确需要，否则请勿在您的 MITM 配置中启用 skip-server-cert-verify 参数。启用此选项会绕过对上游服务器的 TLS 证书验证，并可能使您的连接面临 MITM 攻击。

## [#423](https://t.me/SurgeTestFlightFeed/423) · 2026-10-20

### macOS 上的仪表板问题 27.2
macOS 27.2 上的 Surge Mac 用户：您可能会发现 Surge 仪表盘在启动后立即退出。Surge 本身及所有网络功能均不受影响。
此问题由 macOS 27.2 中的一个系统问题引起，也可能影响其他应用程序。我们已向 Apple 报告了该问题，Apple 已确认修复方案，该修复将随下一个 macOS 更新一同发布。
在此期间：
• 如果您的更新订阅处于活动状态，请更新到 Surge Mac 6.10.0 或更高版本，该版本已对该问题进行了规避处理。
• 如果您的订阅已过期，我们已发布 Surge Dashboard Patcher，这是一款免费工具，仅将捆绑的 Dashboard 替换为修复后的版本。Surge 和您的配置文件均不受影响。
• 或者，您也可以直接等待下一个 macOS 更新，该更新将解决此问题。
详细信息和下载：
[https://kb.nssurge.com/surge-knowledge-base/faq/mac-dashboard-crash](https://kb.nssurge.com/surge-knowledge-base/faq/mac-dashboard-crash)

## [#422](https://t.me/SurgeTestFlightFeed/422) · 2026-10-19

### Surge tvOS Beta 测试版
- 现在可以直接在 Apple TV 上控制 Surge tvOS。Surge 运行时，启动界面新增一列，包含：
- 出站模式按钮。其菜单还可开启或关闭 MitM、Rewrite 与 Scripting。
- 策略组页面。你可以选择策略、覆盖自动组、运行延迟测试并查看 Smart Group 使用情况。使用 `icon-url` 设置的组图标会采用与 iOS 相同的显示方式。
- 外部资源页面。你可以逐个更新资源，也可以一次全部更新。
- 请注意，使用新版 tvOS 版本前，需要先通过最新版 Surge iOS TestFlight 重新部署，否则无法启用。

## [#421](https://t.me/SurgeTestFlightFeed/421) · 2026-10-19

### Snell 6.0.0 版本
Snell 6.0.0 RC2 已作为最终 6.0.0 版本发布，下载链接也已更新。此外新增了 macOS arm64 二进制。
请查看：[https://kb.nssurge.com/surge-knowledge-base/release-notes/snell](https://kb.nssurge.com/surge-knowledge-base/release-notes/snell)

## [#420](https://t.me/SurgeTestFlightFeed/420) · 2026-10-19

### Beta 更新
Tailscale 和 WireGuard 的入站连接
- 旧参数 `accept-incoming` 已重命名为 `allow-peer-access`，但为了兼容仍会读取该旧参数。
- 修复了目标地址为本机时，入站 UDP 数据包无法转发的问题。
- 请注意，由于 Apple Screen Sharing 的通信机制特殊，即使启用 `allow-peer-access`，也无法使用 high-performance（高性能）模式。我们正在研究专门的处理方案。
规则集编辑器
- 现在可以在规则集中通过 Enable/Disable 滑动操作禁用单条规则。禁用规则会保存为 commented-out 行。
改进
- Snell v6：UDP 数据现在会在隧道命令后立即发送，无需等待服务器响应的一次往返。通过 Snell v6 建立 QUIC 连接的速度会明显更快；这需要 v6 服务器。
- 自适应 QUIC 阻断：现在只从新的 QUIC 握手开始检测。此前，已经存在的 QUIC 连接（例如 Surge 启动前建立的连接）发来的数据包可能被错误地记为已允许。现在会阻断这些数据包，使应用重新发起新的握手。
- 端口 443 上的 DTLS、WireGuard、STUN 及其他 non-QUIC UDP 流量不再被当作 QUIC，因此 `block-quic` 不再影响这些流量。
- 当 SOCKS5 代理拒绝连接时，Surge 现在会显示服务器给出的原因（例如 connection refused 或 host unreachable），不再只显示“invalid response”错误。
- Ponte：如果设备记录是在其远程通道重启期间捕获的，设备不再一直卡在“LAN-only 模式”。Surge 会在放弃前刷新设备列表，错误信息现在也会说明原因。
- [Mac] 解决了在同一设备上使用多个用户或多个操作系统时需要反复激活的问题。有关具体方法，请参阅知识库的授权 FAQ。
修复
- 修复了服务器在 304 或其他本应无响应体的响应后仍发送 body 时，请求返回 503 的问题（例如 ASUSWRT-Merlin 路由器）。
- [iOS] 修复了客户端读取较慢时 MITM HTTP/2 连接占用内存过高的问题；此前可能使网络扩展超过内存上限。
- [iOS] 修复了日志中脚本记录很大时查看 Logbook 可能导致网络扩展崩溃的问题。
- [iOS] 修复了外部资源视图有时重复弹出的问题。
- [iOS] 修复了部分弹窗尺寸下文本框被键盘遮挡，以及键盘收起后为键盘预留的空间有时没有移除的问题。
- [iOS] 优化了 iPhone Duo 的键盘布局。

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

技术字面量、代码、版本号和链接会先替换为占位符，译文通过格式与占位符校验后才使用。

本轮仍有 **2** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `SOCKS5 UDP`
- `Surge VM`
