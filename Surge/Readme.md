<p align="center">
  <img src="https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/c7/15/0e/c7150ee6-dbdf-f99c-c8c3-fbbbb37cda46/Placeholder.mill/200x200bb-75.webp" width="150" />
</p>

<h1 align="center">Surge</h1>

<p align="center">Surge 规则集、模块与知识库。</p>

<p align="center">
  <a href="https://www.nssurge.com/">官网</a> ·
  <a href="https://manual.nssurge.com/">官方手册</a> ·
  <a href="Docs/readme.md">知识库</a>
</p>

---

## 目录

| 目录 | 内容 |
|---|---|
| [`Advertising/`](Advertising/) | 去广告：各上游的 `.sgmodule` 与 `Comics.list` |
| [`Module/`](Module/) | 功能性模块（Telegram / Ozon / 下载分流 / MITM…） |
| [`Ruleset/`](Ruleset/) | 常规规则集（`Japan` / `Special` / `Ozon` / `Custom`） |
| [`Docs/`](Docs/readme.md) | **知识库**：配置、规则、模块、脚本、运维 |

## 引用方式

订阅型模块（`.sgmodule`）直接整包引用即可，元数据与参数都已配好：

```
https://raw.githubusercontent.com/laincat/Rules/main/Surge/Advertising/Laincat.sgmodule
```

纯规则列表（`.list`）是**完整规则行**格式，用 `RULE-SET` 引用：

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/laincat/Rules/main/Surge/Ruleset/Special.list,Proxy,extended-matching,"update-interval=21600"
FINAL,Proxy
```

> ⚠️ 这些 `.list` **不能**用 `DOMAIN-SET` 引用 —— 两者的文件格式不同，
> 用错不会报错而是规则静默失效。详见 [`Docs/03-ruleset.md`](Docs/03-ruleset.md)。
