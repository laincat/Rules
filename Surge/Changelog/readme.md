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

---

## 中文翻译

新增内容由 **Index-Translate** 自动翻译，缓存于 [`translations.json`](translations.json)。

技术字面量、代码、版本号和链接会先替换为占位符，译文通过格式与占位符校验后才使用。

本轮仍有 **1** 条等待翻译；下方暂时保留英文，后续运行会自动重试。

- `Surge VM`
