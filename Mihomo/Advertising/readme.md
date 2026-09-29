# Mihomo · Advertising 去广告规则集

去广告规则拆成两个 provider + 一个补充漫画拦截，配套挂载：

| 文件 | behavior | 内容 |
|---|---|---|
| `Advertising.mrs` | domain | 46 万条域名 trie（主路径） |
| `Advertising.Extra.yaml` | classical | DOMAIN-KEYWORD 补充（4 条） |
| `Comic.yaml` | classical | 漫画站补充拦截（15 条，Advertising 未覆盖部分） |

## 引用方式

```yaml
rule-providers:
  laincat-adblock:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.mrs"
    path: ./ruleset/Advertising.mrs
    interval: 43200
  laincat-adblock-extra:
    type: http
    behavior: classical
    format: yaml
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.Extra.yaml"
    path: ./ruleset/Advertising.Extra.yaml
    interval: 43200
  laincat-comic:
    type: http
    behavior: classical
    format: yaml
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Comic.yaml"
    path: ./ruleset/Comic.yaml
    interval: 43200

rules:
  # 去广告必须放最前：REJECT 一旦被前面的 MATCH 抢先就永远不生效
  - RULE-SET,laincat-adblock,REJECT
  - RULE-SET,laincat-adblock-extra,REJECT
  - RULE-SET,laincat-comic,REJECT
```

> ⚠️ `Advertising.mrs` 是 `behavior: domain`，其余两个是 `behavior: classical`，写错静默失效。

