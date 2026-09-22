<p align="center">
  <img src="https://github.com/MetaCubeX/mihomo/blob/Alpha/Meta.png" width="150" />
</p>

<h1 align="center">Mihomo</h1>

<p align="center">mihomo（原 Clash Meta）规则集与知识库。</p>

<p align="center">
  <a href="https://wiki.metacubex.one/">官方文档</a> ·
  <a href="Docs/readme.md">知识库</a>
</p>

---

## 目录

| 目录 | 内容 |
|---|---|
| [`Advertising/`](Advertising/) | 去广告规则集 |
| [`Ruleset/`](Ruleset/) | 常规规则集（`Special` / `Ozon` / `Comics`…） |
| [`Docs/`](Docs/readme.md) | **知识库**：配置、规则、Providers、Geodata、运维 |

## 引用方式

本目录下的 Rule Provider 文件是 **`classical` 格式**（payload 是完整规则行）：

```yaml
rule-providers:
  special:
    type: http
    behavior: classical          # ← 必须是 classical
    url: "https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/Special.yaml"
    path: ./ruleset/Special.yaml
    interval: 43200

rules:
  - RULE-SET,special,Proxy
  - MATCH,Proxy
```

> ⚠️ `behavior` 写成 `domain` 会导致规则**静默全部失效**且不报错。
> 详见 [`Docs/03-providers.md`](Docs/03-providers.md)。

## ⚠️ 目录改名说明（Clash → Mihomo）

本目录原名 **`Clash/`**，已改名为 **`Mihomo/`**。

**旧地址需要尽快改掉。** `raw.githubusercontent.com` 是路径直取、**没有重定向**,
所以此前订阅了 `.../main/Clash/...` 的配置要改地址：

```
旧：https://raw.githubusercontent.com/laincat/Rules/main/Clash/Ruleset/Special.yaml
新：https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Ruleset/Special.yaml
```

> ⚠️ **注意不是立刻 404。** 改名后实测：仓库里 `Clash/` 已不存在，
> 但 `raw.githubusercontent.com` 仍返回 **200 + 旧的完整内容** ——
> 那是它 CDN 的缓存（缓存在该服务上通常持续数分钟到数天）。
>
> 这意味着**旧地址会静默冻结在改名前的快照**：配置看起来一切正常，
> 规则却不再更新。比直接报 404 更难察觉 —— 请主动改地址，
> 不要等它报错。

改名的原因：项目本身早已叫 mihomo，`Clash` 是历史遗留叫法，
继续用容易和原版 Clash（已停止维护、配置语法不同）混淆。
