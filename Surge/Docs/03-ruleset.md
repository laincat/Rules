# 03 · 规则集：`RULE-SET` 与 `DOMAIN-SET`

> 返回 [readme.md](readme.md)

两者都能把长长的规则列表挪出主配置，但**匹配模型完全不同**。
选错不会报错，只会让规则**静默失效**或**变慢**。

---

## 3.1 一张表看懂区别

| 对比项 | `RULE-SET` | `DOMAIN-SET` |
|---|---|---|
| 文件内容 | **完整规则行**（`DOMAIN-SUFFIX,foo.com`） | **一行一个纯域名**（`foo.com`） |
| 能表达 | 任意规则类型（域名 / IP / 逻辑…） | **只有域名** |
| 查找方式 | 通用容器，逐条判断 | **预处理成索引**，专为超大型列表设计 |
| 规模上限 | — | 单个集合最高 **1,000,000** 条 |
| 内置集合 | `SYSTEM`、`LAN` | — |
| 典型用途 | 混合类型的小集合 | 20 万条级的广告域名 |

> ⚠️ **官方硬性约束：同一个 URL / 文件，不能在同一份配置里既当 `RULE-SET`
> 又当 `DOMAIN-SET`。** 两种引用方式的解析结果不同，混用必然有一边是错的。

---

## 3.2 `DOMAIN-SET` 的文件格式

纯文本，一行一条：

```
# 精确域名
example.com
# 前导 . = 该域名及其全部子域
.ads.example.net
```

- 以 `#` 开头的是注释；
- **非法行会被跳过并给出警告，不会让整个集合失效**；
- `DOMAIN-SET` 行支持 `update-interval=<秒>` 参数（默认 `86400`，负值禁用自动更新）；
- 本地文件会被**监视并自动重载**。

---

## 3.3 `RULE-SET` 的文件格式

一行一条规则，但**不写策略部分**（策略在引用行上给）：

```
# 注释行以 #、// 或 ; 开头
DOMAIN-SUFFIX,example.com
DOMAIN,cdn.example.org,extended-matching
IP-CIDR,203.0.113.0/24,no-resolve
IP-ASN,13335
```

行内可以带自己的参数（`no-resolve` / `extended-matching`）。

> 引用时给的那个策略会**应用到集合内每一条**规则上。

---

## 3.4 值的解析顺序

`RULE-SET` 的值按以下顺序解析：

1. **内置集合名**：`SYSTEM` 或 `LAN`；
2. **内联集合**：profile 里 `[Ruleset <name>]` section 的名字；
3. **外部资源**：`http://` / `https://` URL，或本地文件路径（绝对，或相对于
   profile 目录）。

### 内置集合

```
RULE-SET,SYSTEM,DIRECT
RULE-SET,LAN,DIRECT,no-resolve
```

- `SYSTEM` —— macOS / iOS 自身发出的大部分请求（不含 App Store / iTunes 内容服务）；
- `LAN` —— 私有与特殊用途网段，外加 `.local` 后缀。

> ⚠️ `LAN` **含域名规则**（`DOMAIN-SUFFIX,local`）。不加 `no-resolve` 时，
> 它会给域名请求触发一次 DNS 解析 —— 这是 LAN 规则最常见的性能坑。
>
> ⚠️ 内置集合的**具体内容会随 Surge 版本变化**，以 App 内展示的为准。

---

## 3.5 内联规则集 `Mac 5.3.1+`

把规则直接写在 profile 里，用一个 section 承载：

```
[Ruleset Streaming]
DOMAIN-SUFFIX,netflix.com
DOMAIN-SUFFIX,netflix.net

[Rule]
RULE-SET,Streaming,StreamingProxy
```

内联集合与外部文件**语法一致**，也享受同样的预处理优化。
`iOS 5.22.0+` / `Mac 6.9.0+` 起可以直接在规则编辑器里创建与编辑，
包括逐条排序和开关。

> 模块（`.sgmodule`）也可以提供内联规则集。

---

## 3.6 同名内联规则集：`Mac 6.10.0` 是分界线

内联规则集（`[Ruleset <name>]`）引用的是**名字**，所以主配置与模块很容易撞名。
撞名时的行为在 `Mac 6.10.0` 前后**完全不同**：

| 版本 | 主配置与模块定义了同名内联规则集时 |
|---|---|
| **< `Mac 6.10.0`** | **相互替换** —— 只有一份生效，谁赢取决于加载顺序 |
| **`Mac 6.10.0+`** | **合并** —— 两侧的规则**都会保留** |

官方在 `6.10.0` Beta 的发布说明里写的是：

> Inline rule sets with the same name now merge across the main profile and modules
> instead of replacing one another, preserving rules contributed by each source.

配套的手册条目还补了一条限制：

> Since the order inside a rule set has no effect, a module cannot remove or reorder
> existing lines.

→ **模块只能往里加，不能删也不能重排。**

### 实践含义

- 升级到 `6.10.0+` 后，同一份配置的**实际规则数可能变多**（此前被覆盖的那些回来了）。
  如果某域名突然被拦或被放行，先按「同名内联规则集」方向排查；
- **写模块时给内联规则集起带前缀的名字**（如 `[Ruleset LaincatAds]`），
  避免与主配置或其它模块撞名 —— 撞名在旧版是「覆盖」、在新版是「叠加」，
  两种都不是可预期的行为；
- 本仓库的 `.sgmodule` **不受影响**：它们引用的是远程 `DOMAIN-SET` / `RULE-SET`
  地址，不是内联规则集。

---

## 3.7 本仓库的产物怎么引用

本仓库 `Surge/` 下的 `.list` 是**完整规则行**格式：

```
DOMAIN-SUFFIX,steamserver.net
DOMAIN,trts.baishancdnx.cn
```

→ 它们**只能**用 `RULE-SET` 引用，**不能用 `DOMAIN-SET`**。

```
[Rule]
# 去广告（本仓库列表，REJECT）
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/Comics.list,REJECT,pre-matching,extended-matching,"update-interval=21600"

# 常规分流
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Ozon.list,Proxy,extended-matching,"update-interval=21600"
```

订阅型模块（`.sgmodule`）更适合直接整包引用 —— 元数据、策略、参数都已配好。

---

## 3.8 性能取舍

| 做法 | 代价 |
|---|---|
| 20 万条域名走 `DOMAIN-SET` | 索引化，常数级查找 —— **这是正确做法** |
| 20 万条域名硬塞进 `RULE-SET` | 通用容器逐条判断，明显变慢 |
| 域名请求前放未加 `no-resolve` 的 IP 规则 | 每个域名请求先解析一次 |
| 对含域名规则的集合漏加 `no-resolve` | 同上（`LAN` 是典型） |

> 广告拦截场景的正确组合：**纯域名 → `DOMAIN-SET`；混合类型 → `RULE-SET`**。
