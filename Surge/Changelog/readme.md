# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#470](https://t.me/SurgeTestFlightFeed/470) · 2026-11-25

### Beta 更新

#### Surge 引擎

- [Map Local] 规则中，若其数据为远程文件，则现在支持 `update-interval`，例如 RULE-SET: 0 可保留 24 小时默认值，而负值则会禁用自动更新。此前，文件会每 24 小时强制刷新一次，且保存规则时会丢弃该选项。现在，两个编辑器都为远程文件提供了间隔时间设置。
- 修复了 `script-update-interval=-1`（在 iOS 脚本编辑器中禁用）不再阻止远程脚本更新的问题。

#### Surge Mac

- 内联和本地文件规则集中的规则集条目现在都带有可编辑的注释，并且规则集内容表中新增了一列“注释”。

#### Surge iOS

- 修复了 Wi-Fi 地址变更后（例如在同一网络上获得新的 DHCP 租约，或 Wi-Fi 非主要网络接口时），Wi-Fi 访问（LAN 代理、外部控制器和 HTTP API）仍停留在旧地址，直到被切换的问题。
- 修复了“个人热点访问”在发生其他网络更改前无法检测到热点开启或关闭的问题。
- 现在打开已保存的捕获会话已是即时操作：最新的 300 个请求会立即显示，其余请求则在后台加载，而不会因大型会话导致应用冻结数秒。待整个会话加载完成后，相册模式和导出功能即可使用。
- 内联和本地文件规则集中的规则集条目现在可以添加可编辑的注释。
- 当 VPN 停止时，日志簿和停止通知现在会说明原因。当另一个 VPN 接管时，日志簿和通知现在会在所有情况下（而不仅仅是部分情况下）说明这一点。
- 修复了上传的日志经常缺少诊断报告，或包含来自先前上传的陈旧报告的问题。
- 修复了在“开始”选项卡中隐藏“网络”卡片的问题，并从另一台设备（如 Apple TV）的远程控制页面中移除了“出站”模式控件。现在，卡片布局仅适用于本设备的“开始”选项卡。
- Map Local、URL、Header 和 Body Rewrite 编辑器的正则表达式字段现在使用带空格键的键盘，并且 Body Rewrite 的正则表达式和替换字段可接受任何语言的文本。
- 修复了全屏字段编辑器最后几行被键盘隐藏的问题。现在它还会保留字段的智能引号、短横线以及拼写检查设置。
- 修复了“配置文件”和“模块”页面上的垂直滚动有时会被误判为类别滑动的问题，导致列表在手指抬起前无法滚动。
- 修复了首次加载时策略组图标有时会被超大远程图片覆盖的问题。
- 修复了在文本查看器中选择编码时，选择器未关闭或其复选标记未更新的问题。

## [#469](https://t.me/SurgeTestFlightFeed/469) · 2026-11-24

### Beta 更新

#### Surge 引擎

- 修复了向 Tailscale 或 WireGuard 对等体发起的、目标端口拒绝连接的请求，在等待设置超时（Tailscale 为 20 秒）后以 503 错误失败的问题。现在这些请求会立即以“连接被拒绝”失败。在 `prefer-ipv6` 配置下，这会影响所有向仅监听 IPv4 的对等体服务发起的请求。
- 现在，当无法通过任何对等节点、子网路由或选定的出口节点访问 DNS 服务器（例如 `dns-server`、来自 tailnet 的解析器或 Split DNS 名称服务器）时，Tailscale 会发出警告。此前，对此类服务器的查询只有在 5 秒后才会超时。该警告会列出无法访问的服务器名称，并在这些服务器恢复可访问后消失。

#### Surge Mac

- 为 PROCESS-NAME 规则新增 `include-children` 选项，该选项也可在规则编辑器中使用：此规则还会匹配以应用名义发起的请求，例如应用启动的子进程（即使这些子进程来自其应用包之外的可执行文件）以及为其工作的系统服务（例如 WebKit Networking）。像 nsurlsessiond 这样的共享系统守护进程则不会归属到某个应用。
- 出站 TCP 连接现在重新使用 BSD sockets，而非 Network.framework。后者会将每个连接的接收缓冲区限制在约 7 MB，可能导致高延迟路径下的单连接下载速度减半。即使是大流量的多连接通信，仍无法耗尽内核的网络缓冲区：当客户端的读取速度慢于服务器的发送速度时，Surge 现在会限制在内核中等待的数据量。活动监视器不再将这部分 TCP 缓冲区内存计入 Surge。
- 修复了打开代理编辑器时发生的崩溃问题。

#### Surge iOS

- 修复了卡片样式中，展开卡片下方的策略组卡片上出现的黑色缺口。

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

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

代码、版本号和链接会先换为占位符；配置键、命令名等标识符由提示规则要求原样保留。译文通过格式与占位符校验后才使用。

本轮仍有 **1** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `Surge iOS 6: [https://nssurge.com/surge-ios-6](https://nssurge.com/surge-ios-6)`
