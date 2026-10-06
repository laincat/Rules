# Mihomo · Advertising 去广告规则集

分片方案对齐 [SukkaW/Surge](https://github.com/SukkaW/Surge)：每个文件对应一种
**处置策略**与一种**匹配代价**，按需组合，而不是一个巨型文件。

Surge 的 `REJECT-DROP` / `REJECT-NO-DROP` 在 Mihomo 中没有对应策略，统一降级为
`REJECT` —— 这与 SKK 自己的 Mihomo 引用方式一致。

| 文件 | behavior | 处置 | 内容 |
|---|---|---|---|
| `Advertising.Reject.mrs` | domain | REJECT | 纯域名主库（13.4 万） |
| `Advertising.RejectExtra.mrs` | domain | REJECT | 纯域名补充库（9.8 万），**须与主库同时启用** |
| `Advertising.Drop.yaml` | classical | REJECT-DROP | 高频遥测端点，静默丢包 |
| `Advertising.NonIP.yaml` | classical | REJECT | 关键词 / 通配等非 IP 规则 |
| `Advertising.NoDrop.yaml` | classical | REJECT | 需拒绝但保留 RST 语义的条目 |
| `Advertising.IP.yaml` | classical | REJECT | CIDR / ASN，**会触发 DNS 解析，须放最后** |

## 引用方式

```yaml
rule-providers:
  laincat-adblock-drop:
    type: http
    behavior: classical
    format: yaml
    interval: 43200
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.Drop.yaml"
    path: ./ruleset/Advertising.Drop.yaml
  laincat-adblock:
    type: http
    behavior: domain
    format: mrs
    interval: 43200
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.Reject.mrs"
    path: ./ruleset/Advertising.Reject.mrs
  laincat-adblock-extra:
    type: http
    behavior: domain
    format: mrs
    interval: 43200
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.RejectExtra.mrs"
    path: ./ruleset/Advertising.RejectExtra.mrs
  laincat-adblock-nonip:
    type: http
    behavior: classical
    format: yaml
    interval: 43200
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.NonIP.yaml"
    path: ./ruleset/Advertising.NonIP.yaml
  laincat-adblock-nodrop:
    type: http
    behavior: classical
    format: yaml
    interval: 43200
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.NoDrop.yaml"
    path: ./ruleset/Advertising.NoDrop.yaml
  laincat-adblock-ip:
    type: http
    behavior: classical
    format: yaml
    interval: 43200
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Advertising/Advertising.IP.yaml"
    path: ./ruleset/Advertising.IP.yaml

rules:
  # 顺序沿用 SKK：drop 层 → 域名层 → 非 IP 层 → IP 层
  # 任何 domainset / non_ip 规则都必须排在 IP 类规则之前，否则会失去 DNS 污染保护
  - RULE-SET,laincat-adblock-drop,REJECT-DROP
  - RULE-SET,laincat-adblock,REJECT
  - RULE-SET,laincat-adblock-extra,REJECT
  - RULE-SET,laincat-adblock-nonip,REJECT
  - RULE-SET,laincat-adblock-nodrop,REJECT
  - RULE-SET,laincat-adblock-ip,REJECT
```

> ⚠️ 两个 `.mrs` 是 `behavior: domain`，四个 `.yaml` 是 `behavior: classical`，
> 写错会静默失效。
>
> ⚠️ `Advertising.RejectExtra` 是**补充包**，单独启用覆盖率会明显下降。
