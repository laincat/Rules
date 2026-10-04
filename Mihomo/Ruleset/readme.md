# Mihomo · Ruleset 目录

> `AI` / `Ozon` 两套由 `tools/gen_rulesets.py` 自动生成
>（GitHub Actions `gen-rulesets.yml` 每日运行），**请勿手改**；
> `Special` / `Comics` / `ClashMi-SideStore` 为手工维护。
>
> 自动生成的两套均为**双文件**：`<Name>.mrs`（域名 trie，`behavior: domain`）
> 与 `<Name>.Extra.yaml`（非域名类型，`behavior: classical`）。

## 目录清单

| 文件 | behavior | 内容 | 建议策略 |
|---|---|---|---|
| `Special.yaml` | classical | 手动置顶的特殊条目（游戏下载、国内白名单等） | `Proxy` |
| `Ozon.mrs` | domain | Ozon 电商域名（46 条） | `nProxy` |
| `Ozon.Extra.yaml` | classical | Ozon 补充（DOMAIN-KEYWORD + 自有 ASN 网段，13 条） | `nProxy` |
| `AI.mrs` | domain | AI 服务域名（280 条） | `Proxy` |
| `AI.Extra.yaml` | classical | AI 补充（DOMAIN-KEYWORD + 出口 IP，32 条） | `Proxy` |
| `Comics.yaml` | classical | 漫画站 | `REJECT` 或 `Proxy` |
| `ClashMi-SideStore.yaml` | classical | ClashMi / SideStore | `Proxy` |

## 双文件结构：mrs 主 + yaml 补充

`AI` / `Ozon` 两套都是双文件规则集，职责不同：

- `.mrs` —— 纯域名 trie（`behavior: domain` + `format: mrs`），体积小、加载快，域名流量的主路径；
- `.Extra.yaml` —— classical（`DOMAIN-KEYWORD`、`IP-CIDR`、`IP-ASN`），mrs 表达不了的规则的补充路径。

两个 provider 一起挂，**mrs 的 RULE-SET 放在 Extra 前面**：域名流量在 trie 里短路命中，
Extra 只兜底关键词与 IP 候选，线性扫描成本趋近于零。

```yaml
rule-providers:
  ai:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/AI.mrs"
    path: ./ruleset/AI.mrs
    interval: 43200
  ai-extra:
    type: http
    behavior: classical
    format: yaml
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/AI.Extra.yaml"
    path: ./ruleset/AI.Extra.yaml
    interval: 43200

rules:
  - RULE-SET,ai,Proxy
  - RULE-SET,ai-extra,Proxy
```

> ⚠️ **`behavior` 写错不会报错，而是规则静默全部失效。**
> `.mrs` 文件必须 `behavior: domain` + `format: mrs`；
> `.yaml` 文件必须 `behavior: classical` + `format: yaml`（或省略 format）。
> 详见 [Docs/03-providers.md](../Docs/03-providers.md)。

## 最佳先后顺序

`rules:` 是**有序列表**，自上而下匹配，命中即停，顺序本身就是语义。
下面是按「specificity 优先、成本靠后」原则排出的完整示例
（策略名 `nProxy` / `Proxy` / `Speed-US` / `Speed-JP` 按自己的配置改名）：

```yaml
rules:
  # 1 · 拦截类 —— REJECT 越早越好，被拦请求不消耗后续任何规则
  #    去广告双文件: mrs (域名 trie) 在前, Extra (关键词) 紧随
  - RULE-SET,adblock,REJECT
  - RULE-SET,adblock-extra,REJECT

  # 2 · 局域网 —— 字面 IP 本地查表，零 DNS 成本；no-resolve 让域名请求直接跳过
  - RULE-SET,lan,nProxy,no-resolve

  # 3 · 手动置顶 —— 特异性最高的规则必须早于任何宽泛集合，否则被提前吞掉
  - RULE-SET,special,nProxy

  # 4 · 垂直场景 —— mrs（域名主路径）在前，Extra（关键词 / IP 补充）紧随其后
  - RULE-SET,ozon,nProxy
  - RULE-SET,ozon-extra,nProxy
  - RULE-SET,ai,Proxy
  - RULE-SET,ai-extra,Proxy
  - RULE-SET,comic,Proxy

  # 5 · 大而全的通用集合 —— 垂直规则之后，兜住剩余的国内外知名服务
  #    （geosite / Rule Provider 形式的通用集合按需挂载）

  # 6 · IP 兜底 —— GEOIP 需要解析 DNS，靠后放置；no-resolve 跳过未解析的域名请求
  - GEOIP,CN,nProxy,no-resolve

  # 7 · MATCH 必须收尾 —— 永远命中，等价于 Surge 的 FINAL
  - MATCH,Proxy
```

## 顺序原则（为什么这样排）

| 层 | 原则 |
|---|---|
| 拦截类放最前 | REJECT 越早越省；被拦请求不会进入后续任何规则 |
| `lan` 早于 `GEOIP` | 对字面 IP 请求，LAN 是本地查表，比 GEOIP 库查询便宜 |
| `special` 早于垂直集合 | 它是「人工意图」，优先级高于自动维护的集合；被宽泛集合抢先就永远轮不到 |
| mrs 在 Extra 前 | 同名规则集的两半之间：域名在 trie 短路，Extra 只兜关键词与 IP |
| 垂直集合之间先后无依赖 | `ozon` / `ai` / `comic` 条目互不重叠，顺序只影响可读性 |
| `GEOIP` 靠后 + `no-resolve` | 域名请求到这里才触发 DNS；`no-resolve` 让「不解析就命中不了」的请求直接跳过 |
| `MATCH` 收尾 | 永远命中；写在它下面的规则永远不会生效 |

## 参数速查

| 参数 | 作用 |
|---|---|
| `behavior` | `domain` / `ipcidr` / `classical`，决定 payload 写法；写错**静默失效** |
| `format` | `yaml` / `text` / `mrs`，默认 `yaml`；`.mrs` 文件必须显式写 `mrs` |
| `interval` | provider 更新间隔（秒），`43200` = 12h |
| `no-resolve` | 域名请求跳过该规则而不触发 DNS。写在 `RULE-SET` 行上作用于集合内每条 IP 规则 |
| `path` | 本地缓存路径，默认存到 Home Dir 的 `rules` 目录 |

完整语义见 [Docs/03-providers.md](../Docs/03-providers.md) 与 [Docs/04-rules.md](../Docs/04-rules.md)。
