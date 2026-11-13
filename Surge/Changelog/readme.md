# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#454](https://t.me/SurgeTestFlightFeed/454) · 2026-11-12

### Beta 更新

#### Surge 引擎

##### 性能

- Hysteria 2 和 TUIC 的下载速度更快，占用的 CPU 更少。Surge 现在可以批量确认已接收的数据包。在一台 10 GbE 测试机上，Hysteria 2 的速率从 2.86 提升至 3.84 Gbps，CPU 占用率从 137% 降至 108%。
- Hysteria 2 和 TUIC 上传功能不再一次性发送整个拥塞窗口，这曾导致服务器过载并引发丢包。现在，共享同一连接的多个上传任务可以公平地分配带宽。
- 通过其他代理的 UDP 中继运行的 QUIC 会话（例如通过 SOCKS5 或 Shadowsocks 运行的 Hysteria 2）现在会批量发送数据包。其上传速度大幅提升。
- UDP over AnyTLS 和 VLESS 在高速率下已不再丢失大部分上传数据。现在，已排队的 TLS 写入将一并发送。
- HTTP/3 隧道（TrustTunnel 与 `h3=true`、MASQUE）和 SSH 不再为每个数据包花费 CPU 时间来格式化日志行。
- 出站 UDP 套接字和 SOCKS5 UDP 中继现在使用更大的套接字缓冲区，而非系统默认值，因此在负载下丢包会更少。
- 通过 MASQUE、TUIC、HTTP/2 CONNECT、TrustTunnel 或 VLESS gRPC 同时打开多个隧道时，不会再出现部分隧道停滞或挂起的情况。当达到服务器的流限制时，Surge 现在会打开更多连接。

##### 可靠性

- 当 Hysteria 2、TUIC 或 MASQUE 服务器停止响应时，Surge 现在大约能在 3 秒内察觉到并建立新连接。在此之前，新请求会持续发送到已失效的连接上，导致下载任务在空闲超时前一直处于挂起状态。
- MASQUE UDP 关联现在可以在服务器关闭其 QUIC 连接后仍然存在。
- 当一条以 1,350 字节发起的连接未收到任何响应时，MASQUE 现在会在 30 分钟内回退到 1,200 字节的数据包。MTU 较小的路径可以重新建立连接。MASQUE 现在也接受来自服务器的更大数据报帧。

##### 修复

- 修复了 TrustTunnel 的 HTTP/2 下载在全速运行几秒后总会中断的问题。
- 修复了 Hysteria 2 在启用混淆后上传几秒即卡住的问题。
- 修复了在使用 TrustTunnel 和 `h3=true` 时，当大量连接繁忙导致 HTTP/3 上传暂停数秒的问题。
- 修复了在相同连接上进行大文件上传时，通过 Hysteria 2、TUIC 和 MASQUE 传输的 UDP 数据报被丢弃的问题。
- 修复了 HTTP/2 CONNECT-UDP：
  - UDP 发送速度超过了连接承载能力，导致后续数据报被堆积并延迟了数秒。
  - 快速 UDP 上传丢失了大部分数据包。
  - Envoy 在快速 UDP 下载期间重置了连接。
- 修复了基于 TLS 的策略在服务器完成发送后丢弃上传剩余部分的问题。
- 修复了当服务器先完成时，HTTP/2 CONNECT 会丢失上传末尾数据的问题。
- Fixed Trojan UDP to hostnames failing with sing-box servers.
- 修复了 VLESS Vision 的一个崩溃问题。
- 修复了在重新加载配置文件后，Snell 服务器、MTProto 代理和端口转发因“地址已被使用”而未能重启的问题。这是一个回归问题。
- 修复了当 HTTP API 请求中包含错误类型的字段（例如，`/v1/scripting/evaluate` 的 `timeout` 不是数值）时发生的崩溃问题。现在，此类请求将返回 400 响应。
- Snell 服务器和 Vector：
  - 修复了 Snell v6 服务器丢弃 IPv6 UDP 的问题。
  - 修复了 Vector 服务器将 UDP 数据报流重置到其他主机名的问题。
  - 修复了当服务器先完成时 Vector 截断上传的问题。

##### Surge Mac

- 代理编辑器现在支持 VLESS，包括 REALITY、gRPC 和 WebSocket。您还可以导入 `vless://` 分享链接。

#### Surge iOS

##### 改进

- 代理编辑器现在支持 VLESS，包括 REALITY、gRPC 和 WebSocket，并且可以导入 `vless://` 分享链接。
- VMess、TUIC v4 和所有 Shadowsocks 密码已重新加入代理编辑器。TUIC v4 是 TUIC 的一个版本选项。
- 在丢包、高延迟的网络上，QUIC 上传（Hysteria 2、TUIC）的速度要快得多。
- 在易丢包网络上通过 QUIC 进行下载时，内存使用更少。

