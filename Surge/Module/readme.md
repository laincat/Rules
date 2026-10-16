## Surge (version > 5.00)

### 模块兼容性与使用范围

依据 [Surge 官方模块文档](https://manual.nssurge.com/profile/module.html)，模块 `[Rule]` 仅支持内置策略。以下文件包含个人策略 / 设备名，不能当作通用可安装模块：

- `Downloads-Rules.sgmodule`、`Ozon.sgmodule`：`nProxy`
- `Game-Rules.sgmodule`：`Custom`
- `Telegram.sgmodule`：`TG-SG` / `TG-US` / `TG-EU`
- `Ponte.sgmodule`：`DEVICE:LAINCAT-MINI`

这些文件保留原路由意图作为规则参考。需使用时，将其中 `[Rule]` 下的有效规则复制到主配置 `[Rule]` 的合适位置，并确认对应策略组或 Ponte 设备存在；不要同时启用旧模块，也不要把策略盲目改成 DIRECT。官方兼容性限制不等于已在每个 Surge 版本实测失败。

`SSID-Setting.sgmodule` 中 `TYPE:WIRED` 覆盖所有有线网络，且 DNS 指向私人内网。`Mitm_All.sgmodule` 会替换 MITM 主机列表并大范围解密，仅适合明确理解范围的调试场景。请按自己的环境决定是否启用。

`LocalDev.sgmodule` 的 IP Rewrite 需要 Surge iOS 5.23.0 / Mac 6.10.0 或更高版本。`SSID-Setting.sgmodule` 的 `[SSID Setting]` 未列在官方模块支持区段中，建议放入主配置并在设备上验证。

### Install Module

```
https://raw.githubusercontent.com/laincat/Rules/main/Surge/Module/Mitm_All.sgmodule
```

#### Special thanks：

```
https://github.com/scomper/Surge
https://github.com/NobyDa/Script
https://github.com/yichahucha/surge
https://github.com/onewayticket255/Surge-Script
https://github.com/nzw9314/Surge
```

#### BoxJs
```
https://chavyleung.gitbook.io/boxjs
```


### 私人模块需要明确选择后才启用

本目录保留个人配置样本，不代表推荐全部安装。`Mitm_All`、`SSID-Setting` 和 `Ponte` 应在确认解密范围、网络/DNS 与设备名称后单独选择；文档更新不会替你启用、停用或修改设备设置。

`Game-Rules` 与 `Downloads-Rules` 的 Xbox 资源规则存在重叠。迁入主配置前，先决定游戏下载应走 `Custom` 还是 `nProxy`，再安排规则先后；不能靠同时启用两个模块保证结果。

`CaiYun` 引用的外部脚本不仅清理广告，还修改订阅响应并注入脚本自身内置凭据。不要把它视为纯广告过滤；应先审核你实际使用的脚本版本再决定是否启用。仓库不复制或验证该凭据。脚本声明复用名称是否冲突仍需目标 Surge 版本验证，不作未经证实的重命名。
