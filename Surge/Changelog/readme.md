# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#466](https://t.me/SurgeTestFlightFeed/466) · 2026-11-19

### Beta 更新 - TLS 客户端指纹

现在，Proxies over TLS 可以通过新的 `client-fingerprint` 参数，重现真实客户端的 TLS ClientHello：

- `apple-26`: Apple 的系统 TLS 堆栈，由 Safari 及使用 NSURLSession 的应用程序发送：iOS 26–27、macOS 26–27、Safari 26–27
- `chromium-155`: Chrome 155–158 以及基于 Chromium 构建的浏览器
- `auto`（默认）：推荐指纹，当前为 `apple-26`

代理 = 木马，example.com，443，password=pwd，client-fingerprint=chromium-155

此更新适用于 HTTPS、SOCKS5-TLS、HTTP/2 CONNECT、Trust Tunnel、Trojan、AnyTLS 以及使用 TLS 或 REALITY 的 VMess/VLESS。分享链接中的 `fp` 值会自动转换。由于 `auto` 是默认值，现在所有 TLS 代理开箱即用即可模拟 Apple 的系统流量；如需保留旧有行为，请使用 `none`。

Surge 的 TLS 基于 BoringSSL 构建，而 Chrome 也使用相同的库；Apple 的 TLS 栈则运行在其自行分叉的版本之上。因此，这些指纹信息源自该库本身，而非来自某个模板：GREASE 值、扩展顺序以及 ECH GREASE 的生成方式与原始客户端相同，而握手过程的其余部分也遵循相同的代码。

## [#465](https://t.me/SurgeTestFlightFeed/465) · 2026-11-19

### Beta 更新

#### Surge 引擎

##### 智能组改进

- 更稳定的出站连接：除非另一个策略组明显更快，否则站点将持续使用其当前使用的策略组；同时打开到新站点的连接将使用相同的策略组。
- 失效策略的绕过速度更快：一旦备用连接接管了无法连接的策略，站点就会切换到正常工作的策略，而不会在每次新连接时都等待失效策略。
- 现已注意到传输缓慢的问题：除了延迟之外，Surge 现在还会测量响应的第一个兆字节所需的时间。当某个策略组持续以比以前慢得多的速度传输某个网站的数据时，对该网站的新连接将改用另一个策略组。
- 评分更准确：在客户端发送任何内容之前就已关闭的连接（例如浏览器的预连接）不再计为失败。

无需进行任何配置更改。

##### TLS

- 新增的 `client-fingerprint` 参数可让 TLS-over-TCP 代理（HTTPS、SOCKS5-TLS、HTTP/2、Trust Tunnel、Trojan、AnyTLS，以及使用 TLS 或 REALITY 的 VMess 和 VLESS）发送真实客户端的 ClientHello：`apple-26`（Safari 以及 iOS 和 macOS 26 上的应用）、`chromium-155`（Chrome）、`auto`（默认值，当前为 `apple-26`）或 `none`（之前的纯 ClientHello）。若未使用 `alpn`，这些连接现在会像浏览器一样支持 HTTP/2 和 HTTP/1.1。分享链接将 uTLS 指纹名称映射到这些值。
- 新增的 `ech-config` 参数可为基于 TLS 和 QUIC 的代理启用加密客户端问候（Encrypted Client Hello），并使用您提供的 ECHConfigList，从而隐藏真实的 SNI。如果配置文件不可用，连接将直接失败，而不会回退到明文客户端问候；当服务器拒绝 ECH 时，错误信息会包含服务器的重试配置，以便您更新 `ech-config`。ECH 无法与 REALITY 结合使用。

##### 修复

