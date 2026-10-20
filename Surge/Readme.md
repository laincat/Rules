<p align="center">
  <img src="https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/c7/15/0e/c7150ee6-dbdf-f99c-c8c3-fbbbb37cda46/Placeholder.mill/200x200bb-75.webp" width="150" />
</p>

<h1 align="center">Surge</h1>

<p align="center">Surge 规则集、模块与自动更新日志。</p>

<p align="center">
  <a href="https://www.nssurge.com/">官网</a> ·
  <a href="https://manual.nssurge.com/">官方手册</a> ·
  <a href="Changelog/changelog.md">更新日志</a>
</p>

---

## 目录

| 目录 | 内容 |
|---|---|
| [`Advertising/`](Advertising/) | 去广告：`.sgmodule` 与 6 个按处置策略分片的 `.list`（对齐 SukkaW/Surge） |
| [`Module/`](Module/) | 功能性模块（Telegram / Ozon / 下载分流 / MITM…） |
| [`Ruleset/`](Ruleset/) | 常规规则集（`Japan` / `Special` / `Ozon` / `AI` / `Custom`） |
| [`Changelog/`](Changelog/changelog.md) | **自动更新日志**：Telegram 公告的中文翻译 |

## 引用方式

通用订阅模块（`.sgmodule`）可直接引用；含私人策略的功能模块请先阅读 [模块兼容性说明](Module/readme.md)：

```
https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/Advertising.sgmodule
```

`.list` 扩展名不决定格式。以下四份为纯域名集，使用 `DOMAIN-SET`：

- `Ruleset/AI.list`、`Ruleset/Ozon.list`
- `Advertising/Advertising.Reject.list`、`Advertising/Advertising.RejectExtra.list`

其余十份 `.list` 为完整规则行，使用 `RULE-SET`，例如：

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Special.list,Proxy,extended-matching,"update-interval=21600"
FINAL,Proxy
```

> ⚠️ `DOMAIN-SET` 与 `RULE-SET` 文件格式不同，不能互换。AI / Ozon 的 `.Extra.list` 补集仍使用 `RULE-SET`。完整订阅示例见 [`Ruleset/readme.md`](Ruleset/readme.md)，格式定义以 [Surge 官方手册](https://manual.nssurge.com/)为准。

