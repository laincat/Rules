# 06 · 运维与排错

> 返回 [readme.md](readme.md)

---

## 6.1 HTTP API `iOS 4.4.0+` `Mac 4.0.0+`

用 HTTP API 可以程序化控制 Surge。

### 配置

```
[General]
http-api = examplekey@0.0.0.0:6171
http-api-tls = false
http-api-web-dashboard = false
```

| 参数 | 说明 |
|---|---|
| `http-api` | `密钥@监听地址:端口` |
| `http-api-tls` | 开启 HTTPS（用 MITM 的 CA 生成服务端证书，客户端须手动安装该证书） |
| `http-api-web-dashboard` | 在同一监听上提供 Web 面板 |

### 认证

**所有请求都必须在 `X-Key` 头里带上密钥**：

```
GET /v1/events
X-Key: examplekey
Accept: */*
```

个别不方便设 header 的场景（例如用浏览器直接下载 CA 证书）可以用查询串：

```
http://127.0.0.1:6171/v1/mitm/ca?x-key=examplekey
```

### 基本约定

- 只用 **GET 和 POST**：GET 用 URL 查询串传参，POST 用 JSON body；
- 响应**永远是 JSON**。

### 常用路径

| 路径 | 说明 |
|---|---|
| `/v1/features/{mitm,capture,rewrite,scripting}` | 开关能力，GET 读状态 / POST 改状态 |
| `/v1/features/system_proxy` | Mac Only |
| `/v1/features/enhanced_mode` | Mac Only |
| `/v1/mitm/ca` | 下载 CA 证书 |
| `/v1/events` | 事件流 |
| `/v1/metrics` `iOS 5.22.0+` `Mac 6.9.0+` | **Prometheus 文本格式**指标（唯一非 JSON 响应） |

> 完整列表见官方 [tools/http-api.md](https://manual.nssurge.com/tools/http-api.md)。
> 以上路径以官方手册为准，本页只列常用项。

---

## 6.2 排错顺序（按成本从低到高）

| 步骤 | 做法 |
|---|---|
| 1 | **看日志**：Dashboard → 请求列表，先确认请求**有没有走到预期的策略** |
| 2 | 确认**出站模式**：Direct / Global 会绕过整个规则表 |
| 3 | 确认**规则有没有命中**：把可疑规则临时提到最前面试一次 |
| 4 | 检查**参数平台与最低版本**：未知参数会被静默忽略 |
| 5 | 检查**外部集合是否真的加载**：条数为 0 说明 URL 或格式有问题 |
| 6 | 用 HTTP API 拿状态与指标，排除界面误导 |

---

## 6.3 常见错误对照

| 现象 | 最可能的原因 |
|---|---|
| 参数写了但不生效 | 参数名拼错、或该参数要求更高版本 —— Surge **静默忽略未知参数** |
| 外部规则集完全不生效 | 文件格式与引用类型不匹配（`.list` 用 `DOMAIN-SET` 引用等） |
| 规则集条数为 0 | URL 不可达、或地址写错 |
| 同一 URL 用了两种引用 | 违反官方硬约束：同一文件不能既当 `RULE-SET` 又当 `DOMAIN-SET` |
| 域名请求变慢 | IP 类规则在前且缺 `no-resolve` |
| 配了 `pre-matching` 但没用 | 策略不是 REJECT 家族，或写在了子规则里 |
| 模块里的规则不生效 | 模块内规则**只能用 `DIRECT` / `REJECT` / `REJECT-TINYGIF`** |
| 规则顺序奇怪 | 模块注入的规则插在**原规则列表顶部** |
| 脚本导致请求卡住 | 脚本没调 `$done()` |
| DNS 解析失败即请求失败 | `FINAL` 未加 `dns-failed` |
| 某设备流量完全不走 Surge | 该设备写死 DNS，需要 `hijack-dns` |

---

## 6.4 性能要点

1. **`pre-matching`** —— 广告请求在 DNS / TCP 握手阶段就被拒，不建连、不解析，收益最大；
2. **`no-resolve`** —— 避免为匹配 IP 规则而白白解析域名；
3. **`DOMAIN-SET` 承载大列表** —— 索引化查找，20 万条也是常数级；
4. **减少 MITM 覆盖面** —— MITM 需要解密，域名列表越大代价越高；
5. **脚本保持轻量** —— 运行在每个命中请求上。

---

## 6.5 版本升级前的检查清单

| 检查项 | 原因 |
|---|---|
| Beta 通道的特性是否写进了正式配置 | 稳定版会**静默忽略**未知参数 |
| 逻辑规则里是否引用了带括号的策略名 | `Mac 6.10.0` 之前会解析错误 |
| `CORE_VERSION` 表达式是否用了旧式编码 | 断代见 [01-profile.md](01-profile.md) 1.7 |
| 需要 `UNKNOWN` 的规则是否已升到 `iOS 5.22.1+` / `Mac 6.9.1+` | 低版本不认识该取值 |

> ⚠️ 判断"最新版是什么"要分平台：
> Mac 看 appcast（带 build 号），iOS 看 App Store ——
> 知识库的 iOS 更新日志**长期滞后**，不能作为版本依据（见 readme 第五节）。
