# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#468](https://t.me/SurgeTestFlightFeed/468) · 2026-11-23

### Surge iOS
- 关联配置文件的功能与 Mac 版一致：通过 URL 安装受管理配置文件时，系统会询问保留哪些部分保持同步（默认保留规则集、代理和策略组），并将其余部分复制到可编辑的配置文件中，此外还提供完全受管理模式作为替代选项。
- 在编辑器中或通过快速操作编辑受管理或团队配置文件时，系统会提供就地将其转换为链接配置文件的选项，且编辑器会继续将更改保存至该已转换的配置文件中。
- “创建链接配置文件”现在从整个配置文件的副本开始，适用于每个配置文件行，并链接到手册。
- Quick actions that would change a read-only section of a linked profile are now refused instead of being dropped silently on save.
- 日志簿行现在看起来与请求列表类似，带有彩色状态点、中性脚本样式的徽章以及记录详情。空列表或无结果的搜索将显示系统的空状态。
- 代理编辑器中的 ECN 选项现在是一个“自动/开/关”菜单，适用于 iOS 18 及更高版本上的 TCP 代理。修复了“自动”选项显示为“开”的问题，以及任何更改都会写入一个显式的 `ecn` 的问题。
- 策略组成员选择器现在使用内嵌分组样式。
- 修复了“主页”选项卡中蓝宝石徽标显示过大的问题。

## [#467](https://t.me/SurgeTestFlightFeed/467) · 2026-11-23

### Beta 更新

#### Surge 引擎

- `ecn` 参数现在也适用于 macOS 15 及更高版本和 iOS 18 及更高版本上的 TCP 代理：`ecn=true` 或 `ecn=false` 可开启或关闭与服务器的连接上的 ECN，而“自动”选项则交由系统决定。
- 修复了自 6.12.0 以来，正常关闭的连接被错误地标记为失败，并显示“由客户端重置”或“由远程方重置”的问题。
- 修复了 MITM HTTP/2 请求在服务器接受连接但从未响应 TLS 握手后，因等待“等待先前的连接建立完成”而无限期挂起的问题；现在该建立过程会超时。
- 修复了当配置文件使用 `#!include` 时，从 URL 安装配置文件会因解析错误而失败的问题。
- 修复了 WebView 引擎上一个失控脚本导致后续脚本卡住的问题；现在超时的脚本会被完全停止。
- 修复了 WebView 脚本中的异常，包括语法错误以及定时器回调和 `$httpClient` 回调中的异常，脚本不会像 JavaScriptCore 那样停止；现在报告的行号对应于您的脚本。
- 修复了 `$httpClient` 在 JavaScriptCore 上将 TypedArray 请求体作为 JSON 而非字节发送的问题。
- 修复了 `console.log` 对数组和错误的打印效果不佳的问题。
- 修复了 `setTimeout` 在没有延迟或带有额外参数的情况下出现的问题。
- `$persistentStore` 现在会在两种脚本引擎上将非字符串值存储为 JSON。
- WebView 脚本现在会在有超过 64 个计时器挂起时停止执行，与 JavaScriptCore 的行为一致。
- 处理大型 `$httpClient` 主体、`$persistentStore` 数据或 `$utils.ungzip` 的 WebView 脚本现在占用的内存要少得多。
- 修复了在部分网络上许可证激活超时的错误。

#### Surge Mac

##### 用户空间 TCP 网络协议栈

- 在 macOS 15 或更高版本上，无论是 DIRECT 连接还是连接到代理服务器的出站 TCP 连接，现在都使用 Apple 现代化的用户空间网络栈 Network.framework，而非 BSD 套接字。等待转发的数据不再驻留在内核的共享网络缓冲区中，因此，使用 Surge 作为网关的设备执行速度测试等高流量多连接操作，将不再耗尽这些缓冲区，也不会导致 macOS 强制停止 Surge。
- 由于这些连接的 TCP 缓冲区现在位于 Surge 自己的进程中，而非内核中，因此“活动监视器”会将这部分内存归因于 Surge。因此，Surge 的内存使用情况可能看起来比以前更高，但系统的总内存使用情况并未改变；只是相同的内存现在计入了 Surge，而非内核。
- 代理编辑器中的 ECN 选项现在可选“自动/开/关”，且适用于 macOS 15 及更高版本上的 TCP 代理。修复了“自动”状态错误显示为“开”的问题，以及任何点击操作都会写入显式的 `ecn` 的问题。
- 修复了更新因超时而安装失败的问题，例如在 macOS 更新待处理时发生的情况。

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

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

代码、版本号和链接会先换为占位符；配置键、命令名等标识符由提示规则要求原样保留。译文通过格式与占位符校验后才使用。

本轮仍有 **1** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `Surge iOS 6: [https://nssurge.com/surge-ios-6](https://nssurge.com/surge-ios-6)`