##### 修复

- 修复了针对许多主机的 HTTP/2 MITM 问题，该问题导致网络扩展超出其内存限制。这是近期测试版中出现的一项回归问题。

## [#453](https://t.me/SurgeTestFlightFeed/453) · 2026-11-11

- 修复了通过 SSH 策略组上传的文件在会话重新加密后损坏的问题，该问题在传输量达到 1 GB 后发生。
- 修复了 Surge 两次关闭通道后，SSH 服务器断开整个会话及其上所有隧道的问题。
- 修复了 Envoy 中的几个 MASQUE 问题：
  - 每个新的 UDP 目的地址的第一个数据包都丢失了。
  - 当单个连接上打开约 100 个目标后，UDP 到新目标的一次连接失败。
  - 1,200 字节的 UDP 响应被丢弃。
- MASQUE 现在发送 1,350 字节的 QUIC 数据包，因此无法通过 MTU 低于 1,378（IPv4）或 1,398（IPv6）的路径进行连接。
- 修复了关闭某个 HTTP/3 流有时会关闭整个 HTTP/3 会话及其上的所有隧道（MASQUE、带有 `h3=true` 的 TrustTunnel）的问题。
- 修复了半关闭连接丢失数据的问题。例如，客户端发送请求后关闭发送端并等待响应，或服务器先完成处理：
- 修复了 AnyTLS 流在客户端完成发送后仍保持打开 60 秒的问题。
- 修复了 AnyTLS 记录中因 `$httpClient` 请求导致上传量为负数的问题，该问题在流量统计中显示为 18446744.07 TB。
- 修复了当服务器宣布 15 秒空闲超时后，空闲的 TUIC 连接在约 15 秒后被关闭的问题。现在，Surge 的保活时间最多为协商后空闲超时时间的一半。
- 修复了 Shadowsocks 2022 静默丢弃大于 1500 字节的已接收 UDP 数据报的问题。通过 Shadowsocks 传输的 WireGuard 完整尺寸回复均会丢失。
- 修复了当 WireGuard 通过 Shadowsocks 或 SOCKS5 等 UDP 中继进行级联时，TCP 始终无法连接，而 UDP 却能正常工作的问题。Surge 现在会降低内部 TCP 的 MSS，以适应额外的封装。
- 修复了当发送方速度超过连接速度时，UDP over AnyTLS、Trojan 和 VLESS 无限排队的问题，该问题可能导致消耗数 GB 内存。现在，当连接拥塞时，数据报将被丢弃。
- 修复了在握手期间入站连接突发被重置的问题，例如一次性出现 200 个 SOCKS5 连接。此问题影响了 HTTP 和 SOCKS5 代理服务、HTTP API、控制器、Snell 服务器以及端口转发功能。
- 修复了 HTTP/2 页脚被误判为格式错误的响应，以及在流结束后使用 NO_ERROR 重置流时缓冲数据丢失的问题。

### Surge iOS

#### 改进

- 现在，只要 iOS 因任何非您主动停止的原因而中断 VPN，Surge 就会发送通知。此前，仅在 VPN 配置文件被禁用时才会发送通知。
- “主页”选项卡的“无”样式已回归。选择“无”后，将不再显示“主页”选项卡，“配置”页面的页眉将用于启动和停止 Surge。
- 代理编辑器新增了一个用于 TrustTunnel 客户端随机身份验证密钥的字段。

#### 修复

- 修复了在卡片菜单仍在关闭时滑动类别后，策略组卡片消失以及卡片不再响应点击的问题。
- 修复了在行菜单仍在关闭时进行滑动操作，导致某个模块自动开启或关闭的问题。
- 修复了在短暂滑动后页面回弹期间，于“配置”页面滑动时无任何反应的问题。
- 修复了展开后的策略组卡片中，磁贴和滚动指示器超出其圆角范围的问题。
- 修复了“配置”页面在重新启动前仍保留先前启动切换器样式的标题的问题。
- 原本以负值存储（源自 AnyTLS 漏洞）的流量统计数据现在将显示为 0。

## [#452](https://t.me/SurgeTestFlightFeed/452) · 2026-11-11

### Beta 更新

#### Surge 引擎

##### AI 驱动型测试平台

我们为 Surge Engine 构建了一个完全自动化且由 AI 驱动的测试平台。该平台会持续评估 Surge Engine 在所有受支持的代理协议的最新官方客户端实现环境下的兼容性与性能，从而确保 Surge Engine 的性能能够与之匹配甚至超越。

未来，对 Surge Engine 的每一次更改都将通过此平台进行验证，以便及早发现兼容性问题及其他错误，防止性能退化，并确保在每次更新后都能保持一致的可靠性。

##### 性能

