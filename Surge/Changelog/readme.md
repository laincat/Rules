# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#453](https://t.me/SurgeTestFlightFeed/453) · 2026-11-11

- 修复了通过 SSH 策略组上传的文件在会话重新加密后损坏的问题，该问题在传输量达到 1 GB 后发生。
- 修复了 Surge 两次关闭通道后，SSH 服务器断开整个会话及其上所有隧道的问题。
- 修复了 Envoy 中的几个 MASQUE 问题：
  - The first packet to each new UDP destination was lost.
  - UDP to new destinations failed once about 100 were open on one connection.
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

- Surge now sends a notification whenever iOS stops the VPN for any reason other than you stopping it. Before, it only did so when the VPN configuration was disabled.
- The Home tab style None is back. With None there is no Home tab, and the Configure page's header starts and stops Surge.
- The proxy editor has a new field for TrustTunnel's client random auth key.

#### 修复

- 修复了在卡片菜单仍在关闭时滑动类别后，策略组卡片消失以及卡片不再响应点击的问题。
- 修复了在行菜单仍在关闭时进行滑动操作，导致某个模块自动开启或关闭的问题。
- 修复了在短暂滑动后页面回弹期间，于“配置”页面滑动时无任何反应的问题。
- 修复了展开后的策略组卡片中，磁贴和滚动指示器超出其圆角范围的问题。
- 修复了“配置”页面在重新启动前仍保留先前启动切换器样式的标题的问题。
- Traffic statistics that were already stored as negative values (from the AnyTLS bug) are now shown as zero.

## [#452](https://t.me/SurgeTestFlightFeed/452) · 2026-11-11

### Beta 更新

#### Surge 引擎

##### AI 驱动型测试平台

We have built a fully automated, AI-powered testing platform for Surge Engine. The platform continuously evaluates compatibility and performance against the latest official client implementations of all supported proxy protocols, helping ensure that Surge matches or exceeds their performance.

未来，对 Surge Engine 的每一次更改都将通过此平台进行验证，以便及早发现兼容性问题及其他错误，防止性能退化，并确保在每次更新后都能保持一致的可靠性。

##### Performance

- 修复了大量在特定配置或环境下可能出现的性能问题，尤其是在代理链组合下的性能问题。

#### Proxy Protocol

##### VLESS

- New `vless` proxy type. It supports RAW or WebSocket transport, with no TLS, TLS or REALITY. It also supports the `xtls-rprx-vision` flow and the gRPC transport over TLS or REALITY.
- UDP is always sent as XUDP.

##### TrustTunnel

- TrustTunnel 服务器新增 `client-random-auth-key` 参数（适用于 v1.3.0-beta.2 及更高版本），该参数仅接受能够证明其持有共享密钥的客户端。此功能在 HTTP/2 和 HTTP/3 模式下均可使用。
- The parameter requires an SNI, and it is masked in sanitized profiles.

##### Profile Reload

- 更改 `[Proxy]`、`[Proxy Group]` 或 `[Keystore]` 已不再中断 SSH、HTTP/2 CONNECT、MASQUE、TUIC 和 Hysteria 2 策略中仍在传输的连接，前提是这些策略自身的定义未变。现在，它们的共享连接将被保留，正如 WireGuard 和 Tailscale 会话早已实现的那样。

##### 更快的故障检测

- Wrong credentials now fail right away instead of after the 10-second setup timeout. This covers:
  - HTTP 和 HTTPS (407 或 401)
  - SOCKS5 (authentication rejected, or no acceptable method)
  - Hysteria 2
  - an SSH host key that does not match `server-fingerprint` (the error names the key the server offered)
  - ShadowTLS v3
- When a server closes the connection during setup, for example TrustTunnel with a wrong key, Surge now retries once and then fails, instead of retrying until the timeout.

##### 修复

## [#451](https://t.me/SurgeTestFlightFeed/451) · 2026-11-11

### VLESS and REALITY Support in Surge Beta

