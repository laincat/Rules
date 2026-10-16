# Mihomo · 本仓库接入

[返回导航](readme.md) · [来源说明](sources.md)

## 本仓库的 Mihomo 产物

外链前缀：

```
https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/
```

| 目录 | 内容 |
|---|---|
| `Mihomo/Advertising/` | 去广告规则集（2 个 `domain` 分片 `.mrs` + 4 个 `classical` 分片 `.yaml`） |
| `Mihomo/Ruleset/` | 常规规则集（`Special.yaml`、`Ozon.yaml`、`Comics.yaml` 等） |

**下面示例中的文本 Rule Provider 是 `classical` 格式**（payload 里是完整规则行，
如 `DOMAIN-SUFFIX,steamserver.net`）。引用时必须写 `behavior: classical`：

本仓库去广告产物按内容拆分：纯域名主库
用 `behavior: domain` + `format: mrs`，其余分片是 `behavior: classical`。
完整分片示例见 [Advertising/readme.md](../Advertising/readme.md)。

```yaml
rule-providers:
  special:
    type: http
    behavior: classical
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Special.yaml"
    path: ./ruleset/Special.yaml
    interval: 43200
  adblock-drop:
    type: http
    behavior: classical
    format: yaml
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Drop.yaml"
    path: ./ruleset/Advertising.Drop.yaml
    interval: 43200
  adblock-reject:
    type: http
    behavior: domain
    format: mrs
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Reject.mrs"
    path: ./ruleset/Advertising.Reject.mrs
    interval: 43200
  adblock-reject-extra:
    type: http
    behavior: domain
    format: mrs
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.RejectExtra.mrs"
    path: ./ruleset/Advertising.RejectExtra.mrs
    interval: 43200
  adblock-nonip:
    type: http
    behavior: classical
    format: yaml
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NonIP.yaml"
    path: ./ruleset/Advertising.NonIP.yaml
    interval: 43200
  adblock-nodrop:
    type: http
    behavior: classical
    format: yaml
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NoDrop.yaml"
    path: ./ruleset/Advertising.NoDrop.yaml
    interval: 43200
  adblock-ip:
    type: http
    behavior: classical
    format: yaml
    url: "https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.IP.yaml"
    path: ./ruleset/Advertising.IP.yaml
    interval: 43200

rules:
  # 本仓库顺序：drop 层 → 域名层 → 非 IP 层 → IP 层
  - RULE-SET,adblock-drop,REJECT-DROP
  - RULE-SET,adblock-reject,REJECT
  - RULE-SET,adblock-reject-extra,REJECT
  - RULE-SET,adblock-nonip,REJECT
  - RULE-SET,adblock-nodrop,REJECT
  - RULE-SET,adblock-ip,REJECT
  - RULE-SET,special,Proxy
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,Proxy
```

> `behavior`／`format` 必须与文件内容一致；错误条目可能被跳过、误读或加载失败。
> 示例中的 `Special.yaml` 与四个广告 `classical` 分片用 `classical`；
> 两个广告域名分片用 `domain` + `mrs`。`Advertising.RejectExtra` 是补充包，
> 须与主库同时启用；`Advertising.IP` 会触发 DNS 解析，须排在所有域名类规则之后。
> 详见 [03-providers.md](03-providers.md)。

### CNB 单文件直链

需要使用国内镜像时，将对应的 provider URL 改为：

```
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Reject.mrs
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.RejectExtra.mrs
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Drop.yaml
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NonIP.yaml
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NoDrop.yaml
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.IP.yaml
```

仅使用 Release 中实际存在且同步成功的附件名；`latest` 是固定 tag，完整路径不能省略。


## 来源与适用边界

以上是 laincat/Rules 的产物接入约定，不是软件官方默认配置。
规则数据归属与生成来源见各产物目录的说明；数据来源不作为软件语法依据。
优先使用已同步的 CNB `latest` 附件；镜像缺失或校验不一致时，用同名 GitHub
`https://github.com/laincat/Rules/releases/latest/download/` 附件核对。不要推测未发布的附件名。
示例中的 `Proxy` 是占位策略名，合并前必须在自己的配置中定义。