- 修复了大量在特定配置或环境下可能出现的性能问题，尤其是在代理链组合下的性能问题。

#### 代理协议

##### VLESS

- 新增 `vless` 代理类型。它支持 RAW 或 WebSocket 传输，无 TLS、TLS 或 REALITY。它还支持 `xtls-rprx-vision` 流以及通过 TLS 或 REALITY 的 gRPC 传输。
- UDP 始终作为 XUDP 发送。

##### TrustTunnel

- TrustTunnel 服务器新增 `client-random-auth-key` 参数（适用于 v1.3.0-beta.2 及更高版本），该参数仅接受能够证明其持有共享密钥的客户端。此功能在 HTTP/2 和 HTTP/3 模式下均可使用。
- 该参数需要一个 SNI，并且在清理后的配置文件中会被屏蔽。

##### 重新加载配置文件

- 更改 `[Proxy]`、`[Proxy Group]` 或 `[Keystore]` 已不再中断 SSH、HTTP/2 CONNECT、MASQUE、TUIC 和 Hysteria 2 策略中仍在传输的连接，前提是这些策略自身的定义未变。现在，它们的共享连接将被保留，正如 WireGuard 和 Tailscale 会话早已实现的那样。

##### 更快的故障检测

- 现在，错误的凭据会立即失败，而不会等到 10 秒的设置超时之后。这包括：
  - HTTP 和 HTTPS (407 或 401)
  - SOCKS5（身份验证被拒绝，或没有可接受的方法）
  - Hysteria 2
  - 不匹配 `server-fingerprint` 的 SSH 主机密钥（错误信息中会指明服务器提供的密钥名称）
  - ShadowTLS v3
- 当服务器在设置期间关闭连接时（例如，TrustTunnel 的密钥错误），Surge 现在会重试一次然后失败，而不会一直重试直到超时。

##### 修复

## [#451](https://t.me/SurgeTestFlightFeed/451) · 2026-11-11

### Surge 测试版现已支持 VLESS 和 REALITY

