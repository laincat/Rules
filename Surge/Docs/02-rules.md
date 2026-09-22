# 02 · 规则

> 返回 [readme.md](readme.md)

---

## 2.1 求值顺序

规则**自上而下**逐条测试，命中即停：

```
[Rule]
DOMAIN-SUFFIX,company.com,ProxyA
DOMAIN-KEYWORD,google,DIRECT
GEOIP,US,DIRECT
IP-CIDR,192.168.0.0/16,DIRECT
FINAL,ProxyB
```

两种情况会**绕过**正常的自上而下求值：

1. 带 `pre-matching` 的规则被抽出，在**所有其他规则之前**检查。
2. 出站模式是 **Direct** 或 **Global**（非 Rule-Based）时，完全不查询规则列表。

> **硬性要求**：规则列表**必须以一条已启用的 `FINAL` 结尾**。
> `FINAL` 永远命中，所以写在它下面的规则永远不会生效；
> 若有多条启用的 `FINAL`，**最后一条**才是生效的那条。

---

## 2.2 规则类型

### 域名类

| 类型 | 匹配 |
|---|---|
| `DOMAIN` | 精确域名 |
| `DOMAIN-SUFFIX` | 域名后缀（含自身） |
| `DOMAIN-KEYWORD` | 域名关键字 |
| `DOMAIN-WILDCARD` | 通配（如 `cdn?.example.com`） |
| `DOMAIN-SET` | 外部**纯域名列表**，见 [03](03-ruleset.md) |

匹配**不区分大小写**。

### IP 类

| 类型 | 说明 |
|---|---|
| `IP-CIDR` / `IP-CIDR6` | IPv4 / IPv6 网段 |
| `GEOIP` | 按国家码或服务类别匹配 |
| `IP-ASN` | 按自治系统号匹配 |

### 其它

| 类型 | 说明 |
|---|---|
| `USER-AGENT` / `URL-REGEX` | HTTP 层 |
| `PROCESS-NAME` | 进程名（Mac） |
| `SRC-IP` / `SRC-PORT` / `DEST-PORT` / `IN-PORT` | 来源与端口 |
| `DEVICE-NAME` / `MAC-ADDRESS` | 设备（网关模式） |
| `PROTOCOL` / `HOSTNAME-TYPE` / `CELLULAR-RADIO` / `CELLULAR-CARRIER` / `SUBNET` | 协议、主机名类型、蜂窝与子网 |
| `AND` / `OR` / `NOT` | 逻辑规则 |
| `SCRIPT` | 脚本规则 |
| `RULE-SET` | 外部 / 内联规则集合，见 [03](03-ruleset.md) |
| `FINAL` | 兜底 |

---

## 2.3 规则与 DNS 的交互

- 请求目标是域名时，求值会**停在第一条 IP 类规则**上：Surge 先做 DNS 解析，
  再从这一条继续。结果会被缓存，所以每个请求**最多解析一次**。
- 加 `no-resolve` 后，IP 类规则对**尚未解析**的请求**直接跳过**，不触发解析。
- 若 DNS 解析失败，规则求值中止、请求以 DNS 错误失败 ——
  除非 `FINAL` 带了 `dns-failed` 参数。

> ⚠️ 对域名请求把 IP 类规则写在前面且忘了 `no-resolve`，会让**每个**域名请求
> 都先解析一次 —— 这是配置变慢最常见的单一原因。

---

## 2.4 规则参数

