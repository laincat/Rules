# Surge · Ruleset 目录

> `Advertising` / `AI` / `Ozon` 三套由 `tools/gen_rulesets.py` 自动生成
>（GitHub Actions `gen-rulesets.yml` 每日运行），**请勿手改**；
> `Special` / `Custom` / `Comics` / `Japan` 为手工维护。
>
> 自动生成的三套均为**双文件**：`<Name>.list`（纯域名，走 `DOMAIN-SET`）
> 与 `<Name>.Extra.list`（非域名类型，走 `RULE-SET`）。

## 目录清单

| 文件 | 内容 | 建议策略 |
|---|---|---|
| `Advertising.list` | 去广告域名集（46 万条，四源合并去重 + 白名单回剔） | `REJECT` |
| `Advertising.Extra.list` | 去广告补充（DOMAIN-KEYWORD，4 条） | `REJECT` |
| `Special.list` | 手动置顶的特殊条目（游戏下载加速、国内白名单等） | `nProxy` |
| `Custom.list` | 手动自定义（Mastodon、Steam 下载分流等） | `Proxy` |
| `Ozon.list` | Ozon 电商域名（46 条：静态基线 + russia portal 动态解析） | `nProxy` |
| `Ozon.Extra.list` | Ozon 补充（DOMAIN-KEYWORD + 自有 ASN 网段，13 条） | `nProxy` |
| `AI.list` | AI 服务域名（OpenAI / Claude / Gemini / Copilot…，280 条） | `Speed-US` |
| `AI.Extra.list` | AI 补充（DOMAIN-KEYWORD + 出口 IP，32 条） | `Speed-US` |
| `Comics.list` | 漫画站 | `Proxy` |
| `Japan.list` | 日本站点的 DLSite / DMM 等 | `Speed-JP` |

## 引用格式：主文件用 `DOMAIN-SET`，Extra 用 `RULE-SET`

主文件（`Advertising.list` / `AI.list` / `Ozon.list`）是**纯域名**，必须用 `DOMAIN-SET`；
`*.Extra.list` 是**完整规则行**（含 `DOMAIN-KEYWORD`、`IP-CIDR`、`IP-ASN`），必须用 `RULE-SET`。
按官方手册，两类集合都会在加载时预处理（域名编译进索引、>50 条 `IP-CIDR` 编译成
二进制库），所以主要收益是**语义正确**：把域名塞给 `RULE-SET`、或把完整规则行塞给
`DOMAIN-SET`，都会静默失效而不是报错。

```ini
DOMAIN-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Advertising.list,REJECT,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Advertising.Extra.list,REJECT,extended-matching,"update-interval=21600"
DOMAIN-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/AI.list,Speed-US,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/AI.Extra.list,Speed-US,extended-matching,"update-interval=21600"
DOMAIN-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Ozon.list,nProxy,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Ozon.Extra.list,nProxy,extended-matching,"update-interval=21600"
```

## 最佳先后顺序

规则自上而下求值，**命中即停**，所以顺序本身就是语义。
下面是按「 specificity 优先、成本靠后」原则排出的完整示例
（策略名 `nProxy` / `Proxy` / `Speed-US` / `Speed-JP` 按自己的配置改名）：

```ini
[Rule]
# 1 · 拦截类 —— pre-matching 让 REJECT 在预匹配阶段短路，不进入后续任何规则
DOMAIN-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Advertising.list,REJECT,pre-matching,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/Comics.list,REJECT,pre-matching,extended-matching,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Advertising.Extra.list,REJECT,pre-matching,extended-matching,"update-interval=21600"

# 2 · 局域网 —— 字面 IP 本地查表，零 DNS 成本；放 GEOIP 之前省一次库查询
RULE-SET,LAN,nProxy,no-resolve

# 3 · 手动置顶 —— 特异性最高的规则必须早于任何宽泛集合，否则会被提前吞掉
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Special.list,nProxy,extended-matching,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Custom.list,Proxy,extended-matching,"update-interval=21600"

# 4 · 垂直场景 —— 域名 + 关键词 + IP 的精准集合，互不重叠，先后无依赖
DOMAIN-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Ozon.list,nProxy,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Ozon.Extra.list,nProxy,extended-matching,"update-interval=21600"
DOMAIN-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/AI.list,Speed-US,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/AI.Extra.list,Speed-US,extended-matching,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Comics.list,Proxy,extended-matching,"update-interval=21600"
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Japan.list,Speed-JP,extended-matching,"update-interval=21600"

# 5 · 大而全的通用集合 —— 垂直规则之后，兜住剩余的国内外知名服务
RULE-SET,https://ruleset.skk.moe/List/non_ip/stream.conf,Proxy,extended-matching,"update-interval=21600"
RULE-SET,https://ruleset.skk.moe/List/non_ip/global.conf,Proxy,extended-matching,"update-interval=21600"
RULE-SET,https://ruleset.skk.moe/List/non_ip/domestic.conf,nProxy,extended-matching,"update-interval=21600"

# 6 · IP 兜底 —— GEOIP 需要解析 DNS，靠后放置；未解析的域名请求由 no-resolve 跳过
GEOIP,CN,nProxy

# 7 · FINAL 必须收尾 —— 配置合法性的硬要求；dns-failed 让解析失败也走兜底策略
FINAL,Proxy,dns-failed
```

## 顺序原则（为什么这样排）

| 层 | 原则 |
|---|---|
| 拦截类放最前 | `pre-matching` 在预匹配阶段生效，REJECT 家族专用；被拦请求不消耗后续规则 |
| `LAN` 早于 `GEOIP` | 两者都建议 `no-resolve`；对字面 IP 请求，LAN 是本地查表，比 GEOIP 库查询便宜 |
| `Special` / `Custom` 早于垂直集合 | 它们是「人工意图」，优先级高于任何自动维护的集合；被宽泛集合抢先命中就永远轮不到 |
| 垂直集合之间先后无依赖 | `Ozon` / `AI` / `Comics` / `Japan` 条目互不重叠，顺序只影响可读性 |
| 通用集合在垂直之后 | Sukka 的 `global` / `domestic` 覆盖面大，先放会把垂直场景的边界域名提前吸走 |
| `GEOIP` 靠后 | 域名请求到这里才触发 DNS 解析；`no-resolve` 让「未解析就命中不了」的请求直接跳过 |
| `FINAL` 收尾 | 官方硬性要求：`FINAL` 永远命中，写在它下面的规则永远不会生效；多条 `FINAL` 只有最后一条生效 |

## 参数速查

| 参数 | 作用 |
|---|---|
| `extended-matching` | 额外匹配 TLS SNI 与 HTTP Host，覆盖「直连 IP 但带 SNI」的请求。本目录集合建议全开 |
| `"update-interval=21600"` | 集合 6 小时更新一次（默认 86400 = 24h，负值禁用） |
| `no-resolve` | 域名请求跳过该规则而不触发 DNS。写在 `RULE-SET` 行上作用于集合内每条 IP 规则 |
| `pre-matching` | 仅顶层规则可用，策略必须是 REJECT 家族 |
| `dns-failed` | 仅 `FINAL`：DNS 解析失败时改用 FINAL 策略而不是报错 |

完整语义见 [Docs/02-rules.md](../Docs/02-rules.md) 与 [Docs/03-ruleset.md](../Docs/03-ruleset.md)。
