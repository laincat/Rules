# OxiDNS 局域网加密 DNS 配置

这份目录提供一套面向 Windows 局域网的 OxiDNS 配置，包含 WebUI、加密上游、主备回退、响应 IP 测速优选和持久化缓存。配置文件见 [`config.yaml`](./config.yaml)。

它是针对本机网络需求整理的示例，不是 OxiDNS 的完整配置手册。OxiDNS 使用插件和 `sequence` 组合策略；添加新功能时，请先核对当前安装版本和 bundle 是否支持相应插件与字段。

## 功能概览

```text
客户端 UDP/TCP :5335
        │
        ▼
      main
        ├─ 缓存：命中后直接返回
        ├─ 主路径：阿里 DoQ + DoH/HTTP3 并发
        ├─ 备用路径：腾讯 DoT + DoH，按 200ms 阈值回退
        └─ 响应返回时：对 A/AAAA 地址测速并优选

管理 WebUI/API：TCP :9199
```

## 配置说明

### 监听、WebUI 和日志

- `dns_udp`、`dns_tcp` 监听 `0.0.0.0:5335`，接收局域网 IPv4 的传统 DNS UDP/TCP 请求。5335 是非标准 DNS 端口，客户端或路由器需要显式填写端口（若客户端不支持自定义 DNS 端口，则需要本机转发或另一层 DNS 代理）。
- WebUI/API 监听 `0.0.0.0:9199`，使用 HTTP Basic Auth。把 `username` / `password` 中的示例值替换为自己的凭据；不要把真实密码提交到 Git。
- `0.0.0.0` 会绑定所有 IPv4 网卡。请用 Windows 防火墙或上游防火墙限制管理端口和 DNS 端口的访问来源，只开放可信局域网。
- 日志按天轮转，最多保留 7 个文件。相对路径以 OxiDNS 的工作目录为基准。

### 引导 DNS 与出站

`network.outbound.profiles.bootstrap_dns` 定义了三个 IPv4 引导解析器：`119.29.29.29`、`223.5.5.5` 和 `223.6.6.6`。它们用于解析 `dns.alidns.com`、`dot.pub`、`doh.pub` 等加密上游的主机名，不是客户端查询的普通明文上游。该 profile 的 `proxy: none` 表示 OxiDNS 不为这些连接配置代理。

> `proxy: none` 不会自动修改 Windows 路由，也不能保证流量绕过 Mihomo TUN。若 OxiDNS 运行在 Sparkle/Mihomo TUN 后，需要在 Sparkle 的 TUN `route-exclude-address` 中配置实际使用的引导 DNS 及必要的上游拨号 IP，并在运行配置中确认排除项已生效。IP 可能变化，应按当前解析与路由状态维护。配置文件里提到 Windows 主机路由及本地脚本的注释是旧部署说明；此 YAML 本身不会创建或删除系统路由。

### 加密上游与回退

| 路径 | 上游 | 用途 |
|---|---|---|
| 主路径 | `quic://dns.alidns.com`（DoQ）和 `h3://dns.alidns.com/dns-query`（DoH over HTTP/3） | 阿里 DNS；`concurrent: 2` 同时查询两条上游，`balanced` 选择可用响应 |
| 备用路径 | `tls://dot.pub`（DoT）和 `https://doh.pub/dns-query`（DoH） | 腾讯 DNS；主路径失败或超过 200ms 回退阈值时使用 |

DoT 使用 `dot.pub`，因为 `doh.pub` 的 DoT 证书主机名不匹配。DoT 的 pipeline 已关闭，避免目标服务器不稳定时出现错误。两条路径都把 `SERVFAIL`、`REFUSED`、`FORMERR`、`NOTIMP` 视为可清除并重试的响应；正常的 `NXDOMAIN` 和 `NOERROR/NODATA` 会作为有效 DNS 结果保留。

### IP 测速优选

`ip_select` 只对上游响应中的 A/AAAA 地址进行探测和排序，不负责上游竞速。当前设置包括：

- 使用 TCP 443、TCP 80 和 Ping 作为探测方式。
- `best_within_budget` 在最多 800ms 的预算内选择评分较好的地址；`top_n: 1` 只保留一个优选地址。
- 探测错峰间隔为 100ms，单次探测超时为 600ms，最多并行探测 64 个地址。
- 成功评分缓存 600 秒，失败结果缓存 30 秒。
- `dnssec_policy: reorder_only` 在需要保留 DNSSEC 相关记录时只调整顺序，不裁剪地址。

测速结果反映 OxiDNS 实际发起探测时所走的网络路径；若 Mihomo TUN 接管相关 TCP/Ping 流量，结果也可能反映代理出口路径。优选能改善 DNS 返回地址的排序，不保证应用层下载或完整访问延迟一定最低。`ip_selector` 在 OxiDNS 上游文档中标记为实验性插件，升级后应重新验证行为。

### 缓存

