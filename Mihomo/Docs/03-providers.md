# 03 · Providers（代理集合 / 规则集合）

> 返回 [readme.md](readme.md)

Providers 让你把**节点或规则外置**，mihomo 按 `interval` 自动拉取更新。
本仓库的规则集就是通过 `rule-providers` 接入的。

---

## 3.1 两类 Provider

| 段 | 作用 | 引用方式 |
|---|---|---|
| `proxy-providers` | 外置**节点**集合 | 策略组的 `use:` 字段 |
| `rule-providers` | 外置**规则**集合 | `rules:` 里的 `RULE-SET,<名字>,策略` |

---

## 3.2 `rule-providers` 字段

```yaml
rule-providers:
  special:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/Special.yaml"
    path: ./ruleset/Special.yaml
    interval: 43200
    proxy: DIRECT
    # size-limit: 10240
```

| 字段 | 说明 |
|---|---|
| `type` | **必填**：`http`（远程）/ `file`（本地）/ `inline`（内联） |
| `behavior` | `domain` / `ipcidr` / `classical` —— 决定 **payload 怎么写** |
| `format` | `yaml` / `text` / `mrs`，**默认 `yaml`** |
| `url` | 远程地址（`type: http` 时必填） |
| `path` | 本地缓存路径。不填则默认存到 Home Dir 的 `rules` 目录、文件名为 URL 的 MD5 |
| `interval` | 更新间隔（**秒**） |
| `proxy` | 经指定代理下载 / 更新 |
| `size-limit` | 文件大小上限（字节），`0` = 不限 |
| `payload` | `inline` 的规则内容；`http` / `file` provider 也可用作初始 fallback，成功加载外部文件后替换 |
| `header` | 自定义请求头（拉私有地址时带 token） |
| `path-in-bundle` | 本地文件不存在时，从 Home Dir 的 `BundleMRS.7z` 解压指定路径 |

> ⚠️ `path` **默认只允许写在 mihomo 的 Home Dir 内**。要用别的位置，
> 需通过 `SAFE_PATHS` 环境变量声明额外安全路径
> （语法同系统 `PATH`：Windows 用分号分隔，其它系统用冒号）。

内联写法（不落盘，适合几条规则）：

```yaml
rule-providers:
  tiny:
    type: inline
    behavior: domain
    payload:
      - "+.ads.example.com"
```

---

## 3.3 `behavior` 三态（最容易踩的坑）

> `behavior` 必须与 payload 语法一致。错误条目可能被跳过并记录警告，
> 可能导致加载失败，也可能被误读成无法正确匹配的条目；
> 应同时检查 provider 的条目数和日志，不能只看能否启动。

| behavior | 匹配方式 | payload 写法 | 性能 |
|---|---|---|---|
| `domain` | 域名 trie | `+.foo.com`（后缀，**含自身**）/ `foo.com`（精确） | 最快 |
| `ipcidr` | IP 段 | 裸 CIDR：`1.2.3.0/24` | 快 |
| `classical` | 完整规则行 | `DOMAIN-SUFFIX,foo.com`、`IP-CIDR,...`、逻辑规则 | 最慢（逐条） |

### `domain` 的 payload 写法

| 写法 | 含义 |
|---|---|
| `+.foo.com` | 匹配 `foo.com` **及其所有子域**（等价 Surge 的 `DOMAIN-SUFFIX`） |
| `foo.com` | **只**匹配精确的 `foo.com`，不匹配 `a.foo.com` |
| `.foo.com` | 只匹配子域，**不含** `foo.com` 本身 |
| `*.foo.com` | 只匹配**一级**子域 |

> ⚠️ 只有 `+.` 才是"后缀且含自身"。想要 `DOMAIN-SUFFIX` 的语义就用 `+.foo.com`。

---

## 3.4 `format`：`yaml` / `text` / `mrs`

