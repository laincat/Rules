# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#438](https://t.me/SurgeTestFlightFeed/438) · 2026-11-05

### Beta 更新
Surge 引擎
Avoid in Automatic Groups
• You can now mark a policy as avoided. Use this when a policy passes latency tests but performs poorly in practice, for example with low bandwidth. Automatic groups (`url-test`, `fallback`, `load-balance` and `smart`) skip an avoided policy as long as any other member is usable. If nothing else is left, the avoided policy is still used.
• 直接引用的子网分组、临时覆盖项和策略组不受影响。
• 与覆盖项一样，当 Surge 重启时，标记会被清除。
• 新增 `surge-cli policy-avoid list|add|remove|clear`、MCP 工具 `set_policy_avoidance` 以及 HTTP API `GET` / `POST /v1/policies/avoided`。`policy-group` 现在会报告自动策略组中被排除的成员。
使用您自己的证书进行 MITM
• 新的 `[MITM] server-certificates = <hostname>:<keystore item>, ...` 会使用您自己的证书（例如受公众信任的证书）来解密列出的主机，而不是使用 Surge 的 CA 签发的证书。您可以使用它来检查那些固定了其证书或拒绝 user-installed CA 的应用程序。
• 此列表中的主机即使未配置 CA 也能正常工作。
• The first matching entry wins. If its PKCS #12 item cannot be loaded, Surge falls back to a CA-signed certificate.
• 项目中的中间证书将一并发送。
• Surge 会记录证书未覆盖的主机，并将无效条目作为配置文件警告显示。
Surge Mac
修复
• 修复了当 Surge 读取路由表期间路由表大小发生变化（例如 iPhone 通过 USB 连接时）导致 DIRECT 请求因“无出站接口”而失败的问题。现在，当读取失败时，Surge 会保留当前的主用接口。
• 修复了在静态 IPv4 配置下，当网络变更期间默认路由短暂消失后，主 IPv4 接口保持为空的问题。Surge 现在会监控默认路由的变化并重新进行检查。
• 修复了当某个网络接口拥有 IPv4 地址但没有默认路由时，Surge 每 30 秒重新加载网络状态的问题。
Surge iOS
New Features
• MitM 设置页面为 `server-certificates` 提供了一个编辑器，其中包含一个密钥库选择器和一个提示信息，用于显示证书是否覆盖主机名。
• 密钥库：现在，每个项目都会在其所在行显示其存储位置（在配置文件中还是在钥匙串中）。轻点该行即可移动或删除它。
• 项目按名称排序后显示在一个列表中，因此移动后的项目会保持在原位。
• When adding an item, you now enter the content first. The name is then prefilled from the file name or the SSH key comment, in the same prompt as the PKCS #12 password.
• 请求详情现可为远程 iOS 和 tvOS 设备提供“添加临时规则”功能。
• Long-press 新增自定义图标集，可复制其 URL、更新或删除。
改进
• Traffic details: long hostnames now wrap, and the traffic amount moves below the name instead of being pushed off the row. Long-press a host, policy or interface row to copy its name.
修复
• 修复了应用图标选择器。

## [#437](https://t.me/SurgeTestFlightFeed/437) · 2026-11-04

### Beta 更新
Surge Mac
New Features
• `[General]` 中的新 `log-file-size-limit` 选项用于设置日志文件的最大大小（单位：MB）。您也可以在“常规”→“日志”中进行设置。如果未设置，则仍适用旧有限制：Mac 上为 200 MB，iOS 上为 50 MB；详细日志记录时，这些限制会翻倍。
Surge CLI
• 新的 `surge-cli dump traffic-stat-records <today|this-month|last-month>` 返回一个时间段的流量统计信息，按主机、策略和接口合并。相同数据也可通过 MCP 获取。
改进
• 在请求列表中，已修改的请求现在有其专属的紫色状态点，而正在建立的请求则为灰色状态点。此前，已修改的请求与已完成（绿色）的请求外观相同，正在建立的请求也与活动（黄色）的请求外观相同。此变更适用于 Surge 仪表盘和 iOS 版本。
修复
• 修复了脚本 `max-size` 弹出窗口中显示“默认 (1024 KB)”的问题。Mac 的默认值为 10 MB。
• 修复了当脚本保存时，一个非预设值的 `max-size` 被重置为“默认”的问题。
Surge iOS
New Features
• The remote controller now has a Traffic Statistics tool for a remote Mac or iOS device. It has the same periods, grouping, details and export as the local page. The remote device must run a version that includes this update.
• 配置文件历史记录：向左滑动可删除单个版本。下一个更新的版本将继承被删除版本所做的更改。
• 策略组编辑器现在提供 `CELLULAR`、`CELLULAR-ONLY`、`HYBRID` 和 `NO-HYBRID`。此前，编辑器未列出这些规则集，手动添加后保存时会将其删除。
• 现在可以在“更多设置”→“高级”中设置日志文件大小。
修复
• 修复了从请求详情页面进行的第二次规则编辑未保存的问题。
• 修复了在页面底部展开长类别时，模块页会将类别标题移出屏幕的问题。
• 修复了在 iOS 26 之前“自定义主屏幕”面板没有背景的问题，导致其选项会绘制在卡片上方。
• 修复了 iPhone Duo 的布局问题。

