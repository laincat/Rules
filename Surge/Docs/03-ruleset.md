# 03 · 规则集：`RULE-SET` 与 `DOMAIN-SET`

> 本章来源：[官方原文 1](https://manual.nssurge.com/rules/ruleset.html)。
> [来源范围与版本约定](sources.md)；本文示例为配置片段。

> 返回 [readme.md](readme.md)

两者都能把长长的规则列表挪出主配置，但**匹配模型完全不同**。
类型必须与文件内容匹配；加载后检查规则详情与日志，不能只看订阅下载成功。

---

## 3.1 一张表看懂区别

| 对比项 | `RULE-SET` | `DOMAIN-SET` |
|---|---|---|
| 文件内容 | **完整规则行**（`DOMAIN-SUFFIX,foo.com`） | **一行一个纯域名**（`foo.com`） |
| 能表达 | 任意规则类型（域名 / IP / 逻辑…） | **只有域名** |
| 查找方式 | 依规则类型预处理：域名与 IP 有索引，其余类型线性匹配 | **预处理成域名索引** |
| 规模上限 | 单个集合最高 **1,000,000** 条 | 单个集合最高 **1,000,000** 条 |
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

## 3.6 同名内联规则集：`iOS 5.23.0` / `Mac 6.10.0` 起合并

内联规则集（`[Ruleset <name>]`）引用的是**名字**，所以主配置与模块很容易撞名。
撞名时的行为在以下平台版本前后**完全不同**：

| 版本 | 主配置与模块定义了同名内联规则集时 |
|---|---|
| **iOS < `5.23.0` / Mac < `6.10.0`** | **相互替换** —— 只有一份生效，谁赢取决于加载顺序 |
| **iOS `5.23.0+` / Mac `6.10.0+`** | **合并** —— 两侧的规则**都会保留** |

`Mac 6.10.0` / `iOS 5.23.0` 已正式发布。官方发布说明确认该变化：

> Inline rule sets with the same name now merge across the main profile and modules
> instead of replacing one another, preserving rules contributed by each source.

来源：[Surge Mac 稳定版官方发布说明](https://nssurge.com/mac/latest/appcast-signed.xml)及 [Surge 官方 Telegram 发布公告](https://t.me/SurgeTestFlightFeed/417)。

配套的手册条目还补了一条限制：

> Since the order inside a rule set has no effect, a module cannot remove or reorder
> existing lines.

→ **模块只能往里加，不能删也不能重排。**

### 实践含义

- 升级到 `iOS 5.23.0+` / `Mac 6.10.0+` 后，同一份配置的**实际规则数可能变多**（此前被覆盖的那些回来了）。
  如果某域名突然被拦或被放行，先按「同名内联规则集」方向排查；
- **写模块时给内联规则集起带前缀的名字**（如 `[Ruleset LaincatAds]`），
  避免与主配置或其它模块撞名 —— 撞名在旧版是「覆盖」、在新版是「合并」，
  两种都不是可预期的行为；
- 本仓库的 `.sgmodule` **不受影响**：它们引用的是远程 `DOMAIN-SET` / `RULE-SET`
  地址，不是内联规则集。

---

## 3.7 本仓库的产物怎么引用

见 [本仓库接入](repository-recipes.md)。本章仅解释官方语法与字段。

---

## 3.8 性能取舍

| 做法 | 代价 |
|---|---|
| 纯域名用 `DOMAIN-SET` | 格式简洁，专用域名索引；符合本仓库主文件格式 |
| 混合类型用 `RULE-SET` | 域名规则预编译索引；超过 1,000 条域名规则用磁盘数据库 |
| `RULE-SET` 的 IP 规则 | 超过 50 条 IP-CIDR 时使用二进制数据库；IP-ASN 使用常数时间查询 |
| 关键词、URL 等其它规则 | 线性匹配；集合较大时应关注这部分规则数量 |
| IP 规则未加 `no-resolve` | 对尚未解析的域名可能触发 DNS；该参数是解析取舍，不是语法必填项 |

> 广告拦截场景的正确组合：**纯域名 → `DOMAIN-SET`；混合类型 → `RULE-SET`**。
> 来源：[官方规则集性能说明](https://manual.nssurge.com/rules/ruleset.md)。

## 补充官方参考

- [官方原文：domain](https://manual.nssurge.com/rules/domain.html)
