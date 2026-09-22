# 01 · 基础与全局配置

> 返回 [readme.md](readme.md)

---

## 1.1 配置骨架

mihomo 的配置是一份 YAML。官方默认配置（`docs/config.yaml`）就是最完整的字段清单，
**建议直接以它为起点**：

```
https://github.com/MetaCubeX/mihomo/raw/refs/heads/Alpha/docs/config.yaml
```

顶层主要段落：

| 段 | 作用 |
|---|---|
| `mixed-port` / `port` / `socks-port` | 入站端口 |
| `allow-lan` / `bind-address` | 局域网访问 |
| `mode` | `rule` / `global` / `direct` |
| `log-level` | 日志等级 |
| `ipv6` | IPv6 总开关 |
| `geox-url` / `geo-auto-update` | 地理数据库，见 [05](05-geodata.md) |
| `dns` | DNS 子系统，见 [02](02-dns.md) |
| `tun` | TUN 入站 |
| `sniffer` | 域名嗅探 |
| `proxies` | 出站节点 |
| `proxy-groups` | 策略组，见 [06](06-policy-groups.md) |
| `proxy-providers` / `rule-providers` | 外置集合，见 [03](03-providers.md) |
| `rules` / `sub-rules` | 路由规则，见 [04](04-rules.md) |
| `listeners` | 自定义入站监听 |
| `experimental` | 实验性配置 |
| `tunnels` | 隧道 |
| `hosts` | 本地映射 |
| `profile` | 选择记录等 |

---

## 1.2 入站端口

```yaml
mixed-port: 10801      # HTTP(S) + SOCKS 混合端口（推荐）
# port: 7890           # 仅 HTTP(S)
# socks-port: 7891     # 仅 SOCKS5
# redir-port: 7892     # 透明代理（Linux / macOS）
```

`mixed-port` 同时接受 HTTP 与 SOCKS 流量，是最省事的做法。

---

## 1.3 局域网访问

```yaml
allow-lan: true
bind-address: "*"          # 仅 allow-lan 生效；'*' 表示所有地址
lan-allowed-ips:           # 白名单，默认 0.0.0.0/0 与 ::/0
lan-disallowed-ips:        # 黑名单，默认空
authentication:            # http / socks 入口的用户名密码
  - "user:pass"
skip-auth-prefixes:        # 跳过验证的 IP 段
  - 127.0.0.1/32
```

> **黑名单优先于白名单。**

---

## 1.4 模式与日志

```yaml
mode: rule                 # rule / global / direct
log-level: info            # silent / error / warning / info / debug
ipv6: true                 # 关闭会阻断所有 IPv6 连接，并屏蔽 DNS 的 AAAA 记录
find-process-mode: strict  # 进程匹配模式
```

> Surge 里"出站模式"会**完全绕过规则表**；mihomo 的 `mode` 同理 ——
> `global` / `direct` 下 `rules` 不再参与决策，排查时先确认这一项。

---

## 1.5 外部控制（RESTful API）

```yaml
external-controller: 0.0.0.0:9093
# external-controller-tls: 0.0.0.0:9443   # 需要配置 tls 段
external-controller-cors:
  allow-origins: ["*"]
  allow-private-network: true
external-ui: /path/to/ui/folder/
# external-ui-name: xd
# external-ui-url: "https://github.com/MetaCubeX/metacubexd/archive/refs/heads/gh-pages.zip"
# external-doh-server: /dns-query
```

Windows 上还可用命名管道：

```yaml
external-controller-pipe: \\.\pipe\mihomo
```

详见 [07-operations.md](07-operations.md)。

---

## 1.6 TUN

```yaml
tun:
  enable: false
  stack: system              # system / gvisor / mixed / mips
  dns-hijack:
    - 0.0.0.0:53
  auto-route: true
  # auto-detect-interface: true
  # mtu: 9000
  # strict-route: true
```

| 字段 | 说明 |
|---|---|
| `stack` | 网络栈实现。`system` 最快，`gvisor` 兼容性最好，`mips` 是 mihomo 自研用户态栈 |
| `dns-hijack` | 需要劫持的 DNS 目标 |
| `auto-route` | 自动配置路由表 |
| `auto-redirect` | 自动配置 iptables 重定向 TCP（**仅 Linux**） |
| `strict-route` | 把全部连接路由进 TUN 防泄漏（会让本机无法被其它设备访问） |
| `route-address` | 启用 `auto-route` 时用自定义路由替代默认路由 |
| `disable-icmp-forwarding` | 禁用 ICMP 转发，避免某些 ICMP 环回问题（代价是 ping 不显示真实延迟） |
| `endpoint-independent-nat` | 启用端点无关的 NAT |
| `include-interface` / `exclude-interface` | 限制 / 排除被路由的接口（**互斥**） |
| `include-uid` / `exclude-uid` | 按 UID 限制（**仅 Linux**，且需 `auto-route`） |

> ⚠️ `auto-redirect`、`route-address-set`、`gso`、UID 相关字段**仅 Linux 支持**；
> 在别的平台上写了不会报错，只是不生效。

---

## 1.7 嗅探（sniffer）

`sniffer` 用于从流量中还原出域名（例如直连 IP 但带 TLS SNI 的请求），
让域名规则仍能命中。字段位于官方配置的 `sniffer:` 段。

> 与 Surge 的 `extended-matching` 目标相同、**实现与配置项完全不同**。

---

## 1.8 其它全局字段

| 字段 | 说明 |
|---|---|
| `hosts` | 本地 DNS 映射（域名 -> IP，支持通配） |
| `profile` | 选择记录等持久化信息 |
| `tunnels` | 隧道（one-line config） |
| `listeners` | 自定义入站监听（http / socks / mixed / tun / ss / vmess / vless / trojan / anytls / hysteria2 / tuic…） |
| `experimental` | 实验性开关 |
| `tls` | 出站 / API 的证书配置（`certificate` / `private-key` / `custom-certifactes`） |
| `etag-support` / `global-ua` | 元数据与全局 UA |
| `keep-alive-idle` / `keep-alive-interval` / `disable-keep-alive` | TCP keep-alive 控制 |
| `unified-delay` / `tcp-concurrent` | 延迟与并发策略 |

> 完整字段以官方 `docs/config.yaml` 为准 —— 该文件的哈希由本仓库
> `tools/docs_watch.py` 每日盯住，字段增删会立刻反映出来。
