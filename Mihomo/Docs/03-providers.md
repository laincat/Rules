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
| `payload` | **仅 `type: inline`** 时生效 |
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

> ⚠️ **`behavior` 填错不会报错，而是规则静默全部失效。**

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

**本仓库 `Mihomo/` 下的 Rule Provider 文件都是 `classical` 格式**
（payload 里是完整规则行）：

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
  comic:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Comic.yaml"
    path: ./ruleset/Comic.yaml
    interval: 43200

rules:
  - RULE-SET,special,Proxy
  - RULE-SET,comic,REJECT
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,Proxy
```

> ⚠️ 写成 `behavior: domain` 会导致**一条都不命中**且**没有任何报错**。

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
| `health-check` | 节点健康探测（自动剔除不可用节点） |
| `use`（写在策略组里） | 把 provider 的节点整体引入该组 |

> `proxy-providers` 还支持 `age-secret-key` 解密 age armor 格式的加密配置
> （`mihomo age keygen` 生成密钥）。

---

## 3.7 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 规则集"没生效" | `behavior` 与 payload 语法不匹配 → **静默失效** | 核对三态写法 |
| 本地路径被拒 | 路径不在 Home Dir 内 | 用 `SAFE_PATHS` 环境变量声明额外安全路径 |
| 启动报 `unsupported vehicle type` | `type` 写错（只接受 `http` / `file` / `inline`） | 改对类型 |
| `yaml: unmarshal` 报错 | 把 `.mrs` 当 `format: yaml` 读（或反之） | 显式写对 `format` |
| 只匹配自身不匹配子域 | payload 用了 `foo.com` 而非 `+.foo.com` | 改成 `+.foo.com` |
| IP 规则导致解析变慢 | 引用行漏了 `no-resolve` | 加 `no-resolve` |
| `nameserver-policy` 的 `rule-set:` 不生效 | 名字没在 `rule-providers` 里定义 | 补定义（见 [02-dns.md](02-dns.md)） |
