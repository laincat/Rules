# Surge · 本仓库接入

[返回导航](readme.md) · [来源说明](sources.md)

## 本仓库的 Surge 产物

外链前缀统一为：

```
https://raw.githubusercontent.com/laincat/Rules/main/Surge/
```

| 目录 | 内容 |
|---|---|
| `Surge/Advertising/` | 去广告：`.sgmodule` 与 6 个按处置策略分片的 `.list` |
| `Surge/Module/` | 功能性模块（Telegram、Ozon、下载分流、MITM 等） |
| `Surge/Ruleset/` | 常规规则集（`Japan.list`、`Special.list`、`Ozon.list` 等） |

`.sgmodule` 可直接作为模块订阅；`.list` 的引用类型由文件内容决定。去广告采用
[SukkaW/Surge](https://github.com/SukkaW/Surge) 的分片方案 —— 每个文件对应一种
**处置策略**与一种**匹配代价**，按需组合，而不是一个巨型文件：

| 文件 | 内容格式 | 引用方式 |
|---|---|---|
| `Advertising.Reject.list` | 纯域名主库，前导 `.` 表示域名及其子域 | `DOMAIN-SET` |
| `Advertising.RejectExtra.list` | 纯域名补充库，须与主库同时启用 | `DOMAIN-SET` |
| `Advertising.Drop.list`、`Advertising.NonIP.list`、`Advertising.NoDrop.list` | 遥测层 / 关键词 / 需保留 RST 语义的条目 | `RULE-SET` |
| `Advertising.IP.list` | CIDR / ASN，会触发 DNS 解析，须放最后 | `RULE-SET` |
| `AI.list`、`Ozon.list` | 纯域名，前导 `.` 表示域名及其子域 | `DOMAIN-SET` |
| `AI.Extra.list`、`Ozon.Extra.list` | 关键词、IP 等完整规则行 | `RULE-SET` |
| `Special.list`、`Japan.list` 等 | 完整规则行 | `RULE-SET` |

详见 [03-ruleset.md](03-ruleset.md) 的完整去广告与分流示例。

### 单文件下载与订阅地址

每个文件均有固定 Release 直链，更新时覆盖同名附件：

```
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.sgmodule
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Reject.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.RejectExtra.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Drop.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NonIP.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NoDrop.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.IP.list
```

CNB 国内镜像的对应地址为：

```
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.sgmodule
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Reject.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.RejectExtra.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Drop.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NonIP.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NoDrop.list
https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.IP.list
```

CNB 地址中的 `latest` 是固定 tag，须保留完整的 `/-/releases/download/latest/`
路径。模块镜像与 GitHub 原文相同，模块内引用的规则 URL 仍指向 GitHub Raw；
若规则下载也需要走 CNB，请在配置中使用相应的 CNB 单文件直链。


## 来源与适用边界

以上是 laincat/Rules 的产物接入约定，不是软件官方默认配置。
规则数据归属与生成来源见各产物目录的说明；数据来源不作为软件语法依据。
优先使用已同步的 CNB `latest` 附件；镜像缺失或校验不一致时，用同名 GitHub
`https://github.com/laincat/Rules/releases/latest/download/` 附件核对。不要推测未发布的附件名。
示例中的 `Proxy` 是占位策略名，合并前必须在自己的配置中定义。

## 配置片段

下面的广告示例按 SKK 的顺序加载全部分片（`drop` → 域名层 → 非 IP 层 → IP 层）；
`Ozon` 仍是双文件加载：

```
[Rule]
# 去广告（本仓库分片）
RULE-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Drop.list,REJECT-DROP,pre-matching,"update-interval=43200"
DOMAIN-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.Reject.list,REJECT,pre-matching,extended-matching,"update-interval=43200"
DOMAIN-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.RejectExtra.list,REJECT,pre-matching,"update-interval=43200"
RULE-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NonIP.list,REJECT,pre-matching,extended-matching,"update-interval=43200"
RULE-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.NoDrop.list,REJECT-NO-DROP,pre-matching,"update-interval=43200"
RULE-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Advertising.IP.list,REJECT-DROP,"update-interval=43200"

# 常规分流
DOMAIN-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Ozon.list,Proxy,"update-interval=43200"
RULE-SET,https://cnb.cool/laincat/Rules/-/releases/download/latest/Ozon.Extra.list,Proxy,extended-matching,"update-interval=43200"
```

> `Advertising.RejectExtra` 是**补充包**，单独启用覆盖率会明显下降，须与主库同时启用。
> `Advertising.IP` 会触发 DNS 解析，本仓库示例放在域名类规则之后，减少提前解析。

订阅型模块（`.sgmodule`）更适合直接整包引用 —— 元数据、策略、参数都已配好。

---

