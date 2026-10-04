# 05 · Geodata（`geox-url` / dat / mmdb / mrs）

> 返回 [readme.md](readme.md)

`GEOIP` 与 `GEOSITE` 能不能生效，全看这一章。

---

## 5.1 四个文件分别是什么

| 文件 | 格式 | 供什么规则用 |
|---|---|---|
| `geoip.dat` | V2Ray geodata | `GEOIP`（dat 模式） |
| `geosite.dat` | V2Ray geodata | `GEOSITE`，两种 geodata-mode 都使用 |
| `country.mmdb` / `geoip.metadb` | IP 地理数据库 | `GEOIP`（mmdb 模式） |
| `GeoLite2-ASN.mmdb` | MaxMind DB | `IP-ASN` |

文件体积和覆盖范围随来源与版本变化，应以实际下载产物为准。

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

> 上面三条 URL 来自**官方示例配置**，是可选择的镜像源。
> 注意官方 `mmdb` 键指向的是 **`geoip.metadb`**，而不是 `country.mmdb` ——
> 两者内容与体积不同，**别以为可以随意互换**。
>
> `geox-url` 若只写部分键，其余键走官方内置默认值。

`v1.19.32` 内核内置下载地址位于
`https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/`，
分别使用 `geoip.dat`、`geosite.dat`、`geoip.metadb`、`GeoLite2-ASN.mmdb`。
使用相关规则时，缺失的库会尝试自动下载；`geox-url` 用于覆盖来源，
关闭 `geo-auto-update` 只关闭周期更新，不关闭首次缺库下载。
下载、校验或分类加载失败应查看启动日志。
来源：[内核默认地址](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/config/config.go#L583)、
[geodata 初始化](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/component/geodata/init.go#L90)。

### 与 geodata 相关的全局字段

| 字段 | 说明 |
|---|---|
| `geodata-mode` | 只决定 `GEOIP` 的来源：`true` 用 `geoip.dat`，`false`（默认）用 MMDB/metadb；`GEOSITE` 始终使用 `geosite.dat` |
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
  asn:     "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb"
```

库必须包含配置实际引用的国家和分类。需要多地区、多分类分流时选完整版；
裁剪版是否适用，应核对它实际保留的集合：

| 规则 | 依赖 | 选库时检查 |
|---|---|---|
| `GEOIP,CN` | 当前 GEOIP 数据库 | 是否保留 CN |
| `GEOIP,US` / `GEOIP,JP` | 当前 GEOIP 数据库 | 是否保留 US／JP |
| `GEOSITE,netflix` / `category-*` | `geosite.dat` | 是否包含实际引用的分类 |
| `IP-ASN,xxxx` | 独立 ASN 库 | ASN 数据源是否有效，与 geoip/geosite 是否 lite 分开检查 |

---

## 5.4 `.dat` 与 `.mmdb` 的取舍

| | `geodata-mode: true`（dat） | `geodata-mode: false`（mmdb，默认） |
|---|---|---|
| `GEOIP` 文件 | `geoip.dat` | 由 `mmdb` 键指向的 MMDB/metadb |
| `GEOSITE` 文件 | `geosite.dat` | `geosite.dat` |
| 覆盖范围／体积 | 取决于具体来源和版本 | 取决于具体来源和版本 |
| 格式 | V2Ray geodata | MMDB 或 mihomo 支持的 metadb |

来源：[GEOSITE 加载实现](https://github.com/MetaCubeX/mihomo/blob/v1.19.32/rules/common/geosite.go#L64)。

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
| `IP-ASN` 加载失败或不命中 | ASN 库下载失败、无效或缺少目标 ASN | 查启动日志；必要时用 `geox-url.asn` 覆盖内置来源 |
| 改了 `geox-url` 没生效 | `geo-auto-update` 关闭且缓存未失效 | 手动删除缓存文件后重启 |