| 参数 | 适用类型 | 说明 |
|---|---|---|
| `no-resolve` | `IP-CIDR`、`IP-CIDR6`、`GEOIP`、`IP-ASN`、`RULE-SET`、`DOMAIN-SET` | 未解析的域名请求跳过该规则，而不是触发 DNS。写在 `RULE-SET` / `DOMAIN-SET` 上时**作用于集合内每条** |
| `extended-matching` | `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`DOMAIN-WILDCARD`、`URL-REGEX`、`RULE-SET`、`DOMAIN-SET` | 额外匹配 **TLS SNI** 与 **HTTP `Host`**（或 `:authority`），处理"直连 IP 但带 SNI"的情况 |
| `pre-matching` | 域名类、IP 类、`SRC-IP`、`DEST-PORT`、`SRC-PORT`、`SUBNET`、`CELLULAR-*`、逻辑规则、`RULE-SET`、`DOMAIN-SET` | 在预匹配阶段求值。**仅顶层规则**，策略必须属 REJECT 家族 |
| `dns-failed` | **仅 `FINAL`** | DNS 解析失败时改用 `FINAL` 的策略，而不是报 DNS 错误 |
| `update-interval=<秒>` | `RULE-SET`、`DOMAIN-SET` | 外部集合重新下载间隔。默认 `86400`；**负值禁用自动更新** |
| `requires-resolve` | **仅 `SCRIPT`** | 先做 DNS 解析再运行规则脚本 |
| `notification-text=<文本>` | 任意规则（含 `FINAL`） | 命中时弹用户通知 |
| `notification-interval=<秒>` | 任意规则（含 `FINAL`） | 同一规则的通知最小间隔，默认 `300` |

> 参数以**逗号分隔的追加段**写在策略之后：
> `DOMAIN,ad.example.com,REJECT,pre-matching`

---

## 2.5 `pre-matching` 详解 `iOS 5.14.0+` `Mac 5.9.0+`

通常规则决策发生在 Surge **收到连接的第一个包之后**。带 `pre-matching` 且策略为
**REJECT 家族**的规则，会**额外在 DNS 查询阶段与 TCP 握手阶段求值**，
从而以最小开销拒绝不需要的请求 —— 这是广告拦截的性能杀手锏。

```
DOMAIN-SET,https://example.com/adlist.txt,REJECT,pre-matching
```

| 约束 | 说明 |
|---|---|
| 仅顶层规则 | 不能写在 `[Ruleset x]` 或逻辑规则的子规则里 |
| 策略必须属 REJECT 家族 | 不能配代理 / `DIRECT` |
| 优先级最高 | 预匹配规则先于所有其他规则求值 |

> ⚠️ 用 `Proxy` 或 `DIRECT` 配 `pre-matching` 不会报错，但**该规则会被忽略**。

---

## 2.6 `extended-matching` 详解 `iOS 5.8.0+` `Mac 5.4.0+`

默认情况下，域名类规则只看请求里的主机名。开启 `extended-matching` 后，
**额外**拿 TLS SNI 与 HTTP `Host` 头（或 `:authority`）去匹配，
用于"客户端直接连 IP、真实域名只出现在 SNI 里"的场景。

```
DOMAIN-SUFFIX,example.com,Proxy,extended-matching
```

写在 `RULE-SET` / `DOMAIN-SET` 行上时，**对集合内每条规则生效**。

---

## 2.7 特殊取值 `UNKNOWN` `iOS 5.22.1+` `Mac 6.9.1+`

`GEOIP` 与 `IP-ASN` 新增 `UNKNOWN` 取值，用于匹配"数据库里查不到"的地址。

---

## 2.8 逻辑规则与带括号的策略名

逻辑规则（`AND` / `OR` / `NOT`）里引用**名字含括号的策略**时，
`Mac 6.10.0`（Beta build 12350）之前会**解析错误**。

> 该问题已在 `Mac 6.10.0` 修复。低于此版本请避免在逻辑规则里引用带括号的策略名。

---

## 2.9 可直接抄的片段

```
[Rule]
# 广告：在 DNS 阶段就拒，不建连、不解析
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/Comics.list,REJECT,pre-matching,extended-matching,"update-interval=21600"

# 中国大陆 IP 直连（IP 类必须 no-resolve）
GEOIP,CN,DIRECT,no-resolve

# 局域网
RULE-SET,LAN,DIRECT,no-resolve

FINAL,Proxy
```

> 收尾必须是 `FINAL` —— 这是配置合法性的硬要求，不是风格建议。
