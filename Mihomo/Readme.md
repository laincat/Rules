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
| [`Advertising/`](Advertising/) | 去广告规则集（2 个 `domain` 分片 `.mrs` + 4 个 `classical` 分片 `.yaml`） |
| [`Ruleset/`](Ruleset/) | 常规规则集（`Special` / `Ozon` / `AI` / `Comics`…） |
| [`Docs/`](Docs/readme.md) | **知识库**：配置、规则、Providers、Geodata、运维 |

## 引用方式

本目录混合两种格式：Advertising.Reject / RejectExtra、AI / Ozon 主文件 `.mrs` 使用 **`behavior: domain`、`format: mrs`**；其余完整规则行 `.yaml` 使用 **`behavior: classical`、`format: yaml`**。不可混用。下面以 Special 的 classical 文件为例：

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

Ozon 与 AI 是自动生成的双文件规则集（.mrs 主 + .yaml 补充），
引用方式见 [`Ruleset/readme.md`](Ruleset/readme.md)。

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


## Docker / 本机部署边界

此配置按自用场景保留 LAN 代理、DNS 监听与 TUN/auto-route。LAN 可用不等于应该把端口暴露到公网：Docker 映射端口时绑定实际可信内网地址，并用宿主机防火墙限制来源；不要默认转发路由器公网端口。使用 host 网络时，容器内监听直接作用于宿主机。

控制 API 与 LAN 代理是不同入口。远程控制需要在部署侧私有配置中填入强 `secret`，不要提交到仓库；只在本机控制时，可在部署侧将 controller 绑定回环。Docker bridge 下需要从宿主机访问容器面板时，应显式规划容器监听和宿主机端口绑定，不能直接照抄回环地址。公共样例中的注释口令没有启用认证。本文不代替实际防火墙、端口和设备验证。
