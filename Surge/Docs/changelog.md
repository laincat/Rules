# Surge 更新日志（自动生成）

> ⚙️ **本页由 `tools/docs_watch.py` 自动生成，请勿手工编辑。**
> 生成时间：2026-09-22T23:37:31Z（UTC） · 最近一周 = 2026-09-15 起

数据来源：Surge Mac 的 **appcast 双通道**（官方更新日志页读的就是它）
与 **Telegram @SurgeTestFlightFeed**。
iOS 版本来自 **App Store**。

---

## 一、最近一周（2026-09-15 起）

### 正式版（本周无新版本，最近一次如下）

#### `6.9.1`（build 12290） · 2026-09-09


**Improvements**
- The macOS logical rule editor now supports Pre-Matching for AND, OR, and NOT rules using a reject policy, and identifies unsupported sub-rules before saving.
- Added UNKNOWN support to GEOIP and IP-ASN rules, allowing you to match destination IP addresses with no corresponding country or ASN database entry. Supported in both individual rules and rule sets.

**Fixes**
- Fixed missing traffic statistics for UDP connections through proxies and tunnels, including WireGuard and Tailscale.
- Fixed a rare issue where a UDP proxy connection closing during packet reception could stall other traffic handled by Surge.
- Fixed dark menu text becoming unreadable on macOS 26 and improved menu bar icon colors when the system appearance changes.
- Fixed unnecessary Surge Helper installation or upgrade alerts at startup when the enabled features do not require the helper.
- Fixed Hysteria UDP traffic failing with servers where HTTP/3 Datagram negotiation interfered with UDP forwarding.
- Fixed macOS Smart policy group context menus showing outdated usage or incorrect priority adjustments.

### 测试版（Beta 通道）

#### `6.10.0`（build 12360） · 2026-09-22


**Improvements**
- A `category` parameter has been added to policy groups for grouped display. It can be used when there are many policy groups.
- All `test-url` parameters now support configuring HTTPS URLs for testing. The test result remains the latency of a single HTTP RTT, but due to the TLS handshake, the test duration may increase significantly when there are many policies.
- In the previous version, MITM security was strengthened by generating a separate key pair for each distinct domain name. This caused noticeable delays when performing MITM concurrently on a large number of different domains. After evaluation, this change has been reverted.
- Add a workaround for a system bug in macOS 27.2 beta to prevent Dashboard from crashing.
- Improved UDP test diagnostics for peer-to-peer Tailscale and WireGuard policies without Internet egress, reporting unsupported tests instead of waiting for a timeout.
- Fixed logical rules incorrectly parsing policy names containing parentheses.
- Inline rule sets with the same name now merge across the main profile and modules instead of replacing one another, preserving rules contributed by each source.

---

## 二、最近 30 天上下文

| 通道 | 版本 | build | 日期 |
|---|---|---:|---|
| 正式版 | `6.9.1` | 12290 | 2026-09-09 |
| 正式版 | `6.9.0` | 12250 | 2026-08-31 |
| 正式版 | `6.8.1` | 12030 | 2026-08-10 |
| 正式版 | `6.8.0` | 11990 | 2026-08-06 |
| 正式版 | `6.7.0` | 11730 | 2026-07-15 |
| 正式版 | `6.6.0` | 11270 | 2026-06-01 |
| Beta | `6.10.0` | 12360 | 2026-09-22 |
| Beta | `6.9.1` | 12290 | 2026-09-09 |
| Beta | `6.9.0` | 12250 | 2026-08-31 |
| Beta | `6.8.1` | 12030 | 2026-08-10 |
| Beta | `6.8.0` | 11990 | 2026-08-06 |
| Beta | `6.7.0` | 11730 | 2026-07-15 |

> 同一版本的多个 beta build 在 appcast 里会**原地被覆盖**（只剩最后一条），
> 所以 build 级的中间过程要看上一节的 Telegram 公告。
