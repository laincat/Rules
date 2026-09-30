# Laincat Rules

自用规则集仓库，面向 Surge 与 mihomo（原 Clash Meta），两套配置各自独立、互不混用。所有规则集由 CI 每日自动抓取上游、去重、清洗并滚动发布。

## 目录

| 目录 | 面向 | 说明 |
|---|---|---|
| [`Surge/`](Surge/Readme.md) | Surge Mac / iOS / tvOS | 规则集、模块、知识库（`Surge/Docs/`） |
| [`Mihomo/`](Mihomo/Readme.md) | mihomo（原 Clash Meta） | 规则集、知识库（`Mihomo/Docs/`） |

> **两套知识库彼此独立。** Surge 与 mihomo 在规则语法、策略模型、外部集合格式上没有一一对应关系，写在一起只会互相误导，各自看各自的 `Docs/`。

## 规则集

三个类目，每类都提供「主文件 + 补充文件」的结构：主文件是纯域名（走索引，性能最好），补充文件承载关键词、IP 段等无法进索引的规则。

| 类目 | Surge | mihomo |
|---|---|---|
| 去广告 | `Surge/Advertising/Advertising.list`（DOMAIN-SET）+ `Advertising.Extra.list`（RULE-SET） | `Mihomo/Advertising/Advertising.mrs` + `Advertising.Extra.yaml` |
| AI 服务 | `Surge/Ruleset/AI.list` + `AI.Extra.list` | `Mihomo/Ruleset/AI.mrs` + `AI.Extra.yaml` |
| Ozon | `Surge/Ruleset/Ozon.list` + `Ozon.Extra.list` | `Mihomo/Ruleset/Ozon.mrs` + `Ozon.Extra.yaml` |

### 数据来源

| 类目 | 上游 |
|---|---|
| 去广告 | Cats-Team AdRules、Sukka、AWAvenue、BlueSkyXN（白名单回剔 + 误杀防护） |
| AI 服务 | MetaCubeX（= v2fly `category-ai-chat-!cn` 展开）、Sukka、Rabbit-Spec、ACL4SSR、iplist AI、Sukka Voice IP |
| Ozon | 本地基线 + iplist Ozon 域名 + RIPEstat ASN（`AS44386` / `AS207986` 宣告前缀） |

### 下载

所有规则文件都可通过 GitHub Raw 直接引用，release 也提供整包（见下）。

- 固定整包地址（滚动更新）：`https://github.com/laincat/Rules/releases/latest/download/rulesets.tar.gz`
- 单文件 Raw 地址：`https://raw.githubusercontent.com/laincat/Rules/main/<路径>`

## 发布与更新

- **每日自动构建**：CI 抓上游、重算、去重、清洗，有变化才提交。
- **滚动 Release**：tag 固定为 `latest`，永远只保留一条，每次覆盖同名附件；**发行版说明直接展示每次新版本相对旧版的差异**（新增 / 删除条数）。
- **CNB 镜像**：同步推送到 [cnb.cool/laincat/Rules](https://cnb.cool/laincat/Rules)（纯镜像，历史一致），规则文件可从 CNB 侧直连。

## 知识库维护

`Surge/Docs/` 与 `Mihomo/Docs/` 记录上游的版本与配置面状态，靠 `tools/docs_watch.py` 每日采集（版本号 / build / 提交 / 页面清单 / 内容哈希）保持不腐烂，检测到变化时自动开 issue 提醒——「该怎么改文档」仍由人读发布说明后判断，脚本只回答「上游变了没有」。

## 本地构建

```bash
# 生成全部规则集（可选 --mihomo 指向 mihomo 二进制以编译 .mrs）
python tools/gen_rulesets.py --write [--mihomo ./mihomo]

# 对比差异（对比 HEAD 与当前工作区）
python tools/gen_diff.py --pre HEAD --out diff.json --md DIFF.md
```

## 许可

本仓库当前未附带 LICENSE 文件。规则数据来自多个上游项目，各自遵循其许可证，使用前请查阅对应来源。