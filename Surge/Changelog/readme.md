# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

## [#436](https://t.me/SurgeTestFlightFeed/436) · 2026-11-03

### Beta 更新
Surge Mac
Surge Dashboard
• The Traffic Statistics tab has a new Breakdown button in the bottom bar. Pick Host or Policy, and each row expands to show its policies or hosts, ranked by today, this month and last month.
Surge CLI
• New `surge-cli dump traffic-stat-breakdown <primary> <secondary>` groups traffic statistics by two of host, policy, interface, process and device. For example, `dump traffic-stat-breakdown policy host` lists each policy's hosts. The same data is available through MCP.
Surge iOS
改进
• You can now swipe left or right on the policy group page to switch categories.
• iPhone Duo: the inner screen now uses a single column in portrait. Before, the Configure cards overlapped. The sidebar button, which could hide the sidebar with no way to bring it back, has been removed.
修复
• Fixed iCloud Drive background sync staying disabled for too many files after a `.git` folder was removed from the Surge iCloud folder.
• Fixed Network Diagnostics jumping when a test row was tapped.
• Fixed the home tab title moving up under the Dynamic Island while Surge is stopped, on versions before iOS 26.
Surge Engine
Saved Capture Sessions
• HTTP capture sessions saved to disk can now be read through surge-cli, MCP and the HTTP API. Before, only the recent requests in memory were available. Each channel can list sessions, browse a session's requests with paging and a filter, and read request and response bodies:
• `surge-cli capture-session list | dump <session> | data <session> <key> <request|response>`
• MCP tools `list_capture_sessions`, `list_capture_session_requests` and `get_capture_session_body`
• `GET /v1/capture/sessions`, `/v1/capture/sessions/requests` and `/v1/capture/sessions/data`
• New capture sessions now also record their start and end time, limits, filter and why they ended.
改进
• Tailscale and WireGuard: connections from this device to its own tunnel address or MagicDNS name now reach the device itself. Before, they timed out.
修复
• Fixed capture limits set through surge-cli or MCP being ignored on a device that had never saved them in the app (for example `set ReplicaSessionParameters.timeLimit=600`). The command reported success, but the session still stopped at the default limits.

## [#435](https://t.me/SurgeTestFlightFeed/435) · 2026-11-02

### Beta 更新
iOS User Interface
- You can now rearrange and hide the Surge 6 home tab cards in Customize Home → Cards.
- The entire Module page has been completely redone to resolve some tricky issues.
- Other UI detail optimizations and adjustments.
自适应 QUIC 阻断
- 自适应模式现在仅在明确证明应用程序无法回退时，才允许主机使用 QUIC。这意味着在 0.5 秒内不会出现 TCP 连接，并且应用程序会在 3 秒内通过 QUIC 重试。该重试会立即执行。此前，仅缺少 TCP 连接这一条件就足以触发该行为，但应用程序可能只是取消了请求。如果在 3 秒内出现 TCP 连接，QUIC 将再次被阻止。如果两种情况均未发生，则不会记录任何信息。
改进
- Tailscale: Surge now finds a direct path to a peer that is behind NAT on the local network, such as a tailscaled container on a Docker bridge. Before, such a peer kept using DERP or a distant peer relay.

## [#434](https://t.me/SurgeTestFlightFeed/434) · 2026-11-01

### Beta Tips
In the new beta version, all of Surge's external control capabilities, including surge-cli, AI Skills, MCP, and the HTTP API, now have the ability to modify profiles.

## [#430](https://t.me/SurgeTestFlightFeed/430) · 2026-11-01

### Surge iOS Beta Updates
Home View
- We are starting to test a new Home View background.
- Meanwhile, the Surge 6 home tab has a new Customize Home panel below its cards. You can now fully customize the background color scheme.
- If you want to return to the background of the previous version, simply select Dark + Vivid.
修复
- 修复了从“捷径”或自动化中启动或停止 Surge 后，主屏幕小组件和控制项有时仍会显示旧状态的问题。
- 修复了当折叠一个类别时，模块页面会跳转到底部的问题。
- 修复了在 iPhone Duo 外屏上，策略组卡片运行于标签栏下方或折叠成单列窄栏的问题。
- Other fixes.

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

本轮仍有 **34** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `About the Design`
- `Beta Tips`
- `Home View`
- `If you want to return to the background of the previous version, simply select Dark + Vivid.`
- `In the new beta version, all of Surge's external control capabilities, including surge-cli, AI Skills, MCP, and the HTTP API, now have the ability to modify profiles.`
- `Meanwhile, the Surge 6 home tab has a new Customize Home panel below its cards. You can now fully customize the background color scheme.`
- `Other UI detail optimizations and adjustments.`
- `Other fixes.`
- `Saved Capture Sessions`
- `Surge CLI`
- `Surge Dashboard`
- `Surge Engine`
- `Surge Mac`
- `Surge iOS`
- `Surge iOS Beta Updates`
- `Tailscale: Surge now finds a direct path to a peer that is behind NAT on the local network, such as a tailscaled container on a Docker bridge. Before, such a peer kept using DERP or a distant peer relay.`
- `The entire Module page has been completely redone to resolve some tricky issues.`
- `We are starting to test a new Home View background.`
- `You can now rearrange and hide the Surge 6 home tab cards in Customize Home → Cards.`
- `iOS User Interface`
- …（另有 14 条）
