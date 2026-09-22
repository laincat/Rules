# 05 · Module 与脚本

> 返回 [readme.md](readme.md)

---

# 第一部分 · Module（`.sgmodule`）

## 5.1 模块是什么

模块是**对当前 profile 的一层补丁**。用途：

- 在**不可编辑**的 profile（托管 / 企业）上调设置；
- 一键切换某组设置（例如临时给全部域名开 MITM）；
- 复用别人写好的模块；
- 把共享 profile 适配到不同设备/场景。

> **模块的设置优先级高于 profile。**模块的启用状态**不会**同步到其它设备。

三种类型：内置模块（Surge 自带）、本地模块（profile 目录下的 `.sgmodule`）、
已安装模块（按 URL 安装）。

---

## 5.2 能力边界（官方明确）

| 能做 | 说明 |
|---|---|
| 覆盖 `[General]` / `[MITM]` | `key = value` 覆盖；`%APPEND%` 追加；`%INSERT%` 前置 |
| 覆盖 `[WireGuard *]` / `[Tailscale *]` section | 与主配置一样覆盖或追加键 |
| 覆盖 `[Ruleset *]` | 可以补丁内联规则集 |
| 向 `[Rule]` / `[Script]` / `[URL Rewrite]` / `[Header Rewrite]` / `[Host]` 追加 | 新行插入到**原内容顶部** |

| 不能做 | 说明 |
|---|---|
| 改 `[Proxy]` / `[Proxy Group]` | **完全不能调整** |
| 改 MITM 的 CA 证书 | 不能调整 |
| 通过界面调整模块设置 | 模块覆盖主配置，因此不显示在界面里 |

> ⚠️ **关键约束：模块里的规则只能使用内置策略 —— `DIRECT`、`REJECT`、
> `REJECT-TINYGIF`。**
>
> 也就是说，模块**不能**把流量导向自定义代理组（例如 `Proxy`、`US`）。
> 想让某类流量走某个代理组，必须写进**主 profile 的 `[Rule]`**，
> 而不是模块里。

---

## 5.3 元数据

官方定义的元数据字段（全部可选）：

```
#!name=模块名
#!desc=说明
#!system=mac
#!requirement=CORE_VERSION>=20
#!arguments=hostname:example.com,enable_mitm:true
#!arguments-desc=参数表的总说明
```

| 字段 | 用途 |
|---|---|
| `#!name` | 模块名 |
| `#!desc` | 描述 |
| `#!system` | 限定平台（`mac` / `ios` / `tvos`） |
| `#!requirement` | 版本/环境条件，支持逻辑表达式 `iOS 5.10.0+` `Mac 5.6.0+` |
| `#!arguments` | 用户可填的参数表 `Mac 5.5.0+` |
| `#!arguments-desc` | 参数表的总描述 |

### `#!requirement` 可用变量

| 变量 | 示例 |
|---|---|
| `CORE_VERSION` | 数字，如 `20` |
| `SYSTEM` | `macOS` / `iOS` / `tvOS` |
| `SYSTEM_VERSION` | 如 `Version 17.4.1 (Build 21E236)` |
| `DEVICE_MODEL` | 如 `Mac15,8` |
| `LANGUAGE` | 如 `zh-Hans` |

```
#!requirement=CORE_VERSION>=20 && (SYSTEM = 'iOS' || SYSTEM = 'tvOS')
```

> ⚠️ 注意 `CORE_VERSION` 的**编码断代**：`iOS 5.21.0+` / `Mac 6.8.0+` 起改为
> `major×1000000 + minor×1000 + patch`；更早是固定小数字（`22` = Smart Group 起点）。
> 详见 [01-profile.md](01-profile.md) 1.7。

---

## 5.4 参数表 `Mac 5.5.0+`

声明占位符后，用户在启用模块时填写：

```
#!arguments=hostname:example.com,enable_mitm:true
#!arguments-desc=配置主机名以及是否启用 MITM。

[MITM]
hostname = {{{hostname}}}

[Script]
example = type=generic, script-path=script/example.js, argument="{{{enable_mitm}}}"
```

规则：

- 占位符用**三层花括号** `{{{name}}}`；
- 名字与占位符**区分大小写**；
- 名字只用字母、数字、下划线；
- 删参数时要**一并删掉未使用的占位符**；
- ⚠️ **不支持**查询串形式（`hostname=a&b=c`），也**不支持** `%PARAMETER%` 占位符。
  `%APPEND%` / `%INSERT%` 是**模块操作符，与参数替换无关**。

---

## 5.5 最小示例

```
#!name=额外直连
#!desc=把某站点强制走直连
#!system=mac

[General]
always-real-ip = %APPEND% *.example.com
```

---

# 第二部分 · 脚本

## 5.6 脚本类型

脚本在 `[Script]` section 中声明，按触发时机分为几类：

| 类型 | 触发点 |
|---|---|
| HTTP 请求脚本 | 请求发出前，可改写 URL / Header / Body |
| HTTP 响应脚本 | 收到响应后，可改写 Header / Body |
| 规则脚本 | 规则求值阶段，动态决定策略 |
| DNS 脚本 | DNS 查询阶段 |
| 事件脚本 | 系统/网络事件 |
| Cron 脚本 | 定时任务 |
| 通用脚本 | 由上述脚本显式调用 |

> HTTP 类脚本要看到加密内容，必须先启用 **MITM** 并让域名命中 `hostname` 列表。

---

## 5.7 `$done()` 契约

脚本**必须**调用 `$done(...)` 来结束本次处理，否则请求会挂住。

| 场景 | 调用形式 |
|---|---|
| 纯逻辑脚本（无需改写） | `$done()` |
| 改写后放行 | `$done({ response: {...} })` 等 |

> ⚠️ 漏调 `$done()` 是最常见的脚本错误 —— 表现为**请求卡住直到超时**，
> 而不是报错。

---

## 5.8 `[Panel]` 信息面板

`[Panel]` 用于在 iOS / Mac 上展示脚本计算出的信息（流量统计、订阅余量等）。
面板内容由脚本通过 `$done()` 回填。

---

## 5.9 编写要点

- **脚本要能失败**：外部 API 不可达时走 `$done()` 放行，不要让请求挂死；
- 不要在请求脚本里做重活（会拖慢每个请求）；
- `[Script]` 里的 `argument=` 是给脚本传参的常规方式，
  模块参数表也可以通过它注入（见 5.4）。
