# 07 · 运维与排错

> 返回 [readme.md](readme.md)

---

## 7.1 RESTful API

```yaml
external-controller: 0.0.0.0:9093
external-controller-cors:
  allow-origins: ["*"]
  allow-private-network: true
```

若配置了 `secret`，请求需带 `Authorization: Bearer <secret>`。

### 常用端点

| 端点 | 说明 |
|---|---|
| `GET /version` | 内核版本 |
| `GET /configs` | 当前配置 |
| `PATCH /configs` | 热改配置（`mode` / `log-level` 等） |
| `GET /proxies` | 全部策略与节点状态 |
| `PUT /proxies/{name}` | 切换 `select` 组的选中项 |
| `GET /proxies/{name}/delay` | 对某节点测延迟 |
| `GET /providers/proxies` | 节点 provider 状态（含更新时间） |
| `GET /providers/rules` | 规则 provider 状态 |
| `PUT /providers/proxies/{name}` | 手动触发 provider 更新 |
| `GET /rules` | 规则列表 |
| `GET /connections` | 实时连接 |
| `DELETE /connections` | 关闭连接 |
| `GET /logs?level=info` | 日志流（WebSocket） |
| `GET /traffic` | 流量流（WebSocket） |

> 用 `/providers/rules` 可以直接确认**规则集到底加载成功没有** ——
> 这是排查"规则没生效"最快的一步。

---

## 7.2 排错顺序

| 步骤 | 做法 |
|---|---|
| 1 | 确认 `mode` 是 `rule`（`global` / `direct` 会绕过规则表） |
| 2 | 用 `/providers/rules` 确认规则集**已加载且条数非 0** |
| 3 | 确认 `behavior` 与 payload 语法匹配（`classical` vs `domain`） |
| 4 | 看 `/logs` 确认请求命中了哪条规则 |
| 5 | 检查 `GEOIP` / `GEOSITE` 是否因 geodata 缺失而失效 |
| 6 | 检查 `no-resolve` 是否写在引用行上 |

---

## 7.3 常见错误对照

| 现象 | 最可能的原因 |
|---|---|
| 规则集完全不生效、也不报错 | `behavior` 写错 → 静默失效 |
| 规则集条数为 0 | provider URL 不可达 / 路径写错 |
| 启动报 `unsupported vehicle type` | `type` 不是 `http` / `file` / `inline` |
| 启动报 `` `use` or `proxies` missing `` | 策略组两个字段都没写 |
| 本地 path 被拒 | 不在 Home Dir 内，需 `SAFE_PATHS` |
| `GEOIP,US` 不命中 | 用了裁剪版或类别覆盖国家码的库 |
| `IP-ASN` 全不命中 | 缺 `geox-url.asn` |
| 域名请求变慢 | IP 类规则缺 `no-resolve` |
| `.mrs` 报格式错误 | 把 `classical` 当 `mrs` 用了（仅支持 `domain` / `ipcidr`） |
| 规则数量对了但仍不命中 | 前面的规则先命中了，调整顺序 |

---

## 7.4 性能要点

1. **`behavior: domain` 用 trie**（常数级）；`classical` 逐条，最慢；
2. **`.mrs` 优于 `.yaml`**：zstd + succinct trie，加载更快、体积更小；
3. **`no-resolve`** 写在 `rules:` 的引用行上，避免多余的 DNS；
4. **`geodata-loader`**：小内存设备用 `memconservative`（默认）；
5. **`lazy`**：大节点集用惰性测速，减少无谓开销。

---

## 7.5 版本与升级

| 关注点 | 说明 |
|---|---|
| 日常用正式版 | 有 tag、可回退 |
| Alpha 增量多为 bugfix | 不涉配置面时不必跟进 |
| 配置面变更信号 | 官方 `docs/config.yaml` 的哈希（本仓库自动盯） |

> 本仓库 `Mihomo/Docs/upstream.json` 记录着正式版 / Alpha / 配置哈希的
> 当前值与上次变化时间，由 `tools/docs_watch.py` 每日刷新。
