# 02 · DNS 子系统

> 返回 [readme.md](readme.md)

---

## 2.1 是否启用 mihomo 自己的 DNS

```yaml
dns:
  enable: false            # false 时使用系统 DNS
  listen: 0.0.0.0:53       # 开启 DNS 服务器监听
```

> 想用 `fake-ip`、`nameserver-policy`、`hosts` 这些能力，必须先 `enable: true`。
> 只把「DNS 交给上游」不需要它。

---

## 2.2 `default-nameserver`

用于**解析其它 DNS 服务器自身的域名**（`nameserver`、`fallback` 等里的
DoH / DoT 地址）。因此**只能填纯 IP 地址**，但可以是加密 DNS 形式：

```yaml
dns:
  default-nameserver:
    - 114.114.114.114
    - 8.8.8.8
    - tls://1.12.12.12:853
    - system                 # 追加系统配置里的 DNS
```

> ⚠️ 这里填域名会解析不了 —— 它存在的意义正是"在没有可用 DNS 时先把 DNS 服务器
> 的域名解析出来"，属于先有鸡还是先有蛋的那一环。

---

## 2.3 `enhanced-mode`

```yaml
dns:
  enhanced-mode: fake-ip     # 或 redir-host
  fake-ip-range: 198.18.0.1/16
  # fake-ip-range6: fdfe:dcba:9876::1/64
  fake-ip-filter:            # 不做 fake-ip 的域名
    - "*.lan"
```

| 模式 | 行为 |
|---|---|
| `fake-ip` | 立刻返回伪 IP，连接到达时还原域名。**不引入解析延迟，且规则能看到原始域名** |
| `redir-host` | 走真实解析 |

> `fake-ip` 的好处与 Surge 的 Fake-IP 一致（详见
> [Surge/Docs/04-dns-and-policy.md](../../Surge/Docs/04-dns-and-policy.md) 4.3），
> 但**两边的配置项名字完全不同**，不能互相照抄。

`fake-ip-filter` 用于排除需要真实 IP 的域名（游戏机 NAT 检测之类）。

---

## 2.4 上游 DNS 服务器

```yaml
dns:
  nameserver:
    - https://doh.pub/dns-query
    - tls://223.5.5.5:853
  fallback:
    - https://1.1.1.1/dns-query
  fallback-filter:
    geoip: true
    geoip-code: CN
```

支持的地址形式：

| 形式 | 示例 |
|---|---|
| 明文 UDP | `8.8.8.8` |
| DoT | `tls://1.12.12.12:853` |
| DoH | `https://doh.pub/dns-query` |
| DoH over HTTP/3 | 配合 `prefer-h3: true` |
| 系统 DNS | `system` |

---

## 2.5 `nameserver-policy`

按域名指定专用 DNS —— 最常用于「国内域名用国内 DNS、国外域名用国外 DNS」：

```yaml
dns:
  nameserver-policy:
    "geosite:cn,private,apple": https://doh.pub/dns-query
    "geosite:category-ads-all": rcode://success
```

键支持 `geosite:` / `geoip:` 前缀、域名后缀与通配；值可以是单个服务器或列表。

> ⚠️ 旧写法 `dns.fallback` 里的 `geosite:` 过滤**已废弃**，官方标注
> 「请使用 `nameserver-policy`」。

---

## 2.6 其它常用字段

| 字段 | 说明 |
|---|---|
| `cache-algorithm` | DNS 缓存算法（如 `arc`） |
| `prefer-h3` | DoH 是否并发尝试 HTTP/3 |
| `ipv6` | `false` 时对 AAAA 返回空结果 |
| `ipv6-timeout` | 双栈并发时等待 AAAA 的毫秒数（默认 100ms） |
| `hosts` | 本地映射（也可写在顶层） |
| `listen` | DNS 服务监听地址 |

---

## 2.7 排错

| 现象 | 先查 |
|---|---|
| `dns` 配置完全不生效 | `enable: true` 了吗 |
| 启动即报 DNS 相关错误 | `default-nameserver` 里是不是填了域名而非 IP |
| 某类域名解析到 `198.18.x.x` | `fake-ip` 的正常表现；需要真实 IP 的域名加进 `fake-ip-filter` |
| 国内域名解析到国外 IP | `nameserver-policy` 未配置，或 `fallback-filter` 的 `geoip-code` 不对 |
| 改了 `fallback` 里的 `geosite:` 没用 | 该写法已废弃，改用 `nameserver-policy` |
| 规则里 `rule-set:` 引用 DNS 策略不生效 | 该 provider 名字没在 `rule-providers` 定义 |
