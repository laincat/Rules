# 04 · 路由规则

> 返回 [readme.md](readme.md)

---

## 4.1 求值顺序与优先级

`rules:` 是一个**有序列表**，自上而下匹配，命中即停，最后通常用 `MATCH` 兜底：

```yaml
rules:
  - DOMAIN-SUFFIX,example.com,Proxy
  - DOMAIN-KEYWORD,google,Proxy
  - GEOIP,CN,DIRECT
  - MATCH,Proxy
```

---

## 4.2 规则类型

### 域名类

| 类型 | 匹配 |
|---|---|
| `DOMAIN` | 精确域名 |
| `DOMAIN-SUFFIX` | 域名后缀（含自身） |
| `DOMAIN-KEYWORD` | 域名关键字 |
| `DOMAIN-WILDCARD` | 通配 |
| `DOMAIN-REGEX` | 域名正则 |
| `GEOSITE` | 地理站点分类 |

### IP 类

| 类型 | 说明 |
|---|---|
| `IP-CIDR` / `IP-CIDR6` | IPv4 / IPv6 网段 |
| `IP-SUFFIX` | IP 后缀匹配 |
| `IP-ASN` | 自治系统号 |
| `GEOIP` | 按国家 / 地区 |
| `SRC-GEOIP` / `SRC-IP-ASN` / `SRC-IP-CIDR` / `SRC-IP-SUFFIX` | 来源地址类 |

### 端口与进程

| 类型 | 说明 |
|---|---|
| `DST-PORT` / `SRC-PORT` / `IN-PORT` | 端口 |
| `PROCESS-NAME` / `PROCESS-PATH` | 进程（各自还有 `-WILDCARD` / `-REGEX` 变体） |
| `UID` | 用户 ID |
| `NETWORK` | 网络类型（`tcp` / `udp`） |
| `DSCP` | DSCP 标记 |

### 入站类

| 类型 | 说明 |
|---|---|
| `IN-TYPE` | 入站类型（`SOCKS` / `HTTP`…） |
| `IN-USER` / `IN-NAME` | 入站用户 / 名称 |
| `REMATCH-NAME` | 重匹配名称 |

### 组合与引用

| 类型 | 说明 |
|---|---|
| `RULE-SET` | 引用 `rule-providers`，见 [03](03-providers.md) |
| `SUB-RULE` | 引用子规则（`sub-rules`），可带条件 |
| `AND` / `OR` / `NOT` | 逻辑规则 |
| `MATCH` | 兜底 |

---

## 4.3 附加参数

写在规则的**策略之后**：

```yaml
- IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
- RULE-SET,ai-ip,Proxy,no-resolve
```

| 参数 | 说明 |
|---|---|
| `no-resolve` | 禁止为当前规则主动解析目标 IP；已有目标 IP 仍可匹配。在 `RULE-SET` 引用行上影响整个集合 |
| `src` | 把该规则切换为「来源地址」语义 |

classical provider 的 IP 条目也支持 `no-resolve`，只影响该条：

```yaml
payload:
  - IP-CIDR,192.168.0.0/16,no-resolve
```

`domain`／`ipcidr` payload 是域名／CIDR 列表，不能附带完整规则参数。
来源：[classical 参数解析](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/rules/provider/classical_strategy.go#L51)、
[IP 规则解析行为](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/rules/common/ipcidr.go#L38)。

---

## 4.4 逻辑规则

```yaml
- AND,((DOMAIN-SUFFIX,example.com),(NETWORK,tcp)),Proxy
- OR,((DOMAIN-KEYWORD,google),(DOMAIN-KEYWORD,youtube)),Proxy
- NOT,((GEOIP,CN)),Proxy
```

> 语法与 Surge 的逻辑规则**恰好一致**（`LOGIC,((子规则),(子规则)),策略`），
> 但**可用子规则类型不同**，别直接照抄：
>
> | | Surge | mihomo |
> |---|---|---|
> | 网络类型 | `PROTOCOL,UDP` | `NETWORK,udp` |
> | 网络环境 | `SUBNET,TYPE:CELLULAR` | — |
> | 进程 | `PROCESS-NAME` | `PROCESS-NAME` / `UID` |
> | 脚本 | `SCRIPT` 可作子规则 | 无 |
>
> 另注：Surge 的逻辑规则嵌套上限为 **10 层**；mihomo 官方文档未给出同类上限。

---

## 4.5 `MATCH` 兜底

```yaml
- MATCH,Proxy
```

`MATCH` 永远命中，等价于 Surge 的 `FINAL`。

provider 更新失败时通常继续使用已经加载的规则；首次获取失败且没有可用缓存、
Bundle 或 fallback payload 时，集合可能为空。未命中的请求仍按顺序检查后续规则，
并不一定放行或直接落到 `MATCH`。排错先确认 provider 是否有有效规则，
详见 [03-providers.md](03-providers.md)。

---

## 4.6 可直接抄的片段

```yaml
rules:
  # 去广告
  - RULE-SET,adblock,REJECT
  - RULE-SET,adblock-extra,REJECT
  # 常规分流
  - RULE-SET,special,Proxy
  # 国内直连
  - GEOIP,CN,DIRECT,no-resolve
  # 兜底
  - MATCH,Proxy
```

配合 `rule-providers` 定义见 [03-providers.md](03-providers.md)。

---

## 4.7 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| IP 规则让域名请求变慢 | 缺 `no-resolve` | 加到引用行上 |
| 规则整体不生效 | `mode` 是 `global` / `direct` | 改回 `rule` |
| `GEOIP` / `GEOSITE` 全不命中 | geodata 未就绪 | 见 [05-geodata.md](05-geodata.md) |
| 某条规则"跳过"了 | 前面的规则先命中了 | 调整顺序 |