`dns_cache` 最多保留 8192 个条目，启用 NXDOMAIN/NODATA 负缓存，负缓存 TTL 上限为 60 秒，并每 300 秒把缓存写入 `./dns_cache.dump`。`short_circuit: true` 让缓存命中时直接结束后续查询链。

当前没有设置 `lazy_cache_ttl`，因此没有启用“原 TTL 过期后短暂返回旧答案并后台刷新”的 stale cache 行为。需要降低短时上游故障对缓存未命中查询的影响时，可以评估添加该选项；应根据域名变化速度设定 TTL，并验证过期答案的风险。

## 执行链

配置按插件 tag 连接各部分：

1. `dns_udp` / `dns_tcp` 把请求送入 `main`。
2. `main` 先经过 `ip_select` 与 `dns_cache`，然后进入 `fast_fallback`。
3. `fast_fallback` 调用 `primary_path`；主路径的两条阿里上游并发查询。
4. 主路径失败或过慢时，调用 `secondary_path`，由腾讯 DoT/DoH 提供备用答案。
5. 收到响应后，`ip_select` 对 A/AAAA 候选地址进行优选；缓存保存 DNS 答案，并在命中时复用。
6. 所有上游都没有可接受响应时返回 `SERVFAIL`。

`sequence`、`fallback`、`forward`、`cache` 和 `ip_selector` 的语义及可配置字段，以 [OxiDNS 插件参考](https://oxidns.org/plugin-reference/overview) 为准。

## 可扩展方向

按需求逐项增加插件，并把域名规则、匹配条件和上游策略接入 `main`；不要只添加插件定义却忘记在执行链中调用。

| 方向 | 可以增加的能力 | 适用场景 |
|---|---|---|
| 按域名分流 | 用 `domain_set`、`qname` matcher 和多个 `forward` / `sequence`，为内网、国内、海外或特定服务选择不同上游 | 不同域名需要不同解析出口 |
| 按客户端分流 | 用 `client_ip` matcher 为不同设备设置不同解析策略、上游或拒绝规则 | 家庭设备、访客网络、儿童设备需要不同策略 |
| 广告与恶意域名过滤 | 接入 `adguard_rule` provider，或用域名规则配合 `black_hole` 返回 NXDOMAIN/NODATA | 需要 DNS 层过滤时；当前配置未启用广告规则 |
| 本地域名与静态记录 | 增加 `hosts` 或 `arbitrary`，为 NAS、路由器、开发服务设置本地 A/AAAA/CNAME/TXT 等响应 | 家庭内网和实验环境 |
| 缓存策略 | 评估 `lazy_cache_ttl`、正/负 TTL 上限及缓存容量 | 想在上游短暂不可用时复用近期答案，或调整命中率与新鲜度 |
| 双栈与响应处理 | 增加 IPv4/IPv6 偏好、TTL 调整、响应重定向等执行器 | IPv6 不稳定、需要统一 TTL 或兼容特定域名 |
| 加密 DNS 入站 | 添加 DoH、DoT 或 DoQ server 监听，并配置证书和私钥 | 希望客户端到 DNS 服务器之间也使用加密传输 |
| 日志与指标 | 添加 `query_recorder`、`query_summary` 或使用 Prometheus 指标 | 需要按请求追踪策略命中、错误和延迟；注意查询记录可能包含隐私信息 |
| 网络联动 | 根据解析结果调用 webhook、脚本，或同步到 ipset/nftset/RouterOS | 自动更新防火墙或策略路由；部分集成依赖特定平台 |

上述能力是否可用取决于所安装的 OxiDNS 版本、bundle 和运行平台。特别是 ipset/nftset 与 RouterOS 集成具有平台要求；不要把 Linux/RouterOS 示例直接套用到 Windows。

## 部署与验证

1. 把 `api.http.auth.password` 替换为唯一、足够强的密码，确保仓库里只保存脱敏占位值。
2. 配置 Sparkle/Mihomo TUN 排除项及 Windows 防火墙规则；这两项不由 `config.yaml` 创建。
3. 在 OxiDNS 实际工作目录运行配置校验：

   ```powershell
   .\oxidns.exe check -c .\config.yaml -d .
   ```

4. 启动后分别检查 WebUI/API、UDP 和 TCP DNS、本机及局域网客户端，并观察 `cache_hit_total`、`ip_selector_probe_total`、`forward_upstream_success_total` 等指标。
5. 在部署变更或升级后重新验证主路径故障时的备用回退。仅有 `/api/readyz` 成功，不能证明所有外部上游都可用。

## 参考

- [本目录配置文件](./config.yaml)
- [OxiDNS 配置总览](https://oxidns.org/configuration)
- [OxiDNS sequence 与控制流](https://oxidns.org/configuration/sequence)
- [上游转发与缓存](https://oxidns.org/plugin-reference/executor/resolution)
- [IP 优选与响应处理](https://oxidns.org/plugin-reference/executor/response)
- [运维与故障排查](https://oxidns.org/operations)