- 修复了 MASQUE 在 HTTP/3、Hysteria2 和 TUIC 协议下忽略 `client-cert` 的问题，该问题曾导致需要客户端证书的服务端拒绝连接。
- 修复了当某个 URL 的 `#!include` 文件在首次下载时被拒绝的问题，即使其包含的配置文件中存在一个 `FINAL` 规则。
- 修复了带有前导或尾随空格的参数值（例如 `external-policy-name-prefix="[Hello] "`）在 Surge 重写配置文件时丢失这些空格的问题。
- 修复了在某些情况下，当一次遗留的设置重试失败后，一个正常工作的连接有时会被关闭的问题。此问题也导致使用了底层代理的 DNS-over-TLS、Tailscale 和 HTTPS 代理测试中断。
- 修复了智能组将从未发送过数据的浏览器预连接计为策略组违规行为的问题。
- 修复了连接未发送任何数据包后，数据包丢失在智能策略组的评分中不再被计入的问题。

##### Surge Mac

- 代理编辑器新增了客户端指纹和 ECH 配置选项。
- 修复了在另一款应用处于全屏模式且 Surge 窗口位于另一个“空间”时，点击菜单栏图标无响应的问题。

##### Surge iOS

- 代理编辑器新增了客户端指纹和 ECH 配置选项。
- 修复了在启用 `encrypted-dns-follow-outbound-mode` 时，混合发送加密 DNS 查询会直接通过蜂窝网络，从而绕过规则所选路由的问题。
- 修复了在深色模式下，Face ID 覆盖层在启动屏幕上闪烁为白色的问题。

## [#464](https://t.me/SurgeTestFlightFeed/464) · 2026-11-19

### Surge iOS 6 现已在 App Store 上架，同时发布的还有 Surge Mac 6.12 和 Surge tvOS 6.0。

Surge iOS 6 是一款免费更新，对界面和核心引擎进行了大量改进。只有少数新功能需要有效的更新订阅：新的主屏幕、配置文件历史记录以及 MCP 服务器。

Surge iOS 6 已针对 iOS 26 重构，重绘了应用中的几乎每个屏幕，并在您的 iPhone 和 iPad 上运行与 Surge Mac 相同的引擎。

#### 新增内容：

- 全新的主屏幕。滑动第一张卡片即可启动 Surge，然后在一个仪表盘中查看实时流量、网络状态、使用情况以及快速控件。您可以选择要显示的卡片及其排列顺序。

- 专为 iOS 26 设计。Configure 将其设置按类别整理，您可以左右滑动切换；策略组卡片可原地展开，菜单则在您轻点的位置直接打开。

- 更快的请求列表。每一行都带有网站图标，并以特定颜色显示其状态；图像响应会显示缩略图；筛选器则位于列表正上方。轻触并按住筛选器即可反转它。

- 配置文件历史记录。每次保存都是一个版本：在保存前查看更改内容，比较任意两个版本，并通过一次轻触即可回滚。文本编辑器会在您输入时检查每一行。

- 空间允许时，显示两个窗格。在更宽的屏幕上，仪表板会保持在设置旁边。

- 一个用于 AI 智能体的 MCP 服务器。启用 MCP 端点后，Claude Code 等智能体将获得与 surge-cli 相同的控制权，甚至可以控制另一台设备上的 Surge。iPhone 设备本身上的 MCP 应用（例如 FlowDown 和 Minis）可以直接驱动 Surge。

- 与 Surge Mac 共用的更强大的引擎 6.12:
– 支持更多代理协议和传输方式，并为每种受支持的协议添加分享链接导入功能
– 大型配置文件和数千个代理的内存占用大幅减少
– 停止响应的服务器会在数秒内被替换
– 将您的设备提供给您的 tailnet，用作 Tailscale 出口节点或子网路由器
– 接受传入的 WireGuard 对等体
– 自适应 QUIC 拦截，确保仅使用 QUIC 的应用仍可正常运行
– 使用您自己的证书进行 MITM
每次引擎更改都会针对每种代理协议的官方客户端自动进行测试。

此外，还重新设计了远程仪表板，新增了新闻页面，并进行了许多其他改进和修复。

