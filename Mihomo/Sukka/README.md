# Sukka Mihomo 规则

本目录由 `tools/gen_rulesets.py` 自动生成。生成器直接读取
[SukkaW/Surge](https://github.com/SukkaW/Surge) 发布的
[`ruleset.skk.moe/Clash`](https://ruleset.skk.moe/Clash/) 成品；该目录就是
Sukka 已经为 Clash/Mihomo 处理过的规则语义。以 `/Clash` 成品为准，
不保证包含 `/List` 中的全部 Surge 类型或逻辑规则。

生成时排除广告拦截和 AI 清单；这两类规则已由本仓库的
`Mihomo/Advertising` 与 `Mihomo/Ruleset/AI*` 提供。

同时排除 Sukka 标记为 deprecated 的文件、`my_*` 私人规则，以及
`domainset/clash_fake_ip_filter`：后者是 `fake-ip-filter` 数据，不是可加入
`rules:` 的路由规则。`non_ip/cloudmounter` 和
`ip/stream_biliintl` 保留在抓取清单中；当前上游只发布 marker 时不会生成空
provider，后续出现真实规则后会自动生成。

## 目录与格式

- `domainset/`：Sukka 的纯域名规则。
  - 不超过 100 条：`<name>.yaml`，provider 使用 `behavior: domain`。
  - 超过 100 条：`<name>.mrs`，provider 使用 `behavior: domain`、`format: mrs`。
- `non_ip/`：Sukka 中不会触发 DNS 解析的规则。
  - 不超过 100 条：`<name>.yaml`，provider 使用 `behavior: classical`。
  - 超过 100 条：可放入域名 trie 的部分生成 `<name>.mrs`，关键词、通配符、
    进程名和 IP 等其余规则生成 `<name>.Extra.yaml`。单标签域名/后缀（例如
    `unifi`、`local`、`uk`）也保留在 Extra 中，不会因通用域名校验而丢失。
    两者都引用时与原清单等效。
- `ip/`：不超过 100 条时生成 `<name>.yaml`。超过 100 条且包含 CIDR 时，
  CIDR 部分生成 `<name>.mrs`，provider 使用 `behavior: ipcidr`；`IP-ASN`
  等无法进入 IP trie 的规则生成 `<name>.Extra.yaml`。`classical` 中的
  `IP-CIDR` / `IP-CIDR6` 保留上游逐条 `no-resolve` 选项；纯 CIDR
  `ipcidr` provider 仅在原清单所有前缀都带 `no-resolve` 时，于 `RULE-SET`
  行添加该选项。裸 CIDR 不凭空增加 `no-resolve`。同一清单若混合两种解析
  语义，则保留 `classical` YAML，以免单一 `ipcidr` provider 改变匹配结果。

条数跨过 100 条阈值时，文件格式/扩展名及 Extra 是否存在可能随上游变化。
复制到自己配置中的引用不会随范例自动更新；更新时应核对最新 `example.yaml`。

Sukka 每个成品文件首部的
`7h15.ru1353t.1s.m4d3.by.5ukk4w.skk.moe` marker 会被过滤，不会成为规则。
Surge 特有的 `USER-AGENT` 与 `URL-REGEX` 不被 Mihomo 接受，Sukka 自己的 Clash
成品同样会移除；生成器会跳过并在文件头记录跳过数量。

部分上游 `ip/stream_*.conf` 目前没有实际 IP 规则，因此不会生成空 provider。
等上游出现真实规则后，下一次自动生成会创建对应 YAML 或 MRS，并写入
`example.yaml`。

## 引用顺序

必须保持：

1. 全部 `domainset`
2. 全部 `non_ip`
3. 全部 `ip`

不要把任何 IP、GEOIP 或 `ip/` provider 移到 `domainset` / `non_ip` 前面，否则
会失去 Sukka 设计中的 DNS 污染保护。目录中的
[`example.yaml`](./example.yaml) 已按此顺序生成，并将每个 provider 和 rule
写成单行。范例统一使用 `DIRECT` 以便 Mihomo 直接校验；复制后应按自己的代理组
替换策略。

## 获取地址

仓库原始文件：

```text
https://raw.githubusercontent.com/laincat/Rules/main/Mihomo/Sukka/...
```

CNB 镜像：

```text
https://cnb.cool/laincat/Rules/-/git/raw/main/Mihomo/Sukka/...
```

`Mihomo/Sukka` 中的不同子目录会有同名文件，例如 `non_ip/telegram.yaml` 与
`ip/telegram.yaml`，因此不加入 GitHub Release 的扁平单文件附件。完整目录会保留在
`rulesets.tar.gz` 中；日常配置优先直接引用上面的 raw 地址。

## 校验

CI 在生成后重新运行回归测试，并使用与编译 MRS 相同的 Mihomo 核心加载本轮
全部 provider。校验使用临时目录中的本地文件，不下载代理订阅，不启用代理端口、
DNS 或 TUN；逐个核对 YAML 条数，防止核心仅警告后跳过无效规则。
解析 `IP-ASN` 时可能下载 MetaCubeX 官方 ASN 数据库；可用 `--asn-mmdb` 提供
已有数据库进行离线校验。这是语法与载入校验，不是实际流量分流测试。
本地可运行 `python tools/validate_sukka.py --mihomo ./mihomo`。

## 上游许可

规则版权归 SukkaW/Surge 及其贡献者所有。上游只有
`List/ip/china_ip.conf` 按 CC BY-SA 2.0 分享；`ip/china_ip_ipv6.conf` 及其余规则
按 AGPL-3.0 分享。IPv6 原始数据另有 MIT 来源声明；请保留全部来源与许可信息。