## [#436](https://t.me/SurgeTestFlightFeed/436) · 2026-11-03

### Beta 更新
Surge Mac
Surge 仪表盘
• The Traffic Statistics tab has a new Breakdown button in the bottom bar. Pick Host or Policy, and each row expands to show its policies or hosts, ranked by today, this month and last month.
Surge CLI
• 新的 `surge-cli dump traffic-stat-breakdown <primary> <secondary>` 可根据主机、策略、接口、进程和设备中的两项对流量统计信息进行分组。例如，`dump traffic-stat-breakdown policy host` 会列出每个策略组的主机。您也可以通过 MCP 获取相同的数据。
Surge iOS
改进
• You can now swipe left or right on the policy group page to switch categories.
• iPhone Duo: the inner screen now uses a single column in portrait. Before, the Configure cards overlapped. The sidebar button, which could hide the sidebar with no way to bring it back, has been removed.
修复
• 修复了从 Surge iCloud 文件夹中移除一个 `.git` 文件夹后，iCloud Drive 后台同步功能因文件过多而持续保持禁用的问题。
• 修复了当测试行被点击时“网络诊断”发生跳转的问题。
• 修复了在 iOS 26 之前的版本中，当 Surge 停止时，主页标签页标题向上移动到灵动岛下方的问题。
Surge 引擎
已保存的捕获会话
• 现在，保存到磁盘的 HTTP 捕获会话可以通过 surge-cli、MCP 和 HTTP API 读取。之前，只有内存中的最近请求可用。每个通道都可以列出会话、分页浏览会话中的请求（并应用筛选器），以及读取请求和响应主体：
• `surge-cli capture-session list | dump <session> | data <session> <key> <request|response>`
• MCP 工具 `list_capture_sessions`、`list_capture_session_requests` 和 `get_capture_session_body`
• `GET /v1/capture/sessions`, `/v1/capture/sessions/requests` and `/v1/capture/sessions/data`
• 新的捕获会话现在还会记录其开始和结束时间、限制、过滤器以及结束原因。
改进
• Tailscale 和 WireGuard：现在，从此设备到其自身隧道地址或 MagicDNS 名称的连接可以到达设备本身。之前，这些连接会超时。
修复
• 修复了在从未于应用中保存过捕获限制（例如 `set ReplicaSessionParameters.timeLimit=600`）的设备上，通过 surge-cli 或 MCP 设置的捕获限制被忽略的问题。该命令报告成功，但会话仍会在默认限制处停止。

## [#435](https://t.me/SurgeTestFlightFeed/435) · 2026-11-02

### Beta 更新
iOS 用户界面
- 现在，您可以在“自定义主屏幕”→“卡片”中重新排列和隐藏 Surge 6 主屏幕卡片。
- 整个模块页面已完全重写，以解决一些棘手的问题。
- 其他 UI 细节优化与调整。
自适应 QUIC 阻断
- 自适应模式现在仅在明确证明应用程序无法回退时，才允许主机使用 QUIC。这意味着在 0.5 秒内不会出现 TCP 连接，并且应用程序会在 3 秒内通过 QUIC 重试。该重试会立即执行。此前，仅缺少 TCP 连接这一条件就足以触发该行为，但应用程序可能只是取消了请求。如果在 3 秒内出现 TCP 连接，QUIC 将再次被阻止。如果两种情况均未发生，则不会记录任何信息。
改进
- Tailscale：现在，Surge 能够找到一条直达本地网络中 NAT 后端对等节点（例如 Docker 桥接网络上的 tailscaled 容器）的路径。此前，这类对等节点会持续使用 DERP 或遥远的对等节点中继。

## [#434](https://t.me/SurgeTestFlightFeed/434) · 2026-11-01

### Beta Tips
在新版 Beta 版本中，Surge 的所有外部控制功能，包括 surge-cli、AI 技能、MCP 和 HTTP API，现在都具备修改配置文件的能力。

## [#430](https://t.me/SurgeTestFlightFeed/430) · 2026-11-01

### Surge iOS 测试版更新
Home View
- 我们已开始测试新的“主页视图”背景。
- 与此同时，Surge 6 的主页标签页在其卡片下方新增了一个“自定义主页”面板。现在，您可以完全自定义背景配色方案。
- 如果您想返回上一版本的背景，只需选择“深色 + 鲜艳”即可。
修复
- 修复了从“捷径”或自动化中启动或停止 Surge 后，主屏幕小组件和控制项有时仍会显示旧状态的问题。
- 修复了当折叠一个类别时，模块页面会跳转到底部的问题。
- 修复了在 iPhone Duo 外屏上，策略组卡片运行于标签栏下方或折叠成单列窄栏的问题。
- 其他修复。