| 格式 | 说明 |
|---|---|
| `yaml` | 默认。`payload:` 下列出条目 |
| `text` | 纯文本，一行一条 |
| `mrs` | mihomo 专用二进制（zstd + succinct trie）。**仅支持 `domain` 与 `ipcidr`** |

> ⚠️ **`classical` 不能用 `mrs`。** mihomo 的 `convert-ruleset` 对 classical
> 会返回 `ErrInvalidFormat`，命令行封装下表现为 panic —— 所以本仓库的
> `classical` 类文件只提供 `.yaml`。

---

## 3.5 本仓库的规则集怎么接

**下面示例中的文本 Rule Provider 使用 `classical` 格式**
（payload 里是完整规则行）：

`Advertising.mrs` 使用 `behavior: domain` 与 `format: mrs`；
完整去广告示例见 [Advertising/readme.md](../Advertising/readme.md)。

```yaml
payload:
  - DOMAIN-SUFFIX,steamserver.net
  - DOMAIN,trts.baishancdnx.cn
```

→ 引用时必须 `behavior: classical`：

```yaml
rule-providers:
  special:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/Special.yaml"
    path: ./ruleset/Special.yaml
    interval: 43200
  adblock:
    type: http
    behavior: domain
    format: mrs
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.mrs"
    path: ./ruleset/Advertising.mrs
    interval: 43200
  adblock-extra:
    type: http
    behavior: classical
    format: yaml
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.Extra.yaml"
    path: ./ruleset/Advertising.Extra.yaml
    interval: 43200

rules:
  - RULE-SET,adblock,REJECT
  - RULE-SET,adblock-extra,REJECT
  - RULE-SET,special,Proxy
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,Proxy
```

完整规则行文本应使用 `classical`，上例的 `Advertising.mrs` 则应使用
`domain` + `mrs`。CNB 镜像只需替换下载 URL 的前缀，provider 的格式保持不变，
具体地址见 [readme.md](readme.md)。

启动时优先加载有效本地缓存或 Bundle；已加载的 provider 更新失败时保留原规则。
没有可用缓存、Bundle 或 fallback payload 且首次获取失败时，集合可能为空，
未命中的请求继续匹配后续规则。来源：
[provider fallback](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/rules/provider/provider.go#L138)、
[资源加载流程](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/component/resource/fetcher.go#L56)。

---

## 3.6 `proxy-providers`

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
    use:
      - mysub
```

| 字段 | 说明 |
|---|---|
| `type` | `http` / `file` / `inline` |
| `interval` | 订阅更新间隔（**秒**） |
| `health-check` | 周期健康探测，给策略组提供可用性信息；不会删除 provider 的节点定义 |
| `use`（写在策略组里） | 把 provider 的节点整体引入该组 |

> `proxy-providers` 还支持 `age-secret-key` 解密 age armor 格式的加密配置
> （`mihomo age keygen` 生成密钥）。

---

## 3.7 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 规则集"没生效" | `behavior` 与 payload 语法不匹配，条目被跳过、误读或加载失败 | 核对三态写法、日志和条目数 |
| 本地路径被拒 | 路径不在 Home Dir 内 | 用 `SAFE_PATHS` 环境变量声明额外安全路径 |
| 启动报 `unsupported vehicle type` | `type` 写错（只接受 `http` / `file` / `inline`） | 改对类型 |
| `yaml: unmarshal` 报错 | 把 `.mrs` 当 `format: yaml` 读（或反之） | 显式写对 `format` |
| 只匹配自身不匹配子域 | payload 用了 `foo.com` 而非 `+.foo.com` | 改成 `+.foo.com` |
| IP 规则导致解析变慢 | 匹配时主动解析了尚无目标 IP 的域名 | 按需在 IP 条目或集合引用行加 `no-resolve`（见 [04](04-rules.md)） |
| `nameserver-policy` 的 `rule-set:` 不生效 | 名字没在 `rule-providers` 里定义 | 补定义（见 [02-dns.md](02-dns.md)） |
