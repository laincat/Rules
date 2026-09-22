# 04 · DNS 与策略

> 返回 [readme.md](readme.md)

---

# 第一部分 · DNS

## 4.1 两种解析场景

Surge 的 DNS 行为**取决于是不是由它接管流量**：

| 场景 | 行为 |
|---|---|
| 未启用 VIF（未开增强模式 / 非网关） | 系统自己解析，Surge 只是看到连接 |
| 启用 VIF（增强模式、iOS VPN、网关模式） | **Surge 运行自己的 DNS responder**，客户端被配置为使用它 |

下述内容都针对**第二种**（这也是 Fake-IP 生效的前提）。

---

## 4.2 responder 监听的地址

| 平台 | 地址 |
|---|---|
| macOS | `198.18.0.2`（网关模式下也通过 DHCP 下发） |
| iOS | `198.18.0.4` |
| IPv6 | `fd00:6152::2` |

> `198.18.0.2` – `198.18.0.9` 这整段都被视为 Surge 的 DNS responder。

---

## 4.3 Fake-IP

VIF 启用时，对普通的 A / AAAA 查询，responder **不做真实解析**，
而是立刻返回一个伪 IP（来自保留段 `198.18.0.0/15`；
IPv4 池为 `198.18.1.1` – `198.19.255.254`，IPv6 用 `fd00:6152::` 下的独立前缀）。

Surge 会**持久记忆** 伪 IP ⇄ 域名的映射。当指向伪 IP 的连接到达时，
它被还原成原始域名，再做规则匹配与出站。

这样做换来两件事：

1. **连接前不引入 DNS 延迟** —— 真实解析只在匹配到的策略确实需要 IP 时才发生；
2. **规则始终看到原始域名**，哪怕客户端是自己解析的。

| 细节 | 值 |
|---|---|
| 伪应答 TTL | iOS **5 秒** / macOS **30 秒**（让客户端频繁重查，陈旧映射快速消失） |
| 地址族隔离 | AAAA 查询走 IPv4 到达时返回空应答，反之亦然 —— 客户端只会拿到它能路由到 Surge 的伪 IP |
| 非 A/AAAA 查询（TXT、MX 等） | **转发**给上游 DNS，与内部 DNS 客户端使用同一套服务器配置；`[Host]` 的 `server:` 项对转发查询同样生效 |

---

## 4.4 `hijack-dns`（劫持硬编码 DNS）

默认只回答发往 Surge 指定地址的查询；发往普通 DNS 服务器的查询正常穿过。

但有些设备/软件写死了 DNS（例如 Google 音箱固定用 `8.8.8.8`）。
用 `[General]` 里的 `hijack-dns` 把这类查询也接管：

```
[General]
hijack-dns = 8.8.8.8:53, 8.8.4.4:53
```

- 每项是 IPv4 地址或 `*`，端口可选（默认 `53`）；
- `hijack-dns = *:53` 表示劫持全部 DNS 查询；
- **只有能被解析为合法 DNS 查询的包才会被劫持**，发往这些地址的其它流量不受影响。

---

## 4.5 `always-real-ip`（让部分域名拿到真实 IP）

有些场景需要客户端拿到真实可路由的 IP，而不是伪 IP —— 例如游戏机的 NAT 类型
检测、VPN 客户端用到的域名。用 `always-real-ip` 把这些域名排除在 Fake-IP 之外：

```
[General]
always-real-ip = *.srv.nintendo.net, *.stun.playstation.net, xbox.*.microsoft.com, *.xboxlive.com
```

值按 **Host List** 语义匹配查询域名（支持通配）。命中者转给上游 DNS 并返回真实应答。

> 对被豁免的域名，`[Host]` 里的 IP 映射由 responder **权威应答**；
> 其它域名仍拿伪 IP，`[Host]` 映射在 Surge 建立真实连接时才生效。

---

## 4.6 `allow-dns-svcb`

可选，布尔，默认 `false`。

