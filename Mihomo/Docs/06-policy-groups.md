# 06 · 代理组（策略组）

> 返回 [readme.md](readme.md)

---

## 6.1 基本形态

```yaml
proxy-groups:
  - name: "Proxy"
    type: select
    proxies:
      - Auto
      - DIRECT
  - name: "Auto"
    type: url-test
    url: http://cp.cloudflare.com/generate_204
    interval: 300
    proxies:
      - NodeA
      - NodeB
```

---

## 6.2 组类型

| 类型 | 行为 |
|---|---|
| `select` | 手动选一个 |
| `url-test` | 自动选延迟最好的 |
| `fallback` | 按顺序选第一个可用的 |
| `load-balance` | 在可用成员间分摊 |
| `relay` | 链式代理（多跳） |

---

## 6.3 成员来源

一个组的成员可以来自三处：

| 来源 | 字段 |
|---|---|
| 显式列出 | `proxies: [NodeA, DIRECT]` |
| 引入整个 provider | `use: [mysub]` |
| 自动纳入 | `include-all` / `include-all-proxies` / `include-all-providers` |

> ⚠️ 组里必须有 `use` 或 `proxies` 之一，否则启动报
> `` `use` or `proxies` missing ``。

```yaml
  - name: "All"
    type: select
    use:
      - mysub
    proxies:
      - DIRECT
```

---

## 6.4 常用参数

| 参数 | 说明 |
|---|---|
| `url` / `interval` | 测速地址与间隔 |
| `timeout` | 测试超时 |
| `lazy` | 惰性测速（用到才测） |
| `filter` / `exclude-filter` | 按正则筛选 / 排除成员 |
| `exclude-type` | 按类型排除成员 |
| `expected-status` | 期望的 HTTP 状态码 |
| `max-failed-times` | 连续失败几次后判定不可用 |
| `empty-fallback` | 组内无可用节点时的兜底策略 |
| `disable-udp` | 该组禁用 UDP |
| `hidden` | 在界面上隐藏 |
| `icon` | 图标 |

### `filter` 示例

```yaml
  - name: "HK"
    type: url-test
    use: [mysub]
    filter: "(?i)hk|hongkong|香港"
    exclude-filter: "(?i)expire|到期"
```

> `filter` / `exclude-filter` 用正则匹配**节点名**，
> 是"从订阅里自动挑出一类节点"的主要手段。

---

## 6.5 链式代理 `relay`

```yaml
  - name: "Relay"
    type: relay
    proxies:
      - FrontNode
      - BackNode
```

流量先经 `FrontNode` 再经 `BackNode`。

> 与 Surge 的 `underlying-proxy`（整组指定底层代理）**不是一回事**，
> 配置模型完全不同。

---

## 6.6 与 provider 的配合

```yaml
proxy-providers:
  mysub:
    type: http
    url: "https://example.com/sub?token=xxx"
    path: ./sub/mysub.yaml
    interval: 86400
    health-check:
      enable: true
      url: http://cp.cloudflare.com/generate_204
      interval: 300

proxy-groups:
  - name: "Proxy"
    type: select
    use: [mysub]
    proxies: [DIRECT]
```

> `health-check` 写在 **provider** 内，作用于该 provider 的全部节点；
> 组的 `url` / `interval` 是**组级测速**。两者可以并存，作用范围不同。

---

## 6.7 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动报 `` `use` or `proxies` missing `` | 组里两个都没写 | 至少写一个 |
| 组内节点为空 | `filter` 正则没匹配到，或 provider 没拉到 | 检查正则与 provider 状态 |
| 报 `duplicate provider name` | provider 名字与组名冲突 | 改名 |
| 想看某节点为什么不被选 | 先看测速结果与 `expected-status` | 用 API 查组状态（见 [07](07-operations.md)） |