Surge Mac 6.12 采用了相同的引擎，因此上述有关引擎的所有内容也同样适用于 Mac 版本。请通过应用进行更新，或从 [nssurge.com](http://nssurge.com/) 下载。

Surge tvOS 6.0 将全新引擎引入 Apple TV，其重新设计的启动屏幕可显示实时活动、近期事件和 Surge Ponte 状态，并快速访问出站模式、策略组和外部资源。配置文件和日志查看器也已重构。更新后，请再次通过 Surge iOS 6 设置您的 Apple TV。

Surge iOS 6: [https://nssurge.com/surge-ios-6](https://nssurge.com/surge-ios-6)
完整发布说明：[https://nssurge.com/surge-ios-6/release-notes](https://nssurge.com/surge-ios-6/release-notes)
Surge Mac 版本说明：[https://nssurge.com/support/mac/release-notes](https://nssurge.com/support/mac/release-notes)
在 App Store 下载：[https://apps.apple.com/app/id1442620678](https://apps.apple.com/app/id1442620678)

## [#463](https://t.me/SurgeTestFlightFeed/463) · 2026-11-17

### 配置文件验证服务：文档现已提供

[https://services.nssurge.com](https://services.nssurge.com/) 上的配置文件验证服务（Beta 版）现在已在手册中新增一个页面。

涵盖：

- 两种请求格式：原始配置文件或 JSON。
- 响应格式和状态码。
- 新的 /v1/version 端点，用于显示解析器构建所用的 Surge 版本。
- 该服务会检查哪些内容，不会检查哪些内容。例如，它不会解析 #!include 文件，也不会下载远程规则集。

[https://manual.nssurge.com/tools/profile-validation.html](https://manual.nssurge.com/tools/profile-validation.html)

同时，在线手册的风格也已更新，以匹配最新的官方网站设计。

## [#462](https://t.me/SurgeTestFlightFeed/462) · 2026-11-17

### Beta 更新

#### Surge 引擎

- Tailscale 拆分 DNS 路由现已生效，因此 tailnet 中使用了受限名称服务器的域名将通过 Tailscale 策略进行解析；策略详情会列出这些路由。
- 现在，带有 UUID 但没有令牌的 `tuic` 代理将被视为 TUIC v5，以与其他客户端和订阅转换器保持一致。带有令牌的代理仍保持在 v4。
- HTTPUpgrade now works with sing-box and mihomo servers.
- 来自 `http-request` 脚本的模拟响应现在会向 HTTP/2 客户端发送 `trailers`，因此 gRPC 模拟可以返回一个状态。
- 不含出口节点的 Tailscale 策略组，以及不含 DNS 的 WireGuard，将不再提供无法运行的外部 IP、NAT 类型和带宽测试，而 UDP 中继测试会立即失败。
- iPerf 环回测试主机现在始终走 DIRECT 路径，其流量将不再计入流量统计。
- 修复了从此设备或被接管设备发出的、目标为 Surge 自身 Tailscale 或 WireGuard 地址的 DNS TCP 查询被拒绝的问题。
- 修复了部分解析器（例如 Linux、Android 和 Go 上的解析器）将 Surge 的空白 DNS 响应误判为服务器故障的问题。
- 修复了当服务器拒绝 HTTPUpgrade 请求时 UDP NAT 类型测试卡住的问题。

#### Surge Mac

- “概览”下新增 AI 集成页面：可一键安装适用于 Claude Code 和 Codex 的 Surge agent 技能，提供可供复制的其他智能体安装说明，以及 MCP 服务器切换功能，并附带可直接复制的适用于 Claude Code、Codex、JSON 或仅密钥的配置。点击“帮助”菜单项即可打开该页面。
- 已将 URL Rewrite、Header Rewrite、Body Rewrite 和 Map Local 编辑器重构为 settings-card 工作表。现在可以编辑被拒绝的 URL rewrites 和 JSON JQ body rewrites，Map Local 也支持所有数据类型和状态码。
- 重写编辑器有一个注释字段，重写列表有一个“注释”列。
- 增强模式下，本地应用的上传速度更快。
- 修改后的请求现在在仪表盘中以紫色显示。
- Tailscale 策略组详情现在会列出 Split DNS 路由。
- “Rewrite”页面上的卡片间距更大。
- “仪表板”上方的侧边栏分隔线现在已使用系统分隔线样式。
- 修复了编辑重写规则时其注释被删除以及重新启用已禁用规则的问题；现在注释标记将被保留。
- Fixed editing a non-file Map Local rule turning it into a file rule and dropping its status code.

#### Surge iOS

- 远程页面分为“概览”和“工具”两个部分；工具部分以列表形式呈现，与“实用程序”页面相同；维护操作移至“更多”菜单；最后显示的版块会被记住。
- URL Rewrite、Header Rewrite、Body Rewrite 和 Map Local 编辑器都包含一个注释字段。规则列表和重写列表会将注释显示在单独一行，并且搜索功能也能匹配这些注释。
- DNS 响应路径现在以链式方式绘制，从查询的名称开始，经过每个 CNAME，直至地址。
- 修改后的请求现以紫色显示。
- 修复了远程设备控制面板上的 DNS 卡和 DNS 结果无法打开的问题。
- 修复了编辑重写规则时导致其注释丢失、注释标记被更改或已禁用规则被重新启用的问题。
- 修复了 Surge 自动重启后 MTProto 代理、HTTP API 和端口转发仍保持中断的问题。
- 修复了当服务器关闭连接时，响应末尾有时会被截断的问题。
- 修复了当 DNS 服务器在蜂窝网络下不可访问时，混合网络和 Wi-Fi 辅助功能会将加密 DNS 错误日志填满的问题；现在，在发生一次失败后，Surge 会在蜂窝网络下跳过该服务器 30 秒。
- 修复了深色模式下日志簿脚本详情中浅色文本与浅色背景对比度不足的问题。

## [#461](https://t.me/SurgeTestFlightFeed/461) · 2026-11-16

Surge iOS 测试版：VIF 回环基准测试与协议性能验证 最新的 Surge iOS 测试版在 iPerf 页面中引入了一项一键式 VIF 回环测试。该工具可测量虚拟接口 (VIF) 和用户空间 TCP 栈的吞吐量……

## [#460](https://t.me/SurgeTestFlightFeed/460) · 2026-11-16

### Beta 更新

#### Surge 引擎

- `$httpClient` 响应现在包含 `trailers`，因此调用 gRPC 端点的脚本可以读取 `grpc-status`。
- 编辑后的本地规则集、域名集和 `policy-path` 文件现在会在重新加载配置文件时生效，并且每次重新加载时都会重试失败的本地资源。
- Surge 现在会在虚拟网络接口停止接收数据包时发出警告，并告知您如何恢复。
- 修复了 Tailscale 和 WireGuard 对等节点无法通过 TCP 向 Surge 的会话地址发起 DNS 查询的问题，该问题曾导致 Tailscale 客户端报告 DNS 不稳定。
- 修复了未实际更改的配置文件或包含文件被报告为已更改或已重新加载的问题。
- 修复了当订阅在 `[Proxy]` 中列出 "DIRECT = direct" 时，DIRECT 错误地显示为 `policy-path` 策略组成员的问题。
- 修复了某项 XHTTP 失败在策略组的近期错误中重复显示的问题。
- 修复了“Include All Networks”警告中关于 `suspend=true` 会统计已禁用或已注释的子网设置的问题。

#### Surge Mac

- 仪表盘中新增了请求状态颜色：失败为红色，已拒绝为灰色，已修改为橙色，建立中为青色。
- 仪表盘请求详情状态现在显示为带颜色的胶囊状，与 Surge iOS 保持一致。
- 修复了使用 `#!include` 的配置文件通过 URL 导入时，因“关联的配置文件尚未就绪”而失败的问题。
- 修复了导入错误警报在打开面板后消失，并导致主窗口保持灰显的问题。
- 修复了在 Surge 无法读取浏览器当前 URL 时，add-rule 面板未提供任何规则类型的问题。
- 修复了活动栏将警告数量标记为错误的问题。

#### Surge iOS

- 重新设计了 DNS 缓存列表和详细信息，新增了缓存剩余存活时间、不区分大小写的搜索功能以及轻点复制功能。
- 重做了远程页面，采用了大号标题、圆形切换按钮以及工具图标网格。
- 新的请求状态颜色：失败为红色，拒绝为灰色，修改为橙色，建立中为青色。
- 请求列表设备筛选器现在可通过 MAC 地址识别局域网设备。
- 现在，长按请求详情标题后，会在 URL 上方显示一个“复制”气泡。
- 现在启动 Surge 时，会从已启用列表中移除已删除或无法解析的模块。
- Fixed single-stream uploads from local apps stalling for seconds at multi-gigabit speeds on fast iPads such as iPad Pro M5.
- 修复了下载使用 `#!include` 的配置文件时，因“关联的配置文件尚未就绪”而失败的问题。
- 修复了在 iOS 26 之前，徽章列表行中的文本与行边缘接触的问题。
- 修复了策略组卡片在展开卡片周围显示的问题。

#### Surge tvOS

- 更新开始按钮的 UI 样式
- 修复日志和配置文件页面无法滚动的问题

## [#459](https://t.me/SurgeTestFlightFeed/459) · 2026-11-15

### Surge tvOS Beta 测试版

- 与 Surge iOS 6.0 引擎同步，支持所有新功能。
- 采用全新的 Surge iOS 6.0 风格重新设计了用户界面。
- 修复了可能需要手动重启才能正确应用配置同步的问题。
- Surge Ponte 现在支持配置多个通道，与 Mac 版本功能一致。
- 优化了配置文件和日志的查看功能。

## [#458](https://t.me/SurgeTestFlightFeed/458) · 2026-11-15

### Surge iOS 测试版：VIF 回环基准测试与协议性能验证

最新的 Surge iOS 测试版在 iPerf 页面中引入了一项一键 VIF 环回测试。该工具可测量虚拟接口 (VIF) 和用户空间 TCP 栈的吞吐量，让您能够轻松验证其在设备上的性能。

参考结果（最新构建）：

- iPhone 17 Pro 系列（单连接）：18.7 Gbps 下行链路 / 12.7 Gbps 上行链路

此外，我们已完成全面的真实世界基准测试，将每个受支持的代理协议与其官方客户端进行了对比。在吞吐量和延迟方面，Surge 的性能均与官方客户端持平或更优，完全符合各协议的理论设计。

## [#457](https://t.me/SurgeTestFlightFeed/457) · 2026-11-15

### Beta 更新

#### Surge 引擎

- 大幅降低了大型配置文件、大量内联规则、大型模块以及数千个已测试策略组的内存使用。
- 一个指向完整配置文件的 `policy-path` 现在仅读取其 `[Proxy]` 部分，从而大幅降低了峰值内存使用。
- 现在，以主机开头的 URL 模式在针对其他主机的请求中将被跳过，从而加快 HTTP 请求速度，并在使用大型模块时节省内存。
- New `$response.trailers` lets `http-response` scripts with `requires-body=true` read the trailer section, and returning `trailers` replaces it.
- VLESS REALITY 现在可与早于 Xray 的服务器配合使用 25.5.16。
- 修复了在 HTTP/2 客户端环境下，或当脚本对有效负载进行缓冲时，响应尾部数据丢失的问题，该问题曾导致 gRPC 调用中断。
- 修复了 CDN 后方的 XHTTP 连接中，已完成的流被重置后计为策略组错误的问题。
- 修复了折叠的 HTTP 标头行丢失其续行内容的问题。
- 修复了重新加载后仍保留先前配置文件的策略组警告的问题。

#### Surge Mac

- 增强模式下本地应用的吞吐量更高、CPU 使用率更低，通过高延迟链路从网关设备上传的速度更快。
- 仪表板请求详情现在会显示响应标尾部分。
- surge-cli 中新增 `restart-ponte-server` 命令，该命令也已在 HTTP API 和 MCP 工具中提供。

#### Surge iOS

- 应用与隧道之间的 TCP 速度大幅提升：在回环测试中，下载速度几乎翻倍，上传速度则增长了一倍多。
- 重新设计了 Surge tvOS 启动屏幕，并新增了配置文件和日志查看器。
- 请求详情现在会显示“响应附加标头”部分。
- 现在，通过“实用工具”打开的脚本编辑器会保留在选项卡内，保存时会首先列出已编辑的文件。
- iPerf 页面上的回环测试现已可用。
- Surge 现在会在一个配置文件包含超过 5000 条内联规则时，或在 `include-all-networks` 与 `suspend=true` 结合使用时发出警告。
- 修复了在 iPhone 上脚本编辑器最后几行被键盘隐藏的问题。
- 修复了“配置文件”和“模块”页面上的移动列表未跟随手指移动的问题。
- 修复了展开的策略组卡片下方行中的卡片会淡出的问题。

## [#456](https://t.me/SurgeTestFlightFeed/456) · 2026-11-14

### Beta 更新

#### Surge 引擎
- 新的 `ws-http-upgrade=true` 选项（与 `ws=true` 一起）为 VMess、Trojan 和 VLESS 使用 HTTPUpgrade 传输方式。使用 type=httpupgrade 的分享链接会被导入，并且代理编辑器中新增了一个 HTTPUpgrade 开关。
- VLESS REALITY 现在发送的 TLS ClientHello 与 Chrome 相同。
- 在使用数千个代理时，内存使用量大幅减少。
- 加密 DNS 现在遵循 `dns-follow-interface`。在使用 Wi-Fi 辅助或混合模式时，加密 DNS 也会通过蜂窝网络进行查询。
- DNS 查询现在会在 1、2 和 4 秒后重新发送，而没有任何响应的查找会在 5 秒后失败，而不是大约 11 秒后。
- Tailscale 现在会通过已绑定的 DIRECT 底层策略（例如 CELLULAR-ONLY）的接口，或通过其自身的 `interface` 发送流量。
- Hysteria 2、TUIC 和 MASQUE 现在会在服务器停止响应 3 秒后（而非近 4 秒后）将其检测为不可用。
- 修复了将 Surge 用作 Tailscale 出口节点的设备无法解析任何域的问题。
- 修复了当仅支持 IPv6 的代理服务器不可用时（例如，在切换到仅支持 IPv4 的网络后），智能组未能进行故障转移的问题。
- 修复了 Wi-Fi 辅助功能和混合蜂窝备份在链式代理下通过主网络连接的问题。包含 `hybrid=false` 或已绑定接口的策略组成员将不再获得蜂窝备份。
- 修复了一个问题：有问题的加密 DNS 服务器会将网络标记为“不稳定”，并暂停智能策略组学习，而网络本身并无异常。
- 修复了当服务器关闭连接时，DNS-over-TLS 查询等待超时的错误。

#### Surge iOS
- 现在，请求列表会在每个请求的彩色圆点旁边标明其状态，对于没有图标的网站，则使用中性类型的徽章和灰色占位符。
- 数据包捕获列表的布局与请求列表类似，现在数据包时间可在 12 小时时区中正确显示。
- 仪表盘上的“Top Traffic”条形图现在以蓝色显示代理流量占比，以紫色显示直接流量占比。
- 徽章尺寸略大，徽章列表中的行间距更紧凑。
- 修复了折叠的策略组卡片会从展开卡片的角落透出的问题。
- Surge tvOS 部署页面现在支持任意组合的 Ponte 通道：一个 IPv4 通道、IPv6 直接访问和代理中继，与 Mac 版相同。旧版 Surge tvOS 仍可继续使用。此更新在后续的 tvOS 版本也更新到 6.0.0 之前不会生效。

#### Surge Mac
- 仪表板请求列表的 CPU 占用率大幅降低，并在隐藏时暂停。

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

代码、版本号和链接会先换为占位符；配置键、命令名等标识符由提示规则要求原样保留。译文通过格式与占位符校验后才使用。

本轮仍有 **2** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `New `$response.trailers` lets `http-response` scripts with `requires-body=true` read the trailer section, and returning `trailers` replaces it.`
- `Surge iOS 6: [https://nssurge.com/surge-ios-6](https://nssurge.com/surge-ios-6)`
