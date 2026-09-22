# 01 · Profile（配置文件）

> 返回 [readme.md](readme.md)

Profile 是 Surge 行为的**唯一事实来源**。界面能改大部分内容，但高级 / 实验性
功能仍要手写。

---

## 1.1 基本形态（INI 风格）

```
[General]
loglevel = notify

[Proxy]
ProxyA = http, 1.2.3.4, 80

[Rule]
DOMAIN-SUFFIX,example.com,ProxyA
FINAL,DIRECT
```

两类 section，语法不同：

- `[General]` / `[MITM]` 这类是 `key = value`，**行的顺序通常不影响行为**；
- `[Rule]` / `[URL Rewrite]` 这类是**有序**的，**行的先后就是行为的一部分**。

---

## 1.2 Section 一览

官方识别的全部 section（未识别的 section 会被原样保留、不报错）：

| Section | 用途 |
|---|---|
| `[General]` | 全局设置 |
| `[Proxy]` | 代理策略定义 |
| `[Proxy Group]` | 策略组 |
| `[Rule]` | 规则 |
| `[Host]` | 本地 DNS 映射 |
| `[URL Rewrite]` | URL 重写 |
| `[Header Rewrite]` | Header 重写 |
| `[Body Rewrite]` | Body 重写 |
| `[Map Local]` | 本地映射 |
| `[MITM]` | HTTPS 解密 |
| `[Keystore]` | 证书与私钥 |
| `[SSID Setting]` | 按网络环境的子网设置 |
| `[Script]` | 脚本 |
| `[Panel]` | 信息面板 |
| `[Ponte]` | Surge Ponte |
| `[Port Forwarding]` | 端口转发 |
| `[Testing]` | 吞吐测试 |
| `[DHCP]` | DHCP 服务（Mac 网关模式） |
| `[Snell Server]` | 内置 Snell 服务端 |
| `[MTProto]` | 内置 MTProto 服务端 |
| `[WireGuard <name>]` | WireGuard 策略配置 |
| `[Tailscale <name>]` | Tailscale 策略配置 |
| `[Ruleset <name>]` | 内联规则集 |

---

## 1.3 注释

注释行以 `#`、`;` 或 `//` 开头，**三种都合法**：

```
# 注释
; 注释
// 注释
```

**行尾注释**也支持，但**分隔符前至少要有一个空格**：

```
dns-server = 8.8.8.8 // 行尾注释
dns-server = 8.8.8.8 # 行尾注释
dns-server = 8.8.8.8 ; 行尾注释
```

> ⚠️ 不留空格就写 `8.8.8.8//x` 会被当成值的一部分 —— 这是把一行配置
> 写成静默错误的最常见方式。

---

## 1.4 引号包裹的值 `iOS 5.21.0+` `Mac 6.8.0+`

双引号内的 `\"` 表示字面双引号、`\\` 表示字面反斜杠：

```
example = "a quoted value: \"text\"; path: C:\\Proxy"
```

用途：值里含**逗号或空格**时（例如代理组描述、带空格的节点名）必须加引号，
否则会被当作分隔符切开。

---

## 1.5 Profile 的三种类型

| 类型 | 说明 |
|---|---|
| 普通 | 手工创建 / 默认使用。可自由编辑 |
| 托管（Managed） | 通常由企业管理员或服务商下发。**本地不可改**，因为它会被远程更新；要改就先复制成普通 profile |
| 企业（Enterprise） | 仅企业版。不可修改 / 查看 / 复制 |

---

## 1.6 拆分与包含 `#!include`

复杂的配置可以把一个或多个 section 拆到另一个文件：

```
#!include detach.conf
```

> 被 `#!include` 引入的内容在**语句所在位置原地展开**，可与普通内容混用。

---

## 1.7 需求表达式 `#!REQUIREMENT`

用行尾注释给单行加条件，或用独立的 `#!REQUIREMENT` 声明。

**简化记法** `iOS 5.14.3+` `Mac 5.10.0+`：

```
#!IOS-ONLY
#!MACOS-ONLY
#!TVOS-ONLY
```

它们覆盖了绝大多数"只在某平台生效"的场景。更复杂的条件用变量与运算符表达：

```
#!requirement CORE_VERSION>=22 AND SYSTEM=='iOS'
```

常用变量：

| 变量 | 说明 |
|---|---|
| `CORE_VERSION` | 内核版本号 |
| `SYSTEM` | `iOS` / `macOS` / `tvOS` |
| `DEVICE_NAME` `iOS 5.22.0+` `Mac 6.9.0+` | 设备名（系统设置里的那个） |

> `CORE_VERSION` 自 `iOS 5.21.0+` / `Mac 6.8.0+` 起改用
> `major×1000000 + minor×1000 + patch` 编码（Mac 6.8.0 → `6008000`）。
> 更早的版本用**固定小数字**（`22` = Smart Group 起点，`20` = Body Rewrite 起点），
> 引用旧资料时注意这个断代。

> ⚠️ 用旧式写法判断新版本会得到错误结果 —— 这是"条件明明写了却不生效"的典型原因。

---

## 1.8 最低版本速查

| 功能 | 最低版本 |
|---|---|
| 引号包裹值 | `iOS 5.21.0+` / `Mac 6.8.0+` |
| 内联规则集 `[Ruleset x]` | `Mac 5.3.1+` |
| 简化记法 `#!IOS-ONLY` | `iOS 5.14.3+` / `Mac 5.10.0+` |
| 规则编辑器可编辑内联 / 本地规则集 | `iOS 5.22.0+` / `Mac 6.9.0+` |
