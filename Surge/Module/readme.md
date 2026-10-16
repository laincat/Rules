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

