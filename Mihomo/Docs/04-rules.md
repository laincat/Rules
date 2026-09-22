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
| `no-resolve` | 域名请求**跳过**该 IP 类规则，不触发 DNS。**在 `RULE-SET` 上作用于每条子规则** |
| `src` | 把该规则切换为「来源地址」语义 |

> ⚠️ `no-resolve` 必须写在 **`rules:` 的引用行**上，
> **写进 provider 内部是无效的** —— 这是最常被写错的一处。

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

> ⚠️ **provider 拉取失败时集合为空、什么也匹配不到**，
> 请求会径直落到 `MATCH` 上。所以"规则好像没生效"的现象，
> 首先要确认 provider 是否真的加载成功了。

---

## 4.6 可直接抄的片段

```yaml
rules:
  # 去广告
  - RULE-SET,comic,REJECT
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
