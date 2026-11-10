# Surge Telegram 每周更新日志（自动生成）

> 数据来源：[@SurgeTestFlightFeed](https://t.me/SurgeTestFlightFeed)。
> 本页只汇总最近 7 天的 Telegram 公告，并自动生成中文翻译。

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

## [#437](https://t.me/SurgeTestFlightFeed/437) · 2026-11-04

### Beta 更新

#### Surge Mac

##### 新功能

- `log-file-size-limit` 中的新 `[General]` 选项用于设置日志文件的最大大小（单位：MB）。您也可以在“常规”→“日志”中进行设置。如果未设置，则仍适用旧有限制：Mac 上为 200 MB，iOS 上为 50 MB；详细日志记录时，这些限制会翻倍。

##### Surge CLI

- 新的 `surge-cli dump traffic-stat-records <today|this-month|last-month>` 返回一个时间段的流量统计信息，按主机、策略和接口进行合并。相同数据也可通过 MCP 获取。

##### 改进

- 在请求列表中，已修改的请求现在有其专属的紫色状态点，而正在建立的请求则为灰色状态点。此前，已修改的请求与已完成（绿色）的请求外观相同，正在建立的请求也与活动（黄色）的请求外观相同。此变更适用于 Surge 仪表盘和 iOS 版本。

##### 修复

- 修复了脚本 `max-size` 弹出窗口中显示“默认 (1024 KB)”的问题。Mac 的默认值为 10 MB。
- 修复了当脚本保存时，一个非预设值之一的 `max-size` 值被重置为“默认”的问题。

#### Surge iOS

##### 新功能

- 现在，远程控制器为远程 Mac 或 iOS 设备提供了“流量统计”工具。该工具与本地页面具有相同的周期、分组、详细信息和导出功能。远程设备必须运行包含此更新的版本。
- 配置文件历史记录：向左滑动可删除单个版本。下一个更新的版本将继承被删除版本所做的更改。
- 策略组编辑器现在提供 `CELLULAR`、`CELLULAR-ONLY`、`HYBRID` 和 `NO-HYBRID`。之前，编辑器未列出这些规则集，手动添加后在保存时会将其删除。
- 现在可以在“更多设置”→“高级”中设置日志文件大小。

##### 修复

- 修复了从请求详情页面进行的第二次规则编辑未保存的问题。
- 修复了在页面底部展开一个长策略组时，模块页会将类别标题移出屏幕的问题。
- 修复了在 iOS 26 之前“自定义主屏幕”面板没有背景的问题，导致其选项绘制在卡片之上。
- 修复了 iPhone Duo 的布局问题。

## [#436](https://t.me/SurgeTestFlightFeed/436) · 2026-11-03

### Beta 更新

#### Surge Mac

##### Surge 仪表盘

- “流量统计”选项卡的底部工具栏中新增了一个“细分”按钮。选择“主机”或“策略”，即可展开每一行，查看其策略或主机，并按今天、本月和上月的情况进行排序。

##### Surge CLI

- 新的 `surge-cli dump traffic-stat-breakdown <primary> <secondary>` 按主机、策略、接口、进程和设备中的两项对流量统计信息进行分组。例如，`dump traffic-stat-breakdown policy host` 列出了每个策略的主机。您也可以通过 MCP 获取相同的数据。

#### Surge iOS

##### 改进

- 现在，您可以在策略组页面左滑或右滑以切换类别。
- iPhone Duo：现在，内屏在竖屏模式下使用单列显示。之前，配置卡片会相互重叠。现已移除侧边栏按钮，该按钮会隐藏侧边栏且无法将其恢复。

##### 修复

- 修复了在 Surge iCloud 文件夹中移除一个 `.git` 文件夹后，iCloud Drive 后台同步功能因文件过多而持续保持禁用的问题。
- 修复了在点击测试行时“网络诊断”发生跳转的问题。
- 修复了在 iOS 26 之前的版本中，当 Surge 停止运行时，主选项卡标题在灵动岛下方上移的问题。

#### Surge 引擎

##### 已保存的捕获会话

- 现在，已保存到磁盘的 HTTP 捕获会话可以通过 surge-cli、MCP 和 HTTP API 读取。此前，只有内存中的最近请求可供访问。每个通道都可以列出会话、分页浏览会话中的请求（并应用筛选器），以及读取请求和响应正文：
  - `surge-cli capture-session list | dump <session> | data <session> <key> <request|response>`
  - MCP 工具 `list_capture_sessions`、`list_capture_session_requests` 和 `get_capture_session_body`
  - `GET /v1/capture/sessions`、`/v1/capture/sessions/requests` 和 `/v1/capture/sessions/data`
- 新的捕获会话现在还会记录其开始和结束时间、限制、过滤器以及结束原因。

##### 改进

- Tailscale 和 WireGuard：现在，从此设备到其自身隧道地址或 MagicDNS 名称的连接可以成功到达设备本身。此前，这些连接会超时。

##### 修复

- 修复了在从未于应用中保存过捕获限制（例如 `set ReplicaSessionParameters.timeLimit=600`）的设备上，通过 surge-cli 或 MCP 设置的捕获限制被忽略的问题。该命令报告成功，但会话仍会在默认限制处停止。

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

代码、版本号和链接会先换为占位符；配置键、命令名等标识符由提示规则要求原样保留。译文通过格式与占位符校验后才使用。

当前窗口内没有待译条目。
