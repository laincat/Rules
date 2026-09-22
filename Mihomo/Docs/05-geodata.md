# 05 · Geodata（`geox-url` / dat / mmdb / mrs）

> 返回 [readme.md](readme.md)

`GEOIP` 与 `GEOSITE` 能不能生效，全看这一章。

---

## 5.1 四个文件分别是什么

| 文件 | 格式 | 供什么规则用 | 典型大小 |
|---|---|---|---|
| `geoip.dat` | V2Ray geodata | `GEOIP`（dat 模式） | 约 16 MB |
| `geosite.dat` | V2Ray geodata | `GEOSITE` | 约 4 MB |
| `country.mmdb` / `geoip.metadb` | MaxMind DB | `GEOIP`（mmdb 模式） | 约 7–8 MB |
| `GeoLite2-ASN.mmdb` | MaxMind DB | `IP-ASN` | 约 12 MB |

---

## 5.2 `geox-url`

```yaml
geox-url:
  geoip:   "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release/geoip.dat"
  geosite: "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release/geosite.dat"
  mmdb:    "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release/geoip.metadb"
geo-auto-update: false     # 是否自动更新
geo-update-interval: 24    # 更新间隔（小时）
```

> ⚠️ 上面三条 URL 就是**官方默认配置里的原文**（写这份文档时实测）。
> 注意官方 `mmdb` 键指向的是 **`geoip.metadb`**，而不是 `country.mmdb` ——
> 两者内容与体积不同，**别以为可以随意互换**。
>
> `geox-url` 若只写部分键，其余键走官方内置默认值。

### 与 geodata 相关的全局字段

| 字段 | 说明 |
|---|---|
| `geodata-mode` | `true` = 用 `geoip.dat` / `geosite.dat`；`false`（默认）= 用 mmdb |
| `geodata-loader` | 加载器：`standard` / `memconservative`（默认，面向小内存设备） |
| `geosite-matcher` | `GEOSITE` 的匹配器实现：`succinct`（默认）/ 其它 |
| `geo-auto-update` | 是否自动更新 geodata |
| `geo-update-interval` | 更新间隔（**小时**） |

> ⚠️ `geodata-mode` 的**默认值是 `false`**，即默认走 mmdb。
> 网上大量配置片段显式写 `geodata-mode: true`，那是在切到 dat 模式 ——
> 两个模式的规则行为在边界情况下并不完全等价（见 5.4）。

---

## 5.3 该用哪个源？

```yaml
# 完整版（推荐）：全量国家 + 全部 GEOSITE 分类
geox-url:
  geoip:   "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release/geoip.dat"
  geosite: "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release/geosite.dat"
  mmdb:    "https://fastly.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@release/geoip.metadb"
  asn:     "https://github.com/xishang0128/geoip/releases/download/latest/GeoLite2-ASN.mmdb"
```

**必须用完整版，不要用 `-lite` 裁剪版。** geodata 是内核的全局地理数据库，
内核假设它包含所有国家与分类：

| 规则 | 依赖 | 用 lite 版的后果 |
|---|---|---|
| `GEOIP,CN` | 完整 geoip | 仍可命中（CN 通常被保留） |
| `GEOIP,US` / `GEOIP,JP` | 完整 geoip | ❌ 失效 |
| `GEOSITE,netflix` / `category-*` | 完整 geosite | ❌ 大部分分类失效 |
| `IP-ASN,xxxx` | 完整 ASN 库 | ❌ 失效 |

> `meta-rules-dat` 的 release 里**同时提供**完整版与 `-lite` 版：
> `geoip.dat`（约 16 MB）vs `geoip-lite.dat`（约 0.2 MB）；
> `geosite.dat`（约 4 MB）vs `geosite-lite.dat`（约 0.2 MB）。
> 体积差 20–80 倍，说明 lite 是裁剪过的 —— 只适合单一用途（例如只判国内直连），
> **不适合当 `geox-url` 的通用源**。

---

## 5.4 `.dat` 与 `.mmdb` 的取舍

| | `geodata-mode: true`（dat） | `geodata-mode: false`（mmdb，默认） |
|---|---|---|
| 主要文件 | `geoip.dat` + `geosite.dat` | 由 `mmdb` 键指向 |
| `GEOSITE` | 由 `geosite.dat` 提供 | 由对应的 mmdb / metadb 提供 |
| 体积 | 较大 | 较小 |
| 兼容 | 与 V2Ray 生态一致 | mihomo 自有格式（metadb） |

> ⚠️ **别把不同来源的 mmdb 当成等价的。** 例如某些第三方 `Country.mmdb`
> 会把**服务类别**（`GOOGLE` / `NETFLIX` / `CLOUDFLARE`…）写在国家码字段上、
> 且优先级高于国家码，于是 `8.8.8.8` 查出来是 `GOOGLE` 而不是 `US` ——
> 这会让 `GEOIP,US` 漏掉那些段。
> 换库前先用几个已知 IP 验一下，不要只看文件能不能加载。

---

## 5.5 `.mrs` / `.srs` / `.dat` 一览

| 扩展名 | 平台 | 说明 |
|---|---|---|
| `.mrs` | mihomo | 规则集二进制（zstd + succinct trie），`domain` / `ipcidr` 推荐 |
| `.srs` | sing-box | sing-box 的二进制规则集 |
| `.yaml` | mihomo | 纯文本 rule-provider |
| `.dat` | V2Ray / mihomo(geodata) | `geoip.dat` / `geosite.dat` |
| `.metadb` | mihomo | mmdb 的一种变体（官方默认 `mmdb` 键指向它） |

> `.mrs` 只适用于 **rule-provider**，不适用于 `geox-url` ——
> `geox-url` 要的是整库文件。两者别混。

---

## 5.6 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `GEOIP,US` 不命中 | 用了裁剪版库，或用了「服务类别覆盖国家码」的库 | 换完整版；先用已知 IP 验证 |
| `GEOSITE,xxx` 报找不到分类 | `geosite` 未下载完或版本旧 | 检查 `geox-url`，重启后等待下载 |
| geodata 下载慢 / 失败 | 直连源不稳 | 换成 jsDelivr 等镜像 |
| `IP-ASN` 全部不命中 | 缺 `asn` 库 | 配置 `geox-url.asn` |
| 改了 `geox-url` 没生效 | `geo-auto-update` 关闭且缓存未失效 | 手动删除缓存文件后重启 |