## [#429](https://t.me/SurgeTestFlightFeed/429) · 2026-10-31

Surge iOS 6 Beta 现已在 TestFlight 上发布
完整介绍和发布说明：[https://nssurge.com/surge-ios-6](https://nssurge.com/surge-ios-6)
Surge iOS 6 已为 iOS 26 重新构建：全新的主屏幕、贯穿始终的液态玻璃效果、更快的请求列表、带版本号的配置文件，以及用于 AI 智能体的 MCP 服务器。
免费更新
Surge iOS 6.0 是一款免费更新，对界面和核心引擎进行了大量改进。只有少数新功能需要有效的更新订阅：新的主屏幕、配置文件历史记录以及 MCP 服务器。
如果您的更新订阅已过期，现在可以免费试用所有功能 7 天。先探索新功能，再决定是否续订。
Surge 6 还从代理协议中移除了 update-subscription 要求，现在所有协议都对所有 Surge 用户开放。（WireGuard、Tailscale 和 SSH 除外，因为它们不是代理协议。）
About the Design
当你第一次看到这些新颜色时，你可能会想“这看起来像是 AI 的敷衍之作”。其实并非如此。
自 2018 年 Surge v3 版本起，我们就开始使用这个 blue-purple 策略组，那还远早于人工智能时代。Surge iOS 6 在此基础上，融入了 Surge Mac 6 和 Liquid Glass 的设计语言。我们投入了大量时间来打磨最终效果。
我们重新设计和整理了几乎每个屏幕。
新增内容
• 主页：一目了然地掌握您的网络。活动、网络、外部 IP、带宽、DNS、使用情况、流量排名、策略组延迟以及事件，全部显示在一个仪表盘中。
• 液态玻璃：配置、策略组卡片和菜单均采用全新的 iOS 26 材质。菜单在您轻点的位置直接打开。
• 请求：每一行都显示网站图标、状态颜色和协议徽章。筛选栏始终固定在列表顶部。
• 配置文件历史记录：每次保存都是一个版本。在保存前查看更改内容，比较任意两个版本，并通过一次轻触即可回滚。
• iPad 和 iPhone 组合：当空间允许时，Surge 会切换为双窗格模式，使仪表板始终紧挨着您的设置。
• MCP 服务器：Claude Code 等智能体可获得与 surge-cli 相同的控制权。iPhone 上的 MCP 应用（例如 FlowDown 和 Minis）可以直接驱动 Surge。
• 引擎：Tailscale 出口节点和子网路由、WireGuard 监听端口、自适应 QUIC 阻塞、UDP over SOCKS5 Wi-Fi 访问，且不再限制规则集大小。所有这些功能均与 Surge Mac 6.11 共享。

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

技术字面量、代码、版本号和链接会先替换为占位符，译文通过格式与占位符校验后才使用。

本轮仍有 **18** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `About the Design`
- `Avoid in Automatic Groups`
- `Beta Tips`
- `Home View`
- `New Features`
- `Surge CLI`
- `Surge Mac`
- `Surge iOS`
- `• The Traffic Statistics tab has a new Breakdown button in the bottom bar. Pick Host or Policy, and each row expands to show its policies or hosts, ranked by today, this month and last month.`
- `• The first matching entry wins. If its PKCS #12 item cannot be loaded, Surge falls back to a CA-signed certificate.`
- `• The remote controller now has a Traffic Statistics tool for a remote Mac or iOS device. It has the same periods, grouping, details and export as the local page. The remote device must run a version that includes this update.`
- `• Traffic details: long hostnames now wrap, and the traffic amount moves below the name instead of being pushed off the row. Long-press a host, policy or interface row to copy its name.`
- `• When adding an item, you now enter the content first. The name is then prefilled from the file name or the SSH key comment, in the same prompt as the PKCS #12 password.`
- `• You can now mark a policy as avoided. Use this when a policy passes latency tests but performs poorly in practice, for example with low bandwidth. Automatic groups (`url-test`, `fallback`, `load-balance` and `smart`) skip an avoided policy as long as any other member is usable. If nothing else is left, the avoided policy is still used.`
- `• You can now swipe left or right on the policy group page to switch categories.`
- `• `GET /v1/capture/sessions`, `/v1/capture/sessions/requests` and `/v1/capture/sessions/data``
- `• `surge-cli capture-session list | dump <session> | data <session> <key> <request|response>``
- `• iPhone Duo: the inner screen now uses a single column in portrait. Before, the Configure cards overlapped. The sidebar button, which could hide the sidebar with no way to bring it back, has been removed.`