The latest Surge beta adds support for the VLESS protocol, including connections secured with REALITY. Configuration is currently available through text-based profiles only; see [https://manual.nssurge.com/policies/vless.html](https://manual.nssurge.com/policies/vless.html) for syntax and supported options.

#### Why We're Adding VLESS and REALITY

在人工智能让编写代码变得前所未有的简单这个时代，实现一个功能早已不再是难事。但真正没有变得更便宜的，是随之而来的所有工作：我们每增加一个协议，就意味着承担了一项长期的维护、安全和支持承诺，而这也会塑造 Surge 的核心理念。正因如此，我们在决定将哪些内容纳入 Surge 时，反而变得更加审慎，而非更草率。我们曾对 VLESS 和 REALITY 犹豫不决，从来不是因为无法实现它们，而是因为不确定是否应该实现它们。

We have reservations about aspects of their technical design. At the same time, many of our users need these technologies, and we know some have turned to unofficial modified builds of Surge to access them, which carries real security risks. In the end, we decided that a supported, trustworthy implementation serves our users better than leaving them without one.

#### 致 Surge iOS 用户的提醒

正如我们先前所宣布的，Surge iOS 上的协议支持不再需要有效的订阅。所有受支持的协议（包括 VLESS 和 REALITY）均可免费提供给所有 Surge iOS 用户。

## [#450](https://t.me/SurgeTestFlightFeed/450) · 2026-11-11

- Profile errors now explain why a line is invalid, not only where it is.
- New log-file-size-limit option in [General] sets the maximum log file size in MB. You can also set it in General → Log. When it is not set, the old limits still apply: 200 MB on Mac and 50 MB on iOS.

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
- WireGuard and Tailscale: changing [Proxy] or [Proxy Group] no longer restarts every WireGuard and Tailscale session. A session is kept when its policy line and its own section are unchanged, so connections through it keep working. Before, a change made over the tailnet, such as from surge-cli or MCP on another device, cut off its own reply.
- Hysteria 2：现在，大于服务器允许大小的 UDP 数据报在发送时总会拆分成多个片段，即使它们设置了“不分片”（Don't Fragment）标志。由于 v2.6.4，官方的 Hysteria 2 服务器将数据报限制在约 1,200 字节。此前，Surge 会拒绝带有“不分片”标志的更大数据报，这会导致 Steam 数据报中继（CS2 匹配失败）以及隧道内的 QUIC 连接中断。现在，每个数据报还可以多承载约 45 字节的数据。
- Ponte：当两端具有相同的虚拟机桥接地址时（OrbStack、Parallels、UTM 及类似情况），设备不再被错误地视为处于同一局域网。
- Ponte：当 LAN 连接尝试失败时，Surge 现在会回退到 Internet 模式并刷新设备记录，而不会因 ping 超时而终止。
- Ponte：日志中的设备记录现在不再包含 PSK 或控制器密钥。
- Traffic statistics: Tailscale MagicDNS hosts (*.[ts.net](http://ts.net/)) are now shown by their full hostname instead of all being grouped under [http://ts.net](http://ts.net/). The per-host report now adds up entries for the same host instead of keeping only one of them.
- HTTP 代理：Proxy-Authorization 标头将不再转发到上游服务器。它包含的是 Surge 自身代理的凭据。
- HTTP/2：格式错误的请求现在只会重置其自身的流，而不会重置整个连接。
- HTTP/2：当上游服务器在响应中途关闭连接时，Surge 现在会将其报告为“截断”，而非“完整响应”。
- $httpClient：URL 中经过百分比编码的用户名和密码现在会在作为基础身份验证发送之前被解码。无法解码的响应正文现在会报告为错误。
- 移除了规则集和域集上 1,000,000 条目的限制。
- socks5-listen now supports username:password@ authentication, the same way as http-listen.

## [#448](https://t.me/SurgeTestFlightFeed/448) · 2026-11-11

### 使用您自己的证书进行 MITM
- New [MITM] server-certificates = <hostname>:<keystore item>, ... decrypts the listed hosts with your own certificate, such as a publicly trusted one, instead of one signed by Surge's CA. Use it to inspect apps that pin their certificate or reject user-installed CAs.
- 此列表中的主机即使未配置 CA 也能正常工作。
- 第一个匹配项生效。如果其 PKCS #12 项目无法加载，Surge 将回退到由 CA 签发的证书。
- 项目中的中间证书将一并发送。
- Surge 记录了一个证书未覆盖的主机，并将无效条目显示为配置文件警告。

#### 仪表板
- “流量统计”选项卡的底部工具栏中新增了一个“细分”按钮。选择“主机”或“策略”，即可展开每一行，查看其策略或主机，并按今天、本月和上月的情况进行排序。

## [#447](https://t.me/SurgeTestFlightFeed/447) · 2026-11-11

### MCP 服务器
- The HTTP API can now serve a Model Context Protocol endpoint at /v1/mcp, so AI agents such as Claude Code can inspect and control Surge. Enable it with the MCP Server switch in the HTTP API settings, or with http-api-mcp = true. It is off by default.

#### HTTP API
- GET /v1/policies of the HTTP API now accepts the include_external=true query parameter. The response then contains an additional external-policies field that lists the policies loaded from external policy groups (policy-path). Each entry includes the policy name, the group it belongs to, and an identifier. Pass the identifier as the policy option of $httpClient to send a request through that policy, since external policies cannot be referenced by name.
- 现在可以使用 GET / POST /v1/capture/filters 读取和更改捕获过滤器。

#### Surge CLI
- New surge-cli profile section command to read or replace a single profile section. With #!include, the change goes into the file that holds the section and other files stay untouched.
- New surge-cli capture-filter command to read and change capture filters.
- New surge-cli dump traffic-stat-records <today|this-month|last-month> returns one period's traffic statistics, merged by host, policy and interface. The same data is available through MCP.
- surge-cli module list now shows details for each module: its type, version, file modification time, and the number of lines it adds to each section (or why it failed to load). New surge-cli module show <name> also shows every #! header field, the declared argument names and the module text. Also available through MCP (list_modules and the new get_module) and the HTTP API (GET /v1/modules and the new /v1/modules/detail).
- surge-cli rule match and rule explain now show where the matched rule comes from: the profile file and line, or the module that added it. For a RULE-SET or DOMAIN-SET, they also show the entry inside the set that matched. The same fields are returned through MCP and the HTTP API.

#### Surge VM
- New “Disable UDP Fast Path” option in the gateway settings. When a device creates many UDP flows in a short time (for example, P2P downloads), Surge VM normally moves it to the UDP Fast Path. That path forwards its UDP traffic directly at L3 without applying rules. Turn this option on to stop using the fast path for all devices, so all UDP traffic always goes through your rules.

#### Saved Capture Session
- 现在，已保存到磁盘的 HTTP 捕获会话可以通过 surge-cli、MCP 和 HTTP API 读取。此前，只有内存中的最近请求可供访问。每个通道都可以列出会话、分页浏览会话中的请求（并应用筛选器），以及读取请求和响应正文：
  - surge-cli capture-session list | dump <session> | data <session> <key> <request|response>
  - MCP 工具 list_capture_sessions、list_capture_session_requests 和 get_capture_session_body
  - GET /v1/capture/sessions、/v1/capture/sessions/requests 和 /v1/capture/sessions/data
- 新的捕获会话现在还会记录其开始和结束时间、限制、过滤器以及结束原因。

## [#446](https://t.me/SurgeTestFlightFeed/446) · 2026-11-11

Surge Mac 6.11.0 has now been officially released.

### SOCKS5 UDP
- 内置的 SOCKS5 代理服务器现在支持 UDP ASSOCIATE。SOCKS5 客户端可以通过 Surge 发送 UDP 流量，这些流量会像 TCP 流量一样，经过您的规则和策略。每个关联的第一个数据报会根据您的规则进行匹配，后续数据报则使用相同的策略。

### 避免在自动策略组中
- You can now mark a policy as avoided. Use this when a policy passes latency tests but performs poorly in practice, for example with low bandwidth. Automatic groups (url-test, fallback, load-balance and smart) skip an avoided policy as long as any other member is usable. If nothing else is left, the avoided policy is still used.
- 已选择和子网分组的组、临时覆盖项以及直接引用的策略组不受影响。
- 与覆盖项一样，当 Surge 重启时，标记会被清除。
- New surge-cli policy-avoid list|add|remove|clear, the MCP tool set_policy_avoidance and the HTTP API GET / POST /v1/policies/avoided. policy-group now reports the avoided members of automatic groups.

### 自适应 QUIC 阻断
- 为代理策略新增了 block-quic=adaptive 选项。Surge 会先阻止 QUIC，使应用回退到基于 TCP 的 HTTPS。仅当应用显示无法回退时，才允许对某个主机使用 QUIC，例如仅支持 QUIC 的应用：在 0.5 秒内未出现 TCP 连接，且应用会在 3 秒内尝试通过 QUIC 重试。该重试会立即成功。若在这 3 秒内出现 TCP 连接，则表示应用可以回退，QUIC 仍会被阻止。结果会按主机分别记忆。
- block-quic=auto now uses adaptive mode for every policy except DIRECT, so QUIC-only apps keep working through proxies. Policies that cannot relay UDP still block QUIC.
- QUIC 主机名识别现在支持跨多个数据包的 TLS ClientHello；采用后量子密钥交换的新浏览器常见这种情况。同时支持 QUIC v2 和 draft-29。规则、MITM 与请求记录现在能识别更多 QUIC 连接的主机名。
- 端口 443 上的 DTLS、WireGuard、STUN 及其他非 QUIC 的 UDP 流量将不再被视为 QUIC，因此 block-quic 不再对其生效。

### Tailscale 和 WireGuard 的入站连接
现在，Surge 不仅可以发送出站流量，还可以接受通过 Tailscale 和 WireGuard 传入的连接。入站请求的处理方式与其他请求相同：它们会经过您的规则集和策略组，并显示在请求列表中。

### Tailscale
- allow-peer-access = true: other devices on your tailnet can connect to this device through its tailnet address. For example, they can use Surge's HTTP/SOCKS5 proxy or other services running on this device. (The old parameter accept-incoming has been renamed, but it will still be read for compatibility.)
- advertise-exit-node = true: offer this device as an exit node. Other tailnet devices that select it send all their internet traffic through Surge's rules.
- advertise-routes = [192.168.1.0/24](http://192.168.1.0/24), ...: offer this device as a subnet router for the listed networks.
- 退出节点和子网路由在您于 Tailscale 管理控制台中批准后生效。

### WireGuard
- allow-peer-access = true: the peer side can open connections to this device through an existing tunnel.
- listen-port = 51820: Surge acts as a WireGuard server that phones, laptops, and other clients can connect to. A peer can leave out endpoint; Surge learns the client's address when it connects and keeps up when the address changes.
- 客户端可以将 Surge 的隧道地址设置为自己的 DNS 服务器，Surge 的 DNS 将响应其查询。

Note: Surge does not apply your Tailscale access control policy to incoming connections. Use rules such as SRC-IP to limit who can reach which destination.

### 对等访问直通
- Special handling for Apple Screen Sharing is now built in and works without any configuration.

### 规则集编辑器
- 现在，您可以通过“启用/停用”滑动操作来停用规则集中的单个规则。停用的规则将以注释行的形式保存。

## [#445](https://t.me/SurgeTestFlightFeed/445) · 2026-11-11

### 已知问题：Surge 在 iOS 上可能会意外停止 27.3 测试版 1

On iOS 27.3 beta 1, a problem in the system’s Network Extension framework can cause Surge to stop unexpectedly. The problem is in iOS itself, and we are waiting for Apple to fix it in a future update.

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

## [#438](https://t.me/SurgeTestFlightFeed/438) · 2026-11-05

### Beta 更新

#### Surge 引擎

##### 避免在自动策略组中

- 现在，您可以将某项策略标记为“已避免”。当某项策略通过延迟测试但在实际使用中表现不佳（例如带宽较低）时，可使用此功能。只要自动策略组（`url-test`、`fallback`、`load-balance` 和 `smart`）中的其他任何成员均可使用，该策略组就会跳过“已避免”的策略。如果别无选择，仍会使用“已避免”的策略。
- 已选择和子网分组的组、临时覆盖项以及直接引用的策略组不受影响。
- 与覆盖项一样，当 Surge 重启时，标记会被清除。
- 新增 `surge-cli policy-avoid list|add|remove|clear`、MCP 工具 `set_policy_avoidance` 以及 HTTP API `GET` / `POST /v1/policies/avoided`。`policy-group` 现在会报告自动策略组中已避免的成员。

##### 使用您自己的证书进行 MITM

- 新的 `[MITM] server-certificates = <hostname>:<keystore item>, ...` 会使用您自己的证书（例如受公众信任的证书）来解密列出的主机，而不是使用 Surge 的 CA 签发的证书。您可以使用它来检查那些固定了其证书或拒绝用户安装的 CA 的应用程序。
- 此列表中的主机即使未配置 CA 也能正常工作。
- 第一个匹配项生效。如果其 PKCS #12 项目无法加载，Surge 将回退到由 CA 签发的证书。
- 项目中的中间证书将一并发送。
- Surge 记录了一个证书未覆盖的主机，并将无效条目显示为配置文件警告。

#### Surge Mac

##### 修复

- 修复了当 Surge 读取路由表期间路由表大小发生变化（例如 iPhone 通过 USB 连接时）导致 DIRECT 请求因“无出站接口”而失败的问题。现在，当读取失败时，Surge 会保留当前的主用接口。
- 修复了在静态 IPv4 配置下，当网络变更期间默认路由短暂消失后，主 IPv4 接口保持为空的问题。Surge 现在会监控默认路由的变化并重新进行检查。
- 修复了在某个网络接口拥有 IPv4 地址但没有默认路由时，Surge 每 30 秒重新加载网络状态的问题。

#### Surge iOS

##### 新功能

- MitM 设置页面为 `server-certificates` 提供了一个编辑器，其中包含一个密钥库选择器，以及一个用于显示证书是否覆盖主机名的提示信息。
- 密钥库：现在，每个项目都会在其所在行显示其存储位置（在配置文件中还是在钥匙串中）。轻点该行即可移动或删除它。
  - 项目按名称排序后显示在一个列表中，因此移动后的项目会保持在原位。
  - 现在添加项目时，您需要先输入内容。然后，系统会在与 PKCS #12 密码相同的提示框中，根据文件名或 SSH 密钥注释预填充名称。
- 请求详情现可为远程 iOS 和 tvOS 设备添加临时规则。
- 长按已添加的自定义图标集，即可复制其 URL、更新或删除它。

##### 改进

- 流量详情：现在长主机名会换行显示，流量数值会移至名称下方，而不会挤出行外。长按主机、策略或接口行即可复制其名称。

##### 修复

- 修复了应用图标选择器。

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

代码、版本号和链接会先换为占位符；配置键、命令名等标识符由提示规则要求原样保留。译文通过格式与占位符校验后才使用。

本轮仍有 **54** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `GET /v1/policies of the HTTP API now accepts the include_external=true query parameter. The response then contains an additional external-policies field that lists the policies loaded from external policy groups (policy-path). Each entry includes the policy name, the group it belongs to, and an identifier. Pass the identifier as the policy option of $httpClient to send a request through that policy, since external policies cannot be referenced by name.`
- `New [MITM] server-certificates = <hostname>:<keystore item>, ... decrypts the listed hosts with your own certificate, such as a publicly trusted one, instead of one signed by Surge's CA. Use it to inspect apps that pin their certificate or reject user-installed CAs.`
- `New `vless` proxy type. It supports RAW or WebSocket transport, with no TLS, TLS or REALITY. It also supports the `xtls-rprx-vision` flow and the gRPC transport over TLS or REALITY.`
- `New log-file-size-limit option in [General] sets the maximum log file size in MB. You can also set it in General → Log. When it is not set, the old limits still apply: 200 MB on Mac and 50 MB on iOS.`
- `New surge-cli capture-filter command to read and change capture filters.`
- `New surge-cli dump traffic-stat-records <today|this-month|last-month> returns one period's traffic statistics, merged by host, policy and interface. The same data is available through MCP.`
- `New surge-cli policy-avoid list|add|remove|clear, the MCP tool set_policy_avoidance and the HTTP API GET / POST /v1/policies/avoided. policy-group now reports the avoided members of automatic groups.`
- `New surge-cli profile section command to read or replace a single profile section. With #!include, the change goes into the file that holds the section and other files stay untouched.`
- `New “Disable UDP Fast Path” option in the gateway settings. When a device creates many UDP flows in a short time (for example, P2P downloads), Surge VM normally moves it to the UDP Fast Path. That path forwards its UDP traffic directly at L3 without applying rules. Turn this option on to stop using the fast path for all devices, so all UDP traffic always goes through your rules.`
- `Note: Surge does not apply your Tailscale access control policy to incoming connections. Use rules such as SRC-IP to limit who can reach which destination.`
- `On iOS 27.3 beta 1, a problem in the system’s Network Extension framework can cause Surge to stop unexpectedly. The problem is in iOS itself, and we are waiting for Apple to fix it in a future update.`
- `Performance`
- `Profile Reload`
- `Profile errors now explain why a line is invalid, not only where it is.`
- `Proxy Protocol`
- `SOCKS5 (authentication rejected, or no acceptable method)`
- `SOCKS5 UDP`
- `Saved Capture Session`
- `ShadowTLS v3`
- `Special handling for Apple Screen Sharing is now built in and works without any configuration.`
- …（另有 34 条）