最新的 Surge 测试版新增了对 VLESS 协议的支持，包括通过 REALITY 保护的安全连接。目前仅可通过基于文本的配置文件进行配置；有关语法和支持的选项，请参阅 [https://manual.nssurge.com/policies/vless.html](https://manual.nssurge.com/policies/vless.html)。

#### 我们为何要添加 VLESS 和 REALITY

在人工智能让编写代码变得前所未有的简单这个时代，实现一个功能早已不再是难事。但真正没有变得更便宜的，是随之而来的所有工作：我们每增加一个协议，就意味着承担了一项长期的维护、安全和支持承诺，而这也会塑造 Surge 的核心理念。正因如此，我们在决定将哪些内容纳入 Surge 时，反而变得更加审慎，而非更草率。我们曾对 VLESS 和 REALITY 犹豫不决，从来不是因为无法实现它们，而是因为不确定是否应该实现它们。

我们对他们的技术设计的某些方面存有保留意见。同时，我们的许多用户需要这些技术，而且我们知道，有些用户已经转而使用 Surge 的非官方修改版本来获取这些技术，而这会带来切实的安全风险。最终，我们决定，提供一个受支持且值得信赖的实现方案，比让用户无此方案可用，更能服务于我们的用户。

#### 致 Surge iOS 用户的提醒

正如我们先前所宣布的，Surge iOS 上的协议支持不再需要有效的订阅。所有受支持的协议（包括 VLESS 和 REALITY）均可免费提供给所有 Surge iOS 用户。

## [#450](https://t.me/SurgeTestFlightFeed/450) · 2026-11-11

- 配置文件错误现在会说明某条线路无效的原因，而不仅仅是指出其位置。
- [General] 中新增的 log-file-size-limit 选项用于设置日志文件的最大大小（单位：MB）。您也可以在 General → Log 中进行设置。如果未设置，则仍适用旧有限制：Mac 上为 200 MB，iOS 上为 50 MB。

### 修复
- 修复了一个问题：当外部策略被直接用作另一策略的底层代理时，其进程不会自动启动。只有在执行延迟测试后，该进程才会启动。
- 修复了服务器在 304 或其他本应无响应体的响应后仍发送 body 时，请求返回 503 的问题（例如 ASUSWRT-Merlin 路由器）。
- 修复了当响应脚本和正文重写规则均匹配时，HTTP/2 响应中无正文（304、204 或对 HEAD 的响应）未被正确处理的问题。
- 修复了在未返回任何策略组的情况下，使用 WebView 引擎的脚本中 $surge.retestGroup 失败的问题。
- 修复了在分块请求体之后发送的流水线 HTTP/1 请求被作为该请求体的一部分转发，而非作为独立请求处理的问题。
- 修复了 HTTP/1 连接复用和关闭过程中的几个边缘情况，这些问题可能导致响应混淆或连接保持打开状态。
- 修复了自 6.8.0 以来，通过 HTTP/2 发出的 HEAD、204 和 304 请求在某些服务器上失败的问题。
- 修复了 no-resolve 和 extended-matching 未应用于嵌套在 [Ruleset] 部分中的规则集的问题。
- 修复了在某些发送格式错误 AAAA 响应的运营商 DNS 服务器上，DNS 查找等待超时的故障。
- 修复了 Enhanced Mode 中 PROCESS-NAME 规则遗漏短时进程的问题。
- 修复了一个与入站 Tailscale 和 WireGuard 连接相关的崩溃问题。
- 修复了当对等方将其自身的 Tailscale 流量重新发回 tailnet 时出现的 Tailscale 路由环路问题，例如，某个使用本设备作为出口节点或子网路由器的 tsnet 程序。Surge 曾误将环路流量识别为直接路径并持续使用，导致其延迟达到 DERP 级别。
- 修复了 Surge Ponte 在某些局域网配置中反复断开 WAN 连接的问题。
- 修复了 HTTP/2 伪标头以空名称导出到 HAR 的问题。
- 修复了请求说明中列出的、与 AND、OR 或 NOT 分支不匹配的子规则的问题。
- 修复了在缓慢或丢包的网络环境下，通过 Hysteria 2 策略组生成的响应有时会丢失最后部分的问题，这种情况最常出现在以关闭连接结尾的 HTTP/1.1 响应中。
- 修复了一个问题：带有手动覆盖的路由负载均衡组，其评分被计算为各选项的平均值，而非被覆盖的策略，导致包含该组的策略组可能选择了与实际路由不同的路径。
- 修复了当 Surge 读取路由表期间路由表大小发生变化（例如 iPhone 通过 USB 连接时）导致 DIRECT 请求因“无出站接口”而失败的问题。现在，当读取失败时，Surge 会保留当前的主用接口。
- 修复了在静态 IPv4 配置下，当网络变更期间默认路由短暂消失后，主 IPv4 接口保持为空的问题。Surge 现在会监控默认路由的变化并重新进行检查。
- 修复了在某个网络接口拥有 IPv4 地址但没有默认路由时，Surge 每 30 秒重新加载网络状态的问题。
- 修复了 Snell、Vector 和 Ponte 服务器在 NAT64 网络上通过 DIRECT 发送的每个 IPv4 UDP 数据报均被丢弃的问题。
- 修复了在流被中止时 HTTP/2 连接逐渐丢失接收窗口的问题，该问题最终可能导致连接停滞。
- 修复了 WireGuard 策略中 listen-port 在配置文件变更后被替换但未能重新启动的问题，因为旧会话仍占用了该端口。

## [#449](https://t.me/SurgeTestFlightFeed/449) · 2026-11-11

### 改进
- Snell v6：UDP 数据现在会在隧道命令后立即发送，无需等待服务器响应的一次往返。通过 Snell v6 建立 QUIC 连接的速度会明显更快；这需要 v6 服务器。
- Ponte：当设备在远程通道重启期间捕获了其记录后，该设备不会再卡在“仅 LAN 模式”中。Surge 在放弃前会刷新设备列表，并且错误消息现在会解释其原因。
- 当 SOCKS5 代理拒绝连接时，Surge 现在会显示服务器给出的原因（例如 connection refused 或 host unreachable），不再只显示“invalid response”错误。
- 解决了在同一设备上使用多个用户或多个操作系统时需要反复激活的问题。有关具体方法，请参阅知识库的授权 FAQ。
- Tailscale：管理控制台不再为运行 Surge 的设备显示更新警告。
- Tailscale：现在，若 DERP 连接在 120 秒内未收到任何数据，则会被视为已断开并重新连接。此前，静默丢失的连接可能会导致所有转发的流量中断，直到 Surge 重启。
- Tailscale：现在，Surge 能够找到一条直达本地网络中 NAT 后端对等节点（例如 Docker 桥接网络上的 tailscaled 容器）的路径。此前，这类对等节点会持续使用 DERP 或遥远的对等节点中继。
- Tailscale 和 WireGuard：现在，从此设备到其自身隧道地址或 MagicDNS 名称的连接可以成功到达设备本身。此前，这些连接会超时。
- Tailscale：新的网页登录功能现已即时生效。此前，在 Surge 重启之前，该策略会因旧登录信息或登录信息缺失而持续失败。
- Tailscale：被拒绝或过期的授权密钥现在会作为警告提示。它也会显示在“事件”和“日志簿”中，并会一直保留，直到节点被重新授权。此前，它只会显示一条 10 秒后就会消失的通知。
- WireGuard 和 Tailscale：更改 [Proxy] 或 [Proxy Group] 后，将不再重启每个 WireGuard 和 Tailscale 会话。如果某个会话的策略行及其自身部分均未更改，则该会话将得以保留，从而确保通过它的连接仍能正常工作。此前，通过 tailnet 进行的更改（例如来自另一台设备上的 surge-cli 或 MCP 的更改）会中断其自身的响应。
- Hysteria 2：现在，大于服务器允许大小的 UDP 数据报在发送时总会拆分成多个片段，即使它们设置了“不分片”（Don't Fragment）标志。由于 v2.6.4，官方的 Hysteria 2 服务器将数据报限制在约 1,200 字节。此前，Surge 会拒绝带有“不分片”标志的更大数据报，这会导致 Steam 数据报中继（CS2 匹配失败）以及隧道内的 QUIC 连接中断。现在，每个数据报还可以多承载约 45 字节的数据。
- Ponte：当两端具有相同的虚拟机桥接地址时（OrbStack、Parallels、UTM 及类似情况），设备不再被错误地视为处于同一局域网。
- Ponte：当 LAN 连接尝试失败时，Surge 现在会回退到 Internet 模式并刷新设备记录，而不会因 ping 超时而终止。
- Ponte：日志中的设备记录现在不再包含 PSK 或控制器密钥。
- 流量统计：Tailscale MagicDNS 主机（*.[ts.net](http://ts.net/)）现在会以其完整主机名显示，而不会全部归组到 [http://ts.net](http://ts.net/) 下。现在，每个主机的报告会将相同主机的条目进行汇总，而不再是仅保留其中一条。
- HTTP 代理：Proxy-Authorization 标头将不再转发到上游服务器。它包含的是 Surge 自身代理的凭据。
- HTTP/2：格式错误的请求现在只会重置其自身的流，而不会重置整个连接。
- HTTP/2：当上游服务器在响应中途关闭连接时，Surge 现在会将其报告为“截断”，而非“完整响应”。
- $httpClient：URL 中经过百分比编码的用户名和密码现在会在作为基础身份验证发送之前被解码。无法解码的响应正文现在会报告为错误。
- 移除了规则集和域集上 1,000,000 条目的限制。
- socks5-listen 现在支持与 http-listen 相同的 username:password@ 身份验证方式。

## [#448](https://t.me/SurgeTestFlightFeed/448) · 2026-11-11

### 使用您自己的证书进行 MITM
- 新增 [MITM] server-certificates = <hostname>:<keystore item>, ... 功能，可使用您自己的证书（例如受公众信任的证书）来解密列出的主机，而不再使用 Surge 的 CA 签发的证书。此功能可用于检查那些固定了其证书或拒绝用户安装的 CA 的应用程序。
- 此列表中的主机即使未配置 CA 也能正常工作。
- 第一个匹配项生效。如果其 PKCS #12 项目无法加载，Surge 将回退到由 CA 签发的证书。
- 项目中的中间证书将一并发送。
- Surge 记录了一个证书未覆盖的主机，并将无效条目显示为配置文件警告。

#### 仪表板
- “流量统计”选项卡的底部工具栏中新增了一个“细分”按钮。选择“主机”或“策略”，即可展开每一行，查看其策略或主机，并按今天、本月和上月的情况进行排序。

## [#447](https://t.me/SurgeTestFlightFeed/447) · 2026-11-11

### MCP 服务器
- 现在，HTTP API 可以在 /v1/mcp 提供 Model Context Protocol 端点，因此像 Claude Code 这样的 AI 智能体可以检查和控制 Surge。您可以通过 HTTP API 设置中的 MCP Server 开关，或设置 http-api-mcp = true 来启用此功能。默认情况下，该功能处于关闭状态。

#### HTTP API
- HTTP API 的 GET /v1/policies 现在接受 include_external=true 查询参数。响应将包含一个额外的 external-policies 字段，其中列出了从外部策略组（policy-path）加载的策略。每个条目都包含策略名称、所属策略组以及一个标识符。由于无法通过名称引用外部策略，因此请将此标识符作为 $httpClient 的策略选项传递，以便通过该策略发送请求。
- 现在可以使用 GET / POST /v1/capture/filters 读取和更改捕获过滤器。

#### Surge CLI
- 新增 surge-cli 配置文件章节命令，用于读取或替换单个配置文件章节。使用 #!include 时，更改将应用于包含该章节的文件，而其他文件则保持不变。
- 新增 surge-cli capture-filter 命令，用于读取和更改捕获过滤器。
- 新的 surge-cli dump traffic-stat-records <today|this-month|last-month> 命令会返回某一时间段的流量统计数据，数据已按主机、策略和接口进行合并。同样的数据也可通过 MCP 获取。
- surge-cli module list 现在会显示每个模块的详细信息：其类型、版本、文件修改时间，以及它为每个部分添加的行数（或显示其加载失败的原因）。新的 surge-cli module show <name> 命令还会显示每个 #! 标头字段、声明的参数名称以及模块文本。该功能也通过 MCP（list_modules 和新的 get_module）以及 HTTP API（GET /v1/modules 和新的 /v1/modules/detail）提供。
- surge-cli 的规则匹配和规则解释功能现在会显示匹配的规则来自何处：配置文件及其行号，或添加该规则的模块。对于 RULE-SET 或 DOMAIN-SET，它们还会显示规则集内部匹配的具体条目。相同的字段也会通过 MCP 和 HTTP API 返回。

#### Surge VM
- 网关设置中新增“禁用 UDP 快速路径”选项。当设备在短时间内创建大量 UDP 流时（例如 P2P 下载），Surge VM 通常会将这些流移至 UDP 快速路径。该路径会直接在 L3 层转发 UDP 流量，而不会应用任何规则。启用此选项后，所有设备都将不再使用快速路径，从而确保所有 UDP 流量始终经过您的规则。

#### 已保存的捕获会话
- 现在，已保存到磁盘的 HTTP 捕获会话可以通过 surge-cli、MCP 和 HTTP API 读取。此前，只有内存中的最近请求可供访问。每个通道都可以列出会话、分页浏览会话中的请求（并应用筛选器），以及读取请求和响应正文：
  - surge-cli capture-session list | dump <session> | data <session> <key> <request|response>
  - MCP 工具 list_capture_sessions、list_capture_session_requests 和 get_capture_session_body
  - GET /v1/capture/sessions、/v1/capture/sessions/requests 和 /v1/capture/sessions/data
- 新的捕获会话现在还会记录其开始和结束时间、限制、过滤器以及结束原因。

## [#446](https://t.me/SurgeTestFlightFeed/446) · 2026-11-11

Surge Mac 6.11.0 现已正式发布。

### SOCKS5 UDP
- 内置的 SOCKS5 代理服务器现在支持 UDP ASSOCIATE。SOCKS5 客户端可以通过 Surge 发送 UDP 流量，这些流量会像 TCP 流量一样，经过您的规则和策略。每个关联的第一个数据报会根据您的规则进行匹配，后续数据报则使用相同的策略。

### 避免在自动策略组中
- 现在，您可以将某项策略标记为“已避免”。当某项策略通过了延迟测试但在实际使用中表现不佳（例如带宽较低）时，可使用此功能。只要其他成员可用，自动策略组（url-test、fallback、load-balance 和 smart）就会跳过“已避免”的策略。如果别无选择，系统仍会使用“已避免”的策略。
- 已选择和子网分组的组、临时覆盖项以及直接引用的策略组不受影响。
- 与覆盖项一样，当 Surge 重启时，标记会被清除。
- 新增 surge-cli policy-avoid list|add|remove|clear 命令、MCP 工具 set_policy_avoidance 以及 HTTP API GET / POST /v1/policies/avoided。策略组现在会报告自动策略组的已规避成员。

### 自适应 QUIC 阻断
- 为代理策略新增了 block-quic=adaptive 选项。Surge 会先阻止 QUIC，使应用回退到基于 TCP 的 HTTPS。仅当应用显示无法回退时，才允许对某个主机使用 QUIC，例如仅支持 QUIC 的应用：在 0.5 秒内未出现 TCP 连接，且应用会在 3 秒内尝试通过 QUIC 重试。该重试会立即成功。若在这 3 秒内出现 TCP 连接，则表示应用可以回退，QUIC 仍会被阻止。结果会按主机分别记忆。
- block-quic=auto 现在对除 DIRECT 外的所有策略都使用自适应模式，因此仅使用 QUIC 的应用仍可正常通过代理工作。无法转发 UDP 的策略仍会阻止 QUIC。
- QUIC 主机名识别现在支持跨多个数据包的 TLS ClientHello；采用后量子密钥交换的新浏览器常见这种情况。同时支持 QUIC v2 和 draft-29。规则、MITM 与请求记录现在能识别更多 QUIC 连接的主机名。
- 端口 443 上的 DTLS、WireGuard、STUN 及其他非 QUIC 的 UDP 流量将不再被视为 QUIC，因此 block-quic 不再对其生效。

### Tailscale 和 WireGuard 的入站连接
现在，Surge 不仅可以发送出站流量，还可以接受通过 Tailscale 和 WireGuard 传入的连接。入站请求的处理方式与其他请求相同：它们会经过您的规则集和策略组，并显示在请求列表中。

### Tailscale
- allow-peer-access = true：您 tailnet 网络中的其他设备可以通过该设备的 tailnet 地址连接到此设备。例如，它们可以使用 Surge 的 HTTP/SOCKS5 代理或运行在此设备上的其他服务。（旧参数 accept-incoming 已被重命名，但为了兼容仍会读取。）
- advertise-exit-node = true：将此设备提供为出口节点。选择该设备的其他 tailnet 设备会将其所有互联网流量通过 Surge 的规则发送。
- advertise-routes = [192.168.1.0/24](http://192.168.1.0/24), ...: 将此设备作为所列网络的子网路由器提供。
- 退出节点和子网路由在您于 Tailscale 管理控制台中批准后生效。

### WireGuard
- allow-peer-access = true：对端可以通过现有隧道与此设备建立连接。
- listen-port = 51820：Surge 充当 WireGuard 服务器，手机、笔记本电脑和其他客户端都可以连接到该服务器。对等端可以省略端点；Surge 会在客户端连接时获知其地址，并在地址变更时保持同步。
- 客户端可以将 Surge 的隧道地址设置为自己的 DNS 服务器，Surge 的 DNS 将响应其查询。

注意：Surge 不会将您的 Tailscale 访问控制策略应用于入站连接。请使用 SRC-IP 等规则来限制哪些人可以访问哪些目标。

### 对等访问直通
- 现已内置对 Apple 屏幕共享的特殊处理，无需任何配置即可使用。

### 规则集编辑器
- 现在，您可以通过“启用/停用”滑动操作来停用规则集中的单个规则。停用的规则将以注释行的形式保存。

## [#445](https://t.me/SurgeTestFlightFeed/445) · 2026-11-11

### 已知问题：Surge 在 iOS 上可能会意外停止 27.3 测试版 1

在 iOS 27.3 测试版 1 中，系统的 Network Extension 框架存在一个问题，可能导致 Surge 意外停止。该问题源于 iOS 本身，我们正在等待 Apple 在后续更新中修复此问题。

与此同时，下一版 Surge beta 将在出现这种情况时为您提供更清晰的信息。如果 Surge 被停止，您将收到一条通知，其中会说明确切原因，以便您能够区分系统发起的停止与其他问题。

如果您依赖 Surge 始终保持连接，我们建议您在 Apple 发布修复程序前，继续使用 iOS 27.2。

## [#444](https://t.me/SurgeTestFlightFeed/444) · 2026-11-10

### Beta 更新

#### Surge 引擎

##### Surge CLI

- `surge-cli dump` 现在支持 `dns-lookup-times`、`traffic-stat-hourly` 和 `policy-usage`，并能为它们显示可读的输出。之前，这些转储文件仅能与 `--raw` 配合使用。

##### 模块

- 现在，更新模块或从同一 URL 重新安装模块时，其脚本和规则集会立即重新下载。此前，这些资源的新版本会等到其更新间隔才会下载。

##### 改进

- 清理后的配置文件现在会隐藏 `[General]` 中的凭据：`http-api` 和 `external-controller-access` 键、`http-listen` 和 `socks5-listen` 凭据，以及 `wifi-access-http-auth`。这涵盖了 `GET /v1/profiles/current?sensitive=0`、控制器的配置文件转储和诊断日志存档。监听地址仍保持可读，这些行末尾的注释则被移除。
- 现在，来自 surge-cli、HTTP API 或 MCP 的 `set` 命令会拒绝无法分配的路径键并返回错误。该调用中的任何值都不会被应用。

##### 修复

- 修复了 Snell、Vector 和 Ponte 服务器在 NAT64 网络上通过 DIRECT 发送的每个 IPv4 UDP 数据报均被丢弃的问题。
- 修复了在流被中止时 HTTP/2 连接逐渐丢失接收窗口的问题，该问题最终可能导致连接停滞。
- 修复了一个 WireGuard 策略组的问题：在替换它的配置文件更改后，`listen-port` 未能重新启动，因为旧会话仍占用了该端口。

#### Surge iOS

##### 开始切换样式

- “自定义主页”现已新增“启动切换”版块，提供三种样式，即使 Surge 已停止运行，您仍可打开该主页。
  - 始终展开（默认）：滑块卡片在您滚动时会收缩成一个胶囊状。
  - 运行期间折叠：卡片在停止时会折叠。一旦您滑动以开始，它就会在标题旁边变成一个胶囊，并在 Surge 停止时恢复为卡片。
  - 始终折叠：始终显示胶囊。停止时显示为蓝色的“开始”按钮。

##### 策略组卡片

- 自定义卡片背景现已回归，并提供多种样式：63 种预设图形、系统颜色、取色器或“无”。带有背景的卡片将使用浅色文本。
- 卡片自定义工作表中新增了一个“全局”部分，用于设置每张折叠卡片显示延迟的方式：显示带延迟信息的圆点、仅显示圆点，或不显示任何内容。

其他细节修复与优化。

## [#443](https://t.me/SurgeTestFlightFeed/443) · 2026-11-09

### Beta 更新

#### Surge 引擎

##### 外部控制

- `module list` 现在会返回每个模块的详细信息：其类型、每个 `#!` 标头字段、声明的参数名称、文件修改时间，以及使用存储的参数加载后每个部分中的有效行（或加载错误）。新的 `module show <name>` 命令还包含模块的文本。适用于 surge-cli、MCP（`list_modules` 和新的 `get_module`）以及 HTTP API（`GET /v1/modules` 和新的 `/v1/modules/detail`）。
- `rule match` 和 `rule explain` 现在会返回匹配规则的来源：配置文件和行号，或添加该规则的模块。对于 RULE-SET 或 DOMAIN-SET，它们还会返回规则集内实际匹配的那一项，并从最内层的规则集开始。

##### 改进

- WireGuard 和 Tailscale：更改 [Proxy] 或 [Proxy Group] 后，将不再重建所有 WireGuard 和 Tailscale 会话。当某个会话的策略行及其自身部分保持不变时，该会话将被保留，因此通过它建立的连接仍可继续工作。此前，在 tailnet 上进行的更改（例如，由对等节点上的控制器发起的更改）会中断其自身的响应。
- Tailscale：被拒绝或过期的授权密钥现在会作为警告提示。它也会显示在“事件”和“日志簿”中，并会一直保留，直到节点被重新授权。此前，它只会显示一条 10 秒后就会消失的通知。

##### 修复

- 请求日志中不再列出未匹配的 AND/OR/NOT 分支中的子规则。

##### Surge iOS

继续优化和调整 UI 细节。

## [#442](https://t.me/SurgeTestFlightFeed/442) · 2026-11-08

### Beta 更新

#### Surge 引擎

##### 改进

- Hysteria 2：超大 UDP 数据包现已被分片
- Tailscale：新的网页登录功能现已即时生效。此前，在 Surge 重启之前，该策略会因旧登录信息或登录信息缺失而持续失败。

##### 修复

- Tailscale：修复了一个路由环路问题，当对等方将其自身的 Tailscale 流量重新发送回 tailnet 时（例如，使用此设备作为出口节点或子网路由器的 tsnet 程序），就会触发该问题。Surge 曾误将环路流量识别为直接路径，并持续使用它，导致延迟达到 DERP 级别。

##### Surge iOS

继续进行重大的用户界面转换与优化。

##### 类别

- 配置、策略组和模块现在共享一个类别栏。
- “配置收藏夹”星标仅在您通过“更多”→“外观”→“收藏夹卡片”设置了收藏夹卡片后才会出现。它是类别栏上的第一个项目。
- 现在，左右滑动这些页面时，页面会随着手势滑动，而不再只是执行简单的手势操作。

##### 模块

- 模块页面现在一次只显示一个类别，类别由类别栏选择。搜索功能仍然涵盖所有类别。

##### 快捷方式

- 新增的“运行 Surge CLI 命令”操作可运行一个 surge-cli 命令并返回其输出，也可选择以原始 JSON 格式返回。不支持会持续流式输出的命令，例如 `watch` 和 `diagnostics`。
- 新增的“调用 HTTP API”操作会向正在运行的 Surge 发送 GET 或 POST 请求，并返回响应。无需配置 `http-api`。

请注意，此版本包含一些用于内部数据的迁移逻辑。一旦更新到新版本，如果您回退到旧版本，部分统计数据可能会丢失。

## [#441](https://t.me/SurgeTestFlightFeed/441) · 2026-11-08

### Hysteria 2：超大 UDP 数据包现已被分片

自 v2.6.4 以来，官方的 Hysteria 2 服务器已将 QUIC 数据报限制为 1,200 字节，无论网络 MTU 如何。该协议通过分片来处理更大的数据包。

然而，由于 Surge 严格遵循 IP DF 标志，它会通过返回 ICMP Packet Too Big 消息来拒绝设置了 DF 标志的大 UDP 数据包。但由于 Hysteria 2 的每个数据包最大有效载荷大小过低，某些 UDP 服务完全无法使用。

从 Beta 更新开始，Surge 会通过 Hysteria 2 策略组，利用分片技术转发任意大小的 UDP 数据包。此前，被标记为“不分片”（DF）且大小超过约 1130 字节的数据包会被丢弃。

## [#439](https://t.me/SurgeTestFlightFeed/439) · 2026-11-07

### Surge iOS 6 TestFlight 更新

此 Beta 版本包含对视觉样式和交互的大量更新。我们将在整个 Beta 测试期间持续优化和迭代设计和交互。敬请期待。

请访问网站了解更多信息：[https://nssurge.com/surge-ios-6](https://nssurge.com/surge-ios-6)

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

代码、版本号和链接会先换为占位符；配置键、命令名等标识符由提示规则要求原样保留。译文通过格式与占位符校验后才使用。

当前窗口内没有待译条目。