现代系统可能查 SVCB / HTTPS（type 65）记录而非 A 记录，而这类应答可以携带
IP 提示，从而**绕过 Fake-IP**。默认 Surge 把这类查询拒为 not-implemented，
迫使客户端回退到 A 记录。确实需要放行 SVCB/HTTPS 时才开。

---

## 4.7 GeoIP 数据库

`[General]` 里只有两个相关参数：

| 参数 | 说明 |
|---|---|
| `geoip-maxmind-url` | GeoIP 数据库的下载地址 |
| `disable-geoip-db-auto-update` | 关闭 GeoIP 数据库的自动更新 |

```
[General]
geoip-maxmind-url = https://example.com/Country.mmdb
```

> ⚠️ Surge **只能换 `geoip-maxmind-url` 这一个地址**。
> 官方明确说 `IP-ASN` 用的 ASN 库**没有配置项** —— 它随 App 更新，
> 不存在"自己换一份 ASN 库"的做法。

---

## 4.8 DNS 排错顺序

| 现象 | 先查 |
|---|---|
| 域名规则不生效、IP 规则反而命中 | 是不是被 Fake-IP 还原前的伪 IP 干扰；确认 IP 规则该加 `no-resolve` |
| 每个域名请求都多一次解析 | IP 类规则写在了前面且没加 `no-resolve` |
| 某设备完全不走 Surge 的 DNS | 它可能写死了 DNS，需要 `hijack-dns` |
| 游戏机 NAT 类型异常 | 该域名需要进 `always-real-ip` |
| 某些站点解析到 198.18.x.x | 那是 Fake-IP 的正常表现，不是故障 |

---

# 第二部分 · 策略与策略组

## 4.9 策略组基本形态

```
[Proxy Group]
Proxy = select, ProxyA, ProxyB, DIRECT
Auto  = url-test, ProxyA, ProxyB
Smart = smart, ProxyA, ProxyB
```

每行格式：`名字 = 类型, 成员1, 成员2, ..., key=value, ...`

**含 `=` 的组件是参数，其余是成员策略名。**

---

## 4.10 组类型

| 类型 | 行为 |
|---|---|
| `select` | 手动在界面选一个 |
| `url-test` | 自动选延迟测试最好的 |
| `fallback` | 按声明顺序选第一个可用的 |
| `load-balance` | 在可用成员间分摊请求 |
| `smart` | 依据观察到的连接质量与站点历史动态选择 |
| `subnet` | 按当前网络环境选 |

> 关键字 `ssid` 仍作为 `subnet` 的别名被接受（历史兼容）。

---

## 4.11 嵌套

组可以作为另一个组的成员 —— **除 `smart` 外**的所有类型都支持。
`smart` 会**静默忽略**其成员里的嵌套组与内置策略。

组引用**不能成环**。检测到环时 Surge 记警告，受影响的组临时表现为 reject
（日志里显示 `FAILED`）。若某组最终没有任何可用成员，Surge 回落到 `DIRECT`
（日志显示 `SUBSTITUTE`）并给一次性警告。

---

## 4.12 延迟测试怎么工作

自动类型（`url-test` / `fallback` / `load-balance` / `smart`）都依赖延迟测试：
对每个成员发一个 HTTP HEAD 请求并记录结果。测试是**惰性**的 ——
在组被使用时、且上次结果已过期或网络变化了才重测。

测试 URL 与超时的解析顺序：

1. 该策略自己的 `test-url` 参数（最高优先）；
2. 否则用 `[General]` 的 `proxy-test-url`（对代理类策略）
   或 `internet-test-url`（对 direct 类策略）。

---

## 4.13 用法示例

```
[Proxy Group]
# 手动选择，兜底直连
Proxy = select, Auto, US, JP, DIRECT

# 自动测速
Auto = url-test, US, JP, HK, url=http://cp.cloudflare.com/generate_204, interval=300

# 智能：按实际连接质量选
Smart = smart, US, JP, HK

[Rule]
DOMAIN-SUFFIX,example.com,Proxy
FINAL,Proxy
```
