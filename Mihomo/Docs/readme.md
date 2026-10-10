# Mihomo 知识库 · laincat/Rules

> mihomo（原 Clash Meta）的配置、规则、Providers、Geodata 与运维参考。
>
> **本知识库只讲 mihomo，不掺 Surge。** 两者在规则语法、策略模型、外部集合
> 格式上没有一一对应的关系 —— mihomo 的 `behavior`、`format` 在 Surge 里
> **根本不存在**，套用只会写出静默失效的配置。Surge 请看
> [`../../Surge/Docs/readme.md`](../../Surge/Docs/readme.md)。

---

## 一、文档导航

| 章节 | 内容 | 适合谁 |
|---|---|---|
| [01-basics.md](01-basics.md) | 配置骨架、全局字段、TUN、实验性配置 | 刚上手 |
| [02-dns.md](02-dns.md) | DNS 子系统（`enhanced-mode`、`nameserver`、`fake-ip`、`nameserver-policy`） | 排查解析 |
| [03-providers.md](03-providers.md) | **`proxy-providers` / `rule-providers` 与 `behavior` 三态** | 引用本仓库规则集 |
| [04-rules.md](04-rules.md) | 规则类型、`GEOIP` / `GEOSITE`、`RULE-SET`、`SUB-RULE`、逻辑规则 | 写规则 |
| [05-geodata.md](05-geodata.md) | `geox-url`、`.mrs` / `.dat` / `.mmdb` 的取舍 | 配地理库 |
| [06-policy-groups.md](06-policy-groups.md) | 策略组类型、`filter` / `exclude-filter`、`use` / providers | 配策略组 |
| [07-operations.md](07-operations.md) | RESTful API、排错、性能 | 运维排错 |
| [changelog.md](changelog.md) | **最近一周 + 正式版历史的更新日志**（自动生成） | 想跟进版本 |

---

## 二、本仓库的 Mihomo 产物

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

去广告采用 [SukkaW/Surge](https://github.com/SukkaW/Surge) 的分片方案：纯域名主库
用 `behavior: domain` + `format: mrs`，其余分片是 `behavior: classical`。
完整分片示例见 [Advertising/readme.md](../Advertising/readme.md)。

```yaml
rule-providers:
  special:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/Special.yaml"
    path: ./ruleset/Special.yaml
    interval: 43200
  adblock-drop:
    type: http
    behavior: classical
    format: yaml
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.Drop.yaml"
    path: ./ruleset/Advertising.Drop.yaml
    interval: 43200
  adblock-reject:
    type: http
    behavior: domain
    format: mrs
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.Reject.mrs"
    path: ./ruleset/Advertising.Reject.mrs
    interval: 43200
  adblock-reject-extra:
    type: http
    behavior: domain
    format: mrs
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.RejectExtra.mrs"
    path: ./ruleset/Advertising.RejectExtra.mrs
    interval: 43200
  adblock-nonip:
    type: http
    behavior: classical
    format: yaml
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.NonIP.yaml"
    path: ./ruleset/Advertising.NonIP.yaml
    interval: 43200
  adblock-nodrop:
    type: http
    behavior: classical
    format: yaml
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.NoDrop.yaml"
    path: ./ruleset/Advertising.NoDrop.yaml
    interval: 43200
  adblock-ip:
    type: http
    behavior: classical
    format: yaml
    url: "https://github.com/laincat/Rules/releases/latest/download/Advertising.IP.yaml"
    path: ./ruleset/Advertising.IP.yaml
    interval: 43200

rules:
  # 顺序沿用 SKK：drop 层 → 域名层 → 非 IP 层 → IP 层
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

其余文件也可使用相同前缀与原文件名；`latest` 是固定 tag，完整路径不能省略。

---

## 三、四个常见配置误区

| 约束 | 后果 |
|---|---|
| **`behavior` 必须与 payload 语法一致** | 不一致时可能有跳过警告、加载错误或无法正确匹配的条目 |
| **`no-resolve` 的作用范围** | classical IP 条目只影响该条；集合引用行影响整个 provider；已有目标 IP 仍可匹配 |
| **provider 拉取失败不一定为空集合** | 更新失败保留已加载规则；无缓存／Bundle／fallback 的首次获取失败才可能为空 |
| **`GEOIP` / `GEOSITE` 依赖有效 geodata** | 内核有默认下载源；缺库时尝试下载，失败需查日志，`geox-url` 用于覆盖来源 |

> 与 Surge 的根本差异：mihomo 的 `RULE-SET` 需要 provider 声明来描述
> **payload 的语法**（`behavior`），而 Surge 是由引用关键字
> （`RULE-SET` / `DOMAIN-SET`）决定的。两者不能互相套用。

---

## 四、上游状态（自动维护）

<!-- AUTO-STATE:BEGIN -->
> ⚙️ **本节由 `tools/docs_watch.py` 每日自动重写，请勿手工编辑。**
> 采集时间：2026-10-10T00:57:58Z（UTC）

| 上游 | 当前值 | 日期 | 上次变化 |
|---|---|---|---|
| 最新正式版 | `v1.19.32` | 2026-09-30 | 2026-10-01T04:18:49Z |
| Alpha HEAD | `e4dd968` | 2026-10-08 | 2026-10-09T01:15:55Z |
| 正式版 → Alpha 领先 | 4 条提交 | — | 2026-10-09T01:15:55Z |
| 官方默认配置 `docs/config.yaml` | sha256 `e57eea09cdfb1851…`（142920 字节） | — | 2026-09-27T23:50:46Z |
| wiki 源仓库 MetaCubeX/Meta-Docs | `c47fd72` | 2026-10-03 | 2026-10-03T23:52:58Z |
| 官网 wiki sitemap | 285 个 URL | lastmod 2026-10-03 | 2026-10-03T23:52:58Z |
| 社区合集 HenryChiao/MIHOMO_YAMLS | `f5e183f` | 2026-10-09 | 2026-10-10T00:57:58Z |

> 判据提醒：**Alpha 有提交 ≠ 需要追 Alpha**。当前正式版与 Alpha 的差异多为
> bugfix，不涉配置面；真正要盯的是上表里 `docs/config.yaml` 的哈希 ——
> 字段增删改一定会落在那个文件上。
<!-- AUTO-STATE:END -->

---

## 五、版本体系怎么读

mihomo 有两条线：

| 线 | 说明 |
|---|---|
| **正式版** | 有 tag（如 `v1.19.31`）、可回退。**日常用这个** |
| **Alpha 分支** | 持续开发，正式版是它的定期合入 |

> **Alpha 有提交 ≠ 需要追 Alpha。** 多数增量是 bugfix，不涉及配置面。
> 判断依据是「正式版到 Alpha 领先几条、分别是什么」——
> 这组数字由第四节自动维护。
>
> 配置面的权威清单是官方默认配置
> [`docs/config.yaml`](https://github.com/MetaCubeX/mihomo/raw/refs/heads/Alpha/docs/config.yaml)
> —— 字段的增删改一定会落在那个文件上，盯它的哈希比翻 wiki 可靠。

---

## 六、人工复核记录

2026-10-04 已重新核验：正式版仍为 `v1.19.32`，Alpha 为 `9f053c4`，
领先正式版 1 条提交，发布说明待译条目为 0。
官方 wiki 的 `2026-10-03 / c47fd72` 更新补全 MIPS 默认网络栈、
TUN listener 和拥塞控制说明，本库已同步到 [01-basics.md](01-basics.md)。
自动采集时间仅在上游值变化时更新；此次 wiki 补充对应正式版已有配置。
其余章节已对照 `v1.19.32` 复核：链式代理改用节点级 `dialer-proxy`，
补正 provider 缓存／fallback、`no-resolve` 作用范围及 geodata 默认下载行为。

## 七、更新日志自动翻译

自 2026-10-08 起，日常巡检默认调用
[Index-Translate](https://github.com/bilibili/Index-Translate) 翻译尚未收录的发布说明，
通过技术内容与格式校验后直接缓存到 `translations.json` 并生成中文日志，
无需逐条人工审核。已有译文不会重新翻译；接口失败或校验失败时保留英文，
后续巡检自动重试。配置教程的正文复核仍按第六节所述单独进行。

普通版本、Alpha 提交和发布说明的更新由自动化处理，不再生成复核 Issue。
仅配置参考源或官方文档页面变化、发布说明采集未完成、翻译仍有待译条目时提醒；
提醒保留本轮采集的真实差异，便于判断需要处理的内容。

每套文档每轮最多处理 40 条、调用时间预算 120 秒。`--dry-run` 不调用翻译接口，
`--no-auto-translate` 可禁用自动翻译。翻译仅提交公开发布说明，不发送 GitHub Token。
模型译文可能有语义偏差，配置条件与功能限制请以官方原文为准。
